from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Any, Dict, Optional

import pandas as pd

from .schema_model import validate_schema, schema_summary
from .generator import generate_from_schema
from .validator import validate_dataframe, score_realism


def _json_canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _hash_str(s: str, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def _hash_file(path: str, algo: str = "md5") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_pipeline_from_schema(
    schema: Dict[str, Any],
    seed: int | str = 42,
    confirm_schema: bool = False,
    out_csv: Optional[str] = None,
    verbose: bool = False,
    source_csv: Optional[str] = None,
    mode: Optional[str] = None,
    target_rows: Optional[int] = None,
    additional_rows: Optional[int] = None,
    force: bool = False,
) -> Dict[str, Any]:
    try:
        normalized = validate_schema(dict(schema))
        if confirm_schema:
            return {
                "ok": True,
                "schema": normalized,
                "schema_summary": schema_summary(normalized),
            }

        df, gen_report = generate_from_schema(
            normalized,
            seed=seed,
            source_csv=source_csv,
            mode=mode,
            target_rows=target_rows,
            additional_rows=additional_rows,
            force=force,
        )
        validation = validate_dataframe(df, normalized, tolerance={"class_balance": 0.01})
        realism = score_realism(df, normalized)

        csv_path = None
        csv_hash = None
        if out_csv:
            # atomic write
            dname = os.path.dirname(out_csv) or "."
            os.makedirs(dname, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", delete=False, dir=dname, encoding="utf-8", newline="") as tmp:
                df.to_csv(tmp, index=False)
                tmp_path = tmp.name
            os.replace(tmp_path, out_csv)
            csv_path = out_csv
            csv_hash = _hash_file(csv_path, algo="md5")

        # Fingerprint combines normalized schema + generation report + optional CSV hash
        fp_payload = {
            "schema": normalized,
            "generation_report": gen_report,
            "csv_hash": csv_hash,
        }
        fingerprint = _hash_str(_json_canonical(fp_payload), algo="sha256")

        return {
            "ok": True,
            "schema": normalized,
            "generation_report": gen_report,
            "validation": validation,
            "realism": realism,
            "csv_path": csv_path,
            "fingerprint": fingerprint,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reproduce(schema: Dict[str, Any], seed: int | str, csv_path: str) -> Dict[str, Any]:
    try:
        normalized = validate_schema(dict(schema))
        df_expected = pd.read_csv(csv_path)
        df_actual, _ = generate_from_schema(normalized, seed=seed)

        equal = df_expected.equals(df_actual)
        result: Dict[str, Any] = {"ok": equal}
        if not equal:
            # Simple diff summary: show first differing row index and column
            diff_rows = []
            for i, (row_e, row_a) in enumerate(zip(df_expected.itertuples(index=False), df_actual.itertuples(index=False))):
                if row_e != row_a:
                    diff_rows.append(i)
                    break
            result["diff"] = {
                "first_mismatch_row": diff_rows[0] if diff_rows else None,
                "shape_expected": list(df_expected.shape),
                "shape_actual": list(df_actual.shape),
            }
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


