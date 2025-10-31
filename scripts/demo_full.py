#!/usr/bin/env python3
"""
Full OpenSchema Demo Script
Shows end-to-end pipeline with adaptive tuning
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openschema.pipeline import run_pipeline_from_schema


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result_summary(res: dict, label: str = ""):
    if not res.get("ok"):
        print(f"[X] {label} FAILED: {res.get('error', 'unknown')}")
        return
    gen = res.get("generation_report", {})
    val = res.get("validation", {})
    real = res.get("realism", {})
    
    print(f"[OK] {label}")
    print(f"   Rows: {gen.get('rows_generated', 0)}")
    print(f"   Validation: {'OK' if val.get('ok') else 'FAIL'}")
    # Realism might be in different places
    realism_score = 0.0
    if isinstance(real, dict):
        realism_score = real.get('realism_score', 0.0)
    elif isinstance(gen.get("realism"), dict):
        realism_score = gen.get("realism", {}).get("composite_score", 0.0)
    print(f"   Realism: {realism_score:.2f}/100")
    
    # Adaptive tuning results
    if "adaptive_tuning" in gen:
        adapt = gen["adaptive_tuning"]
        history = adapt.get("history", [])
        if history:
            first = history[0]
            last = history[-1]
            print(f"   [*] Adaptive Tuning:")
            print(f"      Initial objective: {first.get('objective', 0):.2f}")
            print(f"      Final objective: {last.get('objective', 0):.2f}")
            print(f"      Improvement: {last.get('objective', 0) - first.get('objective', 0):+.2f}")


def main():
    print_section("OpenSchema Full Demo")
    
    # Step 1: Create a demo schema
    schema = {
        "name": "demo_ecommerce",
        "description": "E-commerce transactions with fraud detection",
        "n_rows": 5000,
        "fields": [
            {"name": "order_id", "type": "string", "format": "uuid", "unique": True},
            {"name": "user_age", "type": "int", "min": 18, "max": 80, "mean": 35, "std": 12},
            {"name": "purchase_amount", "type": "float", "min": 10, "max": 1000, "mean": 150, "std": 80},
            {"name": "category", "type": "category", "categories": ["electronics", "clothing", "food", "books"], "probs": [0.3, 0.3, 0.25, 0.15]},
            {"name": "is_fraud", "type": "bool"},
            {"name": "purchased_at", "type": "datetime"},
        ],
    }
    
    print("\n[Schema]")
    print(json.dumps(schema, indent=2, default=str))
    
    # Step 2: Generate baseline (reference-like data)
    print_section("Step 1: Generate Baseline Reference Dataset")
    ref_schema = schema.copy()
    ref_schema["n_rows"] = 2000  # Smaller reference
    
    ref_res = run_pipeline_from_schema(
        ref_schema,
        seed="reference-seed-42",
        out_csv="demo_reference.csv",
    )
    print_result_summary(ref_res, "Baseline Generation")
    
    if not ref_res.get("ok"):
        print("[X] Failed to generate reference. Exiting.")
        return 1
    
    # Step 3: Generate initial synthetic (no tuning)
    print_section("Step 2: Generate Initial Synthetic (No Tuning)")
    initial_res = run_pipeline_from_schema(
        schema,
        seed="demo-42",
        out_csv="demo_initial.csv",
        evaluate_realism=True,
        reference_csv="demo_reference.csv",
        simulate_privacy=True,
        privacy_reference_csv="demo_reference.csv",
        privacy_sample_size=500,
        ml_benchmark=True,
        ml_target_column="is_fraud",
    )
    print_result_summary(initial_res, "Initial Generation")
    
    # Extract metrics (with safe defaults)
    gen_initial = initial_res.get("generation_report", {})
    real_initial = gen_initial.get("realism", {}).get("composite_score", 0) if isinstance(gen_initial.get("realism"), dict) else 0
    priv_initial = gen_initial.get("privacy_simulation", {}).get("reidentification_rate", 0) * 100 if isinstance(gen_initial.get("privacy_simulation"), dict) else 0
    util_initial = gen_initial.get("ml_benchmark", {}).get("real_test_score", 0) * 100 if isinstance(gen_initial.get("ml_benchmark"), dict) else 0
    
    print(f"   [Metrics]")
    print(f"      Realism: {real_initial:.1f}/100")
    print(f"      Privacy Risk: {priv_initial:.1f}%")
    print(f"      ML Utility: {util_initial:.1f}%")
    
    # Step 4: Adaptive tuning
    print_section("Step 3: Adaptive Tuning (Balanced Objective)")
    print("   [Running 3 iterations of adaptive optimization...]")
    
    tuned_res = run_pipeline_from_schema(
        schema,
        seed="demo-42",
        out_csv="demo_tuned.csv",
        target_rows=5000,
        evaluate_realism=True,
        reference_csv="demo_reference.csv",
        simulate_privacy=True,
        privacy_reference_csv="demo_reference.csv",
        privacy_sample_size=500,
        ml_benchmark=True,
        ml_target_column="is_fraud",
        adaptive_tune=True,
        tune_iterations=3,
        tune_budget=2000,
        objective="balanced",
    )
    print_result_summary(tuned_res, "Adaptive Tuned Generation")
    
    # Extract final metrics (with safe defaults)
    gen_tuned = tuned_res.get("generation_report", {})
    adapt_info = gen_tuned.get("adaptive_tuning", {})
    history = adapt_info.get("history", []) if isinstance(adapt_info, dict) else []
    
    if history:
        fgr = adapt_info.get("final_generation_report", {})
        final_real = fgr.get("realism", {}).get("composite_score", 0) if isinstance(fgr.get("realism"), dict) else 0
        final_priv = fgr.get("privacy", {}).get("reidentification_rate", 0) * 100 if isinstance(fgr.get("privacy"), dict) else 0
        final_util = fgr.get("utility", {}).get("real_test_score", 0) * 100 if isinstance(fgr.get("utility"), dict) else 0
        
        print(f"   [Final Metrics]")
        print(f"      Realism: {final_real:.1f}/100")
        print(f"      Privacy Risk: {final_priv:.1f}%")
        print(f"      ML Utility: {final_util:.1f}%")
        
        print(f"\n   [Improvement Summary]")
        print(f"      Realism: {real_initial:.1f} → {final_real:.1f} ({final_real - real_initial:+.1f})")
        print(f"      Privacy Risk: {priv_initial:.1f}% → {final_priv:.1f}% ({final_priv - priv_initial:+.1f}%)")
        print(f"      ML Utility: {util_initial:.1f}% → {final_util:.1f}% ({final_util - util_initial:+.1f}%)")
    
    # Step 5: Show files
    print_section("Step 4: Generated Files")
    files = ["demo_reference.csv", "demo_initial.csv", "demo_tuned.csv"]
    for f in files:
        path = Path(f)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"   [OK] {f} ({size_kb:.1f} KB)")
        else:
            print(f"   [X] {f} (missing)")
    
    # Artifacts
    print_section("Step 5: Artifacts & Reports")
    fingerprint = tuned_res.get("fingerprint", "")
    print(f"   Fingerprint: {fingerprint}")
    print(f"   Artifacts: /tmp/openschema_artifacts/{fingerprint.replace(':', '_')}/images/")
    
    print_section("Demo Complete! [OK]")
    print("\n[Next Steps]")
    print("   1. Inspect generated CSVs: demo_reference.csv, demo_initial.csv, demo_tuned.csv")
    print("   2. Check artifacts for visualizations")
    print("   3. Try different objectives: --objective realism|utility|privacy")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

