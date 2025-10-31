import os
import sys
import glob
import json
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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

        if req.use_csv:
            csv_files = sorted(glob.glob(os.path.join(ROOT_DIR, req.data_dir, "*.csv")))
            for csv_path in csv_files:
                base = os.path.splitext(os.path.basename(csv_path))[0]
                schema_out = os.path.join(ROOT_DIR, "specs", f"{base}_schema.json")
                schema = build_schema_for_csv(csv_path, natural_prompt=req.prompt, n_rows=req.rows)
                with open(schema_out, "w") as f:
                    json.dump(schema, f, indent=2)
                run_summary["schemas"][base] = schema
                run_summary["files"].append(os.path.relpath(schema_out, ROOT_DIR))

                meta_out = os.path.join(ROOT_DIR, "specs", f"{base}_metadata.json")
                metadata = augment_metadata(csv_path, schema=schema, natural_prompt=req.prompt, n_rows=max(req.rows, 50))
                with open(meta_out, "w") as f:
                    json.dump(metadata, f, indent=2)
                run_summary["metadata"][base] = metadata
                run_summary["files"].append(os.path.relpath(meta_out, ROOT_DIR))
        else:
            only_out = os.path.join(ROOT_DIR, "specs", "intent_only_schema.json")
            schema = build_schema_from_intent(req.prompt)
            with open(only_out, "w") as f:
                json.dump(schema, f, indent=2)
            run_summary["schemas"]["intent_only"] = schema
            run_summary["files"].append(os.path.relpath(only_out, ROOT_DIR))

            meta_out = os.path.join(ROOT_DIR, "specs", "intent_only_metadata.json")
            metadata = augment_from_schema(schema, natural_prompt=req.prompt)
            with open(meta_out, "w") as f:
                json.dump(metadata, f, indent=2)
            run_summary["metadata"]["intent_only"] = metadata
            run_summary["files"].append(os.path.relpath(meta_out, ROOT_DIR))

        return run_summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
