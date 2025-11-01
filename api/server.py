import os
import sys
import glob
import json
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Ensure project root is on path so we can import local modules
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from intent.intent_parser import parse_intent
from schema.schema_builder import build_schema_for_csv, build_schema_from_intent
from metadata.augmenter import augment_metadata, augment_from_schema


class IntentRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the desired dataset")
    out: Optional[str] = Field(default="specs/intent.json")


class SchemaRequest(BaseModel):
    prompt: str = Field(...)
    use_csv: bool = Field(default=True)
    rows: int = Field(default=20, ge=1, le=1000)
    data_dir: str = Field(default="data")


class RunRequest(BaseModel):
    prompt: str = Field(...)
    use_csv: bool = Field(default=True)
    rows: int = Field(default=20, ge=1, le=1000)
    data_dir: str = Field(default="data")
    review: bool = Field(default=False, description="No-op placeholder for future review workflow")


class ApproveRequest(BaseModel):
    files: Optional[list[str]] = Field(default=None, description="List of schema file paths to approve; if omitted, approve all *_schema.json in specs/")


class SubmitReviewRequest(BaseModel):
    name: str = Field(..., description="Schema base name or filename (e.g., ecommerce_transactions_schema.json or ecommerce_transactions)")
    schema: Dict[str, Any] = Field(..., description="Reviewed schema JSON content")


def ensure_specs():
    os.makedirs(os.path.join(ROOT_DIR, "specs"), exist_ok=True)


def list_specs() -> Dict[str, Any]:
    specs_dir = os.path.join(ROOT_DIR, "specs")
    ensure_specs()
    files = []
    for p in sorted(glob.glob(os.path.join(specs_dir, "*.json"))):
        files.append(os.path.relpath(p, ROOT_DIR))
    return {"files": files}


app = FastAPI(title="OpenSchema Backend", version="0.1.0")

# CORS for local dev (Vite default port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    load_dotenv()  # load GEMINI_API_KEY or GOOGLE_API_KEY
    ensure_specs()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/specs")
def get_specs():
    return list_specs()


