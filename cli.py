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
        res = run_pipeline_from_schema(
            schema,
            seed=ns.seed,
            out_csv=ns.out,
            verbose=ns.verbose,
            source_csv=ns.source_csv,
            mode=ns.mode,
            target_rows=ns.target_rows,
            additional_rows=ns.additional_rows,
            force=getattr(ns, "force", False),
            progressive=getattr(ns, "progressive", False),
            use_crawl4ai=getattr(ns, "use_crawl4ai", False),
            crawl_timeout=getattr(ns, "crawl_timeout", 10),
            crawl_mode=getattr(ns, "crawl_mode", "cache"),
            crawl_bypass_cache=getattr(ns, "crawl_bypass_cache", False),
            evaluate_realism=getattr(ns, "evaluate_realism", False),
            reference_csv=getattr(ns, "reference_csv", None),
            simulate_privacy=getattr(ns, "simulate_privacy", False),
            privacy_reference_csv=getattr(ns, "privacy_reference_csv", None),
            quasi_identifiers=(ns.quasi_identifiers.split(',') if getattr(ns, 'quasi_identifiers', None) else None),
            privacy_noise_level=getattr(ns, "privacy_noise_level", 0.01),
            privacy_sample_size=getattr(ns, "privacy_sample_size", None),
            ml_benchmark=getattr(ns, "ml_benchmark", False),
            ml_target_column=getattr(ns, "ml_target_column", None),
            auto_adapt=getattr(ns, "auto_adapt", False),
            adapt_iterations=getattr(ns, "adapt_iterations", 5),
            adapt_budget=getattr(ns, "adapt_budget", 1000),
            adaptive_tune=getattr(ns, "adaptive_tune", False),
            tune_iterations=getattr(ns, "tune_iterations", 5),
            tune_budget=getattr(ns, "tune_budget", 5000),
            objective=getattr(ns, "objective", "balanced"),
        )
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
        ok = res.get("ok") and res.get("validation", {}).get("ok", False)
        rows = res.get("generation_report", {}).get("rows_generated", 0)
        realism = res.get("realism", {}).get("realism_score", 0.0)
        print(f"SMOKE: {'PASS' if ok else 'FAIL'} | rows={rows} realism={realism:.2f}")
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
    p_gen.add_argument("--source-csv", dest="source_csv", default=None)
    p_gen.add_argument("--mode", choices=["append", "augment"], default=None)
    p_gen.add_argument("--target-rows", type=int, default=None)
    p_gen.add_argument("--additional-rows", type=int, default=None)
    p_gen.add_argument("--progressive", action="store_true")
    p_gen.add_argument("--use-crawl4ai", action="store_true")
    p_gen.add_argument("--crawl-timeout", type=int, default=10)
    p_gen.add_argument("--crawl-mode", choices=["cache", "llm", "scrape", "upload"], default="cache")
    p_gen.add_argument("--crawl-bypass-cache", action="store_true")
    p_gen.add_argument("--evaluate-realism", action="store_true")
    p_gen.add_argument("--reference-csv", dest="reference_csv", default=None)
    p_gen.add_argument("--simulate-privacy", action="store_true")
    p_gen.add_argument("--privacy-reference-csv", dest="privacy_reference_csv", default=None)
    p_gen.add_argument("--privacy-noise-level", dest="privacy_noise_level", type=float, default=0.01)
    p_gen.add_argument("--privacy-sample-size", dest="privacy_sample_size", type=int, default=None)
    p_gen.add_argument("--quasi-identifiers", dest="quasi_identifiers", default=None)
    p_gen.add_argument("--ml-benchmark", action="store_true")
    p_gen.add_argument("--ml-target-column", dest="ml_target_column", default=None)
    p_gen.add_argument("--auto-adapt", action="store_true")
    p_gen.add_argument("--adapt-iterations", dest="adapt_iterations", type=int, default=5)
    p_gen.add_argument("--adapt-budget", dest="adapt_budget", type=int, default=1000)
    p_gen.add_argument("--adaptive-tune", action="store_true")
    p_gen.add_argument("--tune-iterations", dest="tune_iterations", type=int, default=5)
    p_gen.add_argument("--tune-budget", dest="tune_budget", type=int, default=5000)
    p_gen.add_argument("--objective", choices=["realism", "utility", "privacy", "balanced"], default="balanced")
    p_gen.add_argument("--force", action="store_true")
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

