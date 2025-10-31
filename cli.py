import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from openschema.schema_model import load_schema_from_file, validate_schema, schema_summary
from openschema.pipeline import run_pipeline_from_schema
from openschema.validator import validate_dataframe, generate_validation_report


def _print(obj, verbose: bool) -> None:
    if verbose:
        print(json.dumps(obj, indent=2, default=str))


def cmd_generate(ns: argparse.Namespace) -> int:
    try:
        schema = load_schema_from_file(ns.schema_file)
        if ns.confirm_schema:
            norm = validate_schema(schema)
            print(schema_summary(norm))
            return 0
        res = run_pipeline_from_schema(schema, seed=ns.seed, out_csv=ns.out, verbose=ns.verbose)
        if not res.get("ok"):
            print(f"ERROR: {res.get('error')}")
            return 1
        print(f"Generated {res['generation_report']['rows_generated']} rows | seed={res['generation_report'].get('normalized_seed', res['generation_report'].get('seed'))}")
        print(f"Validation: {'OK' if res['validation']['ok'] else 'FAIL'} | Realism: {res['realism']['realism_score']:.2f}")
        if res.get("csv_path"):
            print(f"CSV: {res['csv_path']}")
        _print(res if ns.verbose else {
            "fingerprint": res.get("fingerprint"),
            "schema_name": res["schema"].get("name"),
            "rows": res["generation_report"]["rows_generated"],
        }, ns.verbose)
        return 0 if res["validation"]["ok"] else 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def cmd_validate(ns: argparse.Namespace) -> int:
    try:
        schema = load_schema_from_file(ns.schema_file)
        norm = validate_schema(schema)
        df = pd.read_csv(ns.csv)
        res = validate_dataframe(df, norm)
        report = generate_validation_report(df, norm)
        print(report)
        return 0 if res["ok"] else 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def cmd_smoke(ns: argparse.Namespace) -> int:
    try:
        ex_path = Path("examples/example_schema_samples.json")
        data = json.loads(Path(ex_path).read_text(encoding="utf-8"))
        if isinstance(data, list):
            schema = dict(data[0])
        else:
            schema = dict(data)
        schema["n_rows"] = 100
        res = run_pipeline_from_schema(schema, seed="smoke")
        ok = res.get("ok") and res["validation"]["ok"]
        print(f"SMOKE: {'PASS' if ok else 'FAIL'} | rows={res['generation_report']['rows_generated']} realism={res['realism']['realism_score']:.2f}")
        if ns.verbose:
            _print(res, True)
        return 0 if ok else 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="openschema", description="OpenSchema Core Engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Generate data from schema")
    p_gen.add_argument("--schema-file", required=True, dest="schema_file")
    p_gen.add_argument("--seed", default=42)
    p_gen.add_argument("--out", dest="out", default=None)
    p_gen.add_argument("--confirm-schema", action="store_true", dest="confirm_schema")
    p_gen.add_argument("--verbose", action="store_true")
    p_gen.set_defaults(func=cmd_generate)

    p_val = sub.add_parser("validate", help="Validate CSV against schema")
    p_val.add_argument("--csv", required=True)
    p_val.add_argument("--schema-file", required=True, dest="schema_file")
    p_val.add_argument("--verbose", action="store_true")
    p_val.set_defaults(func=cmd_validate)

    p_smoke = sub.add_parser("smoke", help="Run smoke test on example schema")
    p_smoke.add_argument("--verbose", action="store_true")
    p_smoke.set_defaults(func=cmd_smoke)

    ns = parser.parse_args()
    rc = ns.func(ns)
    sys.exit(rc)


if __name__ == "__main__":
    main()