@app.get("/specs/{name}")
def get_spec_file(name: str):
    # Prevent path traversal, only allow files in specs/
    safe_name = os.path.basename(name)
    path = os.path.join(ROOT_DIR, "specs", safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/json")


@app.post("/review/approve")
def review_approve(req: ApproveRequest):
    ensure_specs()
    specs_dir = os.path.join(ROOT_DIR, "specs")
    # Determine which files to approve
    candidate_files: list[str]
    if req.files:
        # Normalize and filter to schema files within specs
        candidate_files = []
        for f in req.files:
            safe = os.path.basename(f)
            if not safe.endswith("_schema.json"):
                continue
            path = os.path.join(specs_dir, safe)
            if os.path.isfile(path):
                candidate_files.append(path)
    else:
        candidate_files = sorted(glob.glob(os.path.join(specs_dir, "*_schema.json")))

    if not candidate_files:
        return {"approved": [], "message": "No schema files to approve."}

    approved_out = []
    for schema_path in candidate_files:
        base = os.path.splitext(os.path.basename(schema_path))[0]
        reviewed_path = os.path.join(specs_dir, base + ".reviewed.json")
        with open(schema_path, "r") as f:
            content = json.load(f)
        with open(reviewed_path, "w") as f:
            json.dump(content, f, indent=2)
        approved_out.append(os.path.relpath(reviewed_path, ROOT_DIR))

    return {"approved": approved_out}


@app.post("/review/submit")
def review_submit(req: SubmitReviewRequest):
    ensure_specs()
    specs_dir = os.path.join(ROOT_DIR, "specs")
    safe = os.path.basename(req.name)
    if safe.endswith("_schema.json"):
        base = os.path.splitext(safe)[0]
    elif safe.endswith(".json"):
        base = os.path.splitext(safe)[0]
        if not base.endswith("_schema"):
            base = base + "_schema"
    else:
        base = f"{safe}_schema"
    reviewed_path = os.path.join(specs_dir, base + ".reviewed.json")
    with open(reviewed_path, "w") as f:
        json.dump(req.schema, f, indent=2)
    return {"saved": os.path.relpath(reviewed_path, ROOT_DIR)}


def _sse_encode(message: str, event: Optional[str] = None) -> bytes:
    lines = []
    if event:
        lines.append(f"event: {event}")
    for chunk in str(message).splitlines() or [""]:
        lines.append(f"data: {chunk}")
    lines.append("")  # end of event
    return ("\n".join(lines) + "\n").encode("utf-8")


@app.get("/run_stream")
def api_run_stream(prompt: str, use_csv: bool = True, rows: int = 20, data_dir: str = "data"):
    ensure_specs()

    def gen():
        saved_files = []
        try:
            # 1) Interpret user intent
            intent_out = os.path.join(ROOT_DIR, "specs", "intent.json")
            intent = parse_intent(prompt, save_path=intent_out)
            saved_files.append(os.path.relpath(intent_out, ROOT_DIR))
            yield _sse_encode("✅ Intent parsed and validated.")
            yield _sse_encode(f"Saved to: {os.path.relpath(intent_out, ROOT_DIR)}")

            # 2) Auto build schemas and 3) Augment descriptions
            if use_csv:
                csv_files = sorted(glob.glob(os.path.join(ROOT_DIR, data_dir, "*.csv")))
                if not csv_files:
                    yield _sse_encode(f"No CSV files found in {data_dir}. Skipping schema/metadata steps.")
                else:
                    for csv_path in csv_files:
                        base = os.path.splitext(os.path.basename(csv_path))[0]
                        schema_out = os.path.join(ROOT_DIR, "specs", f"{base}_schema.json")
                        meta_out = os.path.join(ROOT_DIR, "specs", f"{base}_metadata.json")

                        yield _sse_encode(f"\n🧩 Building schema for: {csv_path}")
                        schema = build_schema_for_csv(csv_path, natural_prompt=prompt, n_rows=rows)
                        with open(schema_out, 'w') as f:
                            json.dump(schema, f, indent=2)
                        yield _sse_encode(f"   • Wrote {os.path.relpath(schema_out, ROOT_DIR)}")
                        saved_files.append(os.path.relpath(schema_out, ROOT_DIR))

                        yield _sse_encode(f"📝 Augmenting metadata for: {csv_path}")
                        metadata = augment_metadata(csv_path, schema=schema, natural_prompt=prompt, n_rows=max(rows, 50))
                        with open(meta_out, 'w') as f:
                            json.dump(metadata, f, indent=2)
                        yield _sse_encode(f"   • Wrote {os.path.relpath(meta_out, ROOT_DIR)}")
                        saved_files.append(os.path.relpath(meta_out, ROOT_DIR))
            else:
                only_out = os.path.join(ROOT_DIR, "specs", "intent_only_schema.json")
                yield _sse_encode("\n🧩 Building schema from intent only (no CSV context)...")
                schema = build_schema_from_intent(prompt)
                with open(only_out, 'w') as f:
                    json.dump(schema, f, indent=2)
                yield _sse_encode(f"   • Wrote {os.path.relpath(only_out, ROOT_DIR)}")
                saved_files.append(os.path.relpath(only_out, ROOT_DIR))

                meta_out = os.path.join(ROOT_DIR, "specs", "intent_only_metadata.json")
                yield _sse_encode("📝 Augmenting metadata from schema (no CSV)...")
                metadata = augment_from_schema(schema, natural_prompt=prompt)
                with open(meta_out, 'w') as f:
                    json.dump(metadata, f, indent=2)
                yield _sse_encode(f"   • Wrote {os.path.relpath(meta_out, ROOT_DIR)}")
                saved_files.append(os.path.relpath(meta_out, ROOT_DIR))

            # Final: emit files as a separate event and a friendly summary
            yield _sse_encode(json.dumps(saved_files), event="files")
            yield _sse_encode("Done", event="done")
        except Exception as e:
            # Send error then close
            yield _sse_encode(f"Error: {str(e)}", event="error")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


@app.post("/intent")
def api_intent(req: IntentRequest):
    try:
        intent = parse_intent(req.prompt, save_path=req.out or "specs/intent.json")
        return {"intent": intent, "saved": os.path.relpath(req.out or "specs/intent.json", ROOT_DIR)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/schema")
def api_schema(req: SchemaRequest):
    try:
        ensure_specs()
        results: Dict[str, Any] = {"schemas": {}, "files": []}
        if req.use_csv:
            csv_files = sorted(glob.glob(os.path.join(ROOT_DIR, req.data_dir, "*.csv")))
            if not csv_files:
                return JSONResponse(status_code=200, content={"message": f"No CSV files found in {req.data_dir}", **results})
            for csv_path in csv_files:
                base = os.path.splitext(os.path.basename(csv_path))[0]
                schema_out = os.path.join(ROOT_DIR, "specs", f"{base}_schema.json")
                schema = build_schema_for_csv(csv_path, natural_prompt=req.prompt, n_rows=req.rows)
                with open(schema_out, "w") as f:
                    json.dump(schema, f, indent=2)
                results["schemas"][base] = schema
                results["files"].append(os.path.relpath(schema_out, ROOT_DIR))
        else:
            only_out = os.path.join(ROOT_DIR, "specs", "intent_only_schema.json")
            schema = build_schema_from_intent(req.prompt)
            with open(only_out, "w") as f:
                json.dump(schema, f, indent=2)
            results["schemas"]["intent_only"] = schema
            results["files"].append(os.path.relpath(only_out, ROOT_DIR))
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/augment")
def api_augment(req: SchemaRequest):
    try:
        ensure_specs()
        results: Dict[str, Any] = {"metadata": {}, "files": []}
        if req.use_csv:
            csv_files = sorted(glob.glob(os.path.join(ROOT_DIR, req.data_dir, "*.csv")))
            if not csv_files:
                return JSONResponse(status_code=200, content={"message": f"No CSV files found in {req.data_dir}", **results})
            for csv_path in csv_files:
                base = os.path.splitext(os.path.basename(csv_path))[0]
                schema_path = os.path.join(ROOT_DIR, "specs", f"{base}_schema.json")
                if not os.path.exists(schema_path):
                    # Build schema if missing
                    schema = build_schema_for_csv(csv_path, natural_prompt=req.prompt, n_rows=req.rows)
                else:
                    with open(schema_path, "r") as f:
                        schema = json.load(f)
                meta_out = os.path.join(ROOT_DIR, "specs", f"{base}_metadata.json")
                metadata = augment_metadata(csv_path, schema=schema, natural_prompt=req.prompt, n_rows=max(req.rows, 50))
                with open(meta_out, "w") as f:
                    json.dump(metadata, f, indent=2)
                results["metadata"][base] = metadata
                results["files"].append(os.path.relpath(meta_out, ROOT_DIR))
        else:
            # intent-only
            intent_schema_path = os.path.join(ROOT_DIR, "specs", "intent_only_schema.json")
            if not os.path.exists(intent_schema_path):
                schema = build_schema_from_intent(req.prompt)
            else:
                with open(intent_schema_path, "r") as f:
                    schema = json.load(f)
            meta_out = os.path.join(ROOT_DIR, "specs", "intent_only_metadata.json")
            metadata = augment_from_schema(schema, natural_prompt=req.prompt)
            with open(meta_out, "w") as f:
                json.dump(metadata, f, indent=2)
            results["metadata"]["intent_only"] = metadata
            results["files"].append(os.path.relpath(meta_out, ROOT_DIR))
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/run")
def api_run(req: RunRequest):
    try:
        ensure_specs()
        saved_files = []
        intent_out = os.path.join(ROOT_DIR, "specs", "intent.json")
        intent = parse_intent(req.prompt, save_path=intent_out)
        saved_files.append(os.path.relpath(intent_out, ROOT_DIR))

        run_summary: Dict[str, Any] = {"intent": intent, "schemas": {}, "metadata": {}, "files": saved_files}
        log = []
        # Mirror main.py console messages for frontend-friendly display
        log.append("✅ Intent parsed and validated.")
        log.append(f"Saved to: {os.path.relpath(intent_out, ROOT_DIR)}")

        if req.use_csv:
            csv_files = sorted(glob.glob(os.path.join(ROOT_DIR, req.data_dir, "*.csv")))
            if not csv_files:
                # nothing to do
                run_summary["log"] = log
                return run_summary
            for csv_path in csv_files:
                base = os.path.splitext(os.path.basename(csv_path))[0]
                schema_out = os.path.join(ROOT_DIR, "specs", f"{base}_schema.json")
                schema = build_schema_for_csv(csv_path, natural_prompt=req.prompt, n_rows=req.rows)
                with open(schema_out, "w") as f:
                    json.dump(schema, f, indent=2)
                run_summary["schemas"][base] = schema
                run_summary["files"].append(os.path.relpath(schema_out, ROOT_DIR))
                log.append(f"\n🧩 Building schema for: {csv_path}")
                log.append(f"   • Wrote {os.path.relpath(schema_out, ROOT_DIR)}")

                meta_out = os.path.join(ROOT_DIR, "specs", f"{base}_metadata.json")
                metadata = augment_metadata(csv_path, schema=schema, natural_prompt=req.prompt, n_rows=max(req.rows, 50))
                with open(meta_out, "w") as f:
                    json.dump(metadata, f, indent=2)
                run_summary["metadata"][base] = metadata
                run_summary["files"].append(os.path.relpath(meta_out, ROOT_DIR))
                log.append(f"📝 Augmenting metadata for: {csv_path}")
                log.append(f"   • Wrote {os.path.relpath(meta_out, ROOT_DIR)}")
        else:
            only_out = os.path.join(ROOT_DIR, "specs", "intent_only_schema.json")
            schema = build_schema_from_intent(req.prompt)
            with open(only_out, "w") as f:
                json.dump(schema, f, indent=2)
            run_summary["schemas"]["intent_only"] = schema
            run_summary["files"].append(os.path.relpath(only_out, ROOT_DIR))
            log.append("\n🧩 Building schema from intent only (no CSV context)...")
            log.append(f"   • Wrote {os.path.relpath(only_out, ROOT_DIR)}")

            meta_out = os.path.join(ROOT_DIR, "specs", "intent_only_metadata.json")
            metadata = augment_from_schema(schema, natural_prompt=req.prompt)
            with open(meta_out, "w") as f:
                json.dump(metadata, f, indent=2)
            run_summary["metadata"]["intent_only"] = metadata
            run_summary["files"].append(os.path.relpath(meta_out, ROOT_DIR))
            log.append("📝 Augmenting metadata from schema (no CSV)...")
            log.append(f"   • Wrote {os.path.relpath(meta_out, ROOT_DIR)}")

        run_summary["log"] = log
        return run_summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Mount static files (React frontend) at root - MUST be last so API routes take precedence
WEB_DIST_DIR = os.path.join(ROOT_DIR, "web", "dist")
if os.path.isdir(WEB_DIST_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="static")
