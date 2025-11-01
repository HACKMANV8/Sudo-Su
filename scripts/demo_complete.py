#!/usr/bin/env python3
"""
Complete OpenSchema Demo - Showcases All Features
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openschema.pipeline import run_pipeline_from_schema
from openschema.schema_model import load_schema_from_file


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(res: dict, label: str = ""):
    if not res.get("ok"):
        print(f"[X] {label} FAILED: {res.get('error', 'unknown')}")
        return False
    
    gen = res.get("generation_report", {})
    val = res.get("validation", {})
    
    print(f"[OK] {label}")
    print(f"   Rows: {gen.get('rows_generated', 0)}")
    print(f"   Validation: {'OK' if val.get('ok') else 'FAIL'}")
    
    # Realism
    realism = gen.get("realism", {})
    if isinstance(realism, dict):
        score = realism.get('composite_score', realism.get('realism_score', 0))
        print(f"   Realism Score: {score:.2f}/100")
    
    return True


def safe_get(d: dict, *keys, default=0):
    """Safely get nested dict value."""
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, {})
        else:
            return default
    return d if d else default


def main():
    print_section("OpenSchema Complete Feature Demo")
    print("\nThis demo showcases:")
    print("  1. Basic Data Generation")
    print("  2. LLM Priors Extraction")
    print("  3. Relational Learning & Generation")
    print("  4. Realism Evaluation")
    print("  5. Privacy Simulation")
    print("  6. ML Utility Benchmarking")
    print("  7. Adaptive Tuning")
    
    # Load simple schema
    schema_file = "examples/simple_test_schema.json"
    if not Path(schema_file).exists():
        print(f"\n[X] Schema file not found: {schema_file}")
        return 1
    
    schema = load_schema_from_file(schema_file)
    print(f"\n[Schema] {schema.get('name', 'Unknown')}")
    print(f"  Fields: {len(schema.get('fields', []))}")
    
    # Step 1: Basic Generation
    print_section("Step 1: Basic Generation (No Enhancements)")
    basic_res = run_pipeline_from_schema(
        schema,
        seed="demo-basic",
        target_rows=200,
        out_csv="demo_basic.csv",
    )
    if not print_result(basic_res, "Basic Generation"):
        return 1
    
    # Step 2: Generate Reference Data
    print_section("Step 2: Generate Reference Dataset")
    ref_schema = schema.copy()
    ref_schema["n_rows"] = 300
    ref_res = run_pipeline_from_schema(
        ref_schema,
        seed="demo-reference",
        target_rows=300,
        out_csv="demo_reference.csv",
    )
    if not print_result(ref_res, "Reference Dataset"):
        return 1
    
    # Step 3: LLM Priors
    print_section("Step 3: LLM Priors Extraction")
    print("   [Note: Requires GEMINI_API_KEY environment variable]")
    llm_res = run_pipeline_from_schema(
        schema,
        seed="demo-llm",
        target_rows=200,
        reference_csv="demo_reference.csv",
        use_llm_priors=True,
        llm_model="gemini",
        llm_max_tokens=16384,
        out_csv="demo_llm.csv",
    )
    if print_result(llm_res, "LLM-Powered Generation"):
        llm_info = llm_res.get("generation_report", {}).get("llm", {})
        if llm_info.get("used"):
            print(f"   LLM Model: {llm_info.get('model', 'N/A')}")
            print(f"   Cache Key: {llm_info.get('priors_cache_key', 'N/A')[:30]}...")
            if llm_info.get("redactions", {}).get("performed"):
                print(f"   PII Redactions: Yes")
        else:
            print(f"   LLM: Not used (fallback to standard generation)")
    
    # Step 4: Relational Learning & Generation
    print_section("Step 4: Relational Learning & Generation")
    rel_res = run_pipeline_from_schema(
        schema,
        seed="demo-relational",
        target_rows=200,
        reference_csv="demo_reference.csv",
        learn_relations=True,
        use_relational_generation=True,
        rel_min_samples=10,
        out_csv="demo_relational.csv",
    )
    if print_result(rel_res, "Relational Generation"):
        rel_info = rel_res.get("generation_report", {}).get("relational", {})
        if rel_info.get("learned"):
            print(f"   Relational Learning: Success")
            print(f"   Cache Key: {rel_info.get('cache_key', 'N/A')[:30]}...")
            if rel_info.get("generation"):
                print(f"   Relational Generation: Success")
            warnings = rel_info.get("warnings", [])
            if warnings:
                print(f"   Warnings: {len(warnings)}")
    
    # Step 5: Full Evaluation Suite
    print_section("Step 5: Full Evaluation (Realism + Privacy + ML)")
    eval_res = run_pipeline_from_schema(
        schema,
        seed="demo-eval",
        target_rows=200,
        reference_csv="demo_reference.csv",
        evaluate_realism=True,
        simulate_privacy=True,
        privacy_reference_csv="demo_reference.csv",
        privacy_sample_size=100,
        ml_benchmark=True,
        ml_target_column="salary",  # Note: may not work for all schemas
        out_csv="demo_evaluated.csv",
    )
    if print_result(eval_res, "Full Evaluation"):
        gen_rep = eval_res.get("generation_report", {})
        
        # Realism
        realism = gen_rep.get("realism", {})
        if isinstance(realism, dict):
            print(f"   Realism Score: {safe_get(realism, 'composite_score', default=0):.2f}/100")
            metrics = realism.get("metrics", {})
            if metrics:
                print(f"   Metrics: KS={safe_get(metrics, 'ks_statistic', default=0):.3f}, "
                      f"EMD={safe_get(metrics, 'emd_score', default=0):.3f}")
        
        # Privacy
        privacy = gen_rep.get("privacy_simulation", {})
        if isinstance(privacy, dict):
            reid_rate = privacy.get("reidentification_rate", 0) * 100
            print(f"   Privacy Risk: {reid_rate:.1f}% reidentification rate")
        
        # ML Utility
        ml_bench = gen_rep.get("ml_benchmark", {})
        if isinstance(ml_bench, dict):
            test_score = ml_bench.get("real_test_score", 0)
            is_class = ml_bench.get("is_classification", False)
            if is_class:
                print(f"   ML Utility: {test_score*100:.1f}% accuracy")
            else:
                print(f"   ML Utility: RMSE={test_score:.2f}")
    
    # Step 6: Adaptive Tuning
    print_section("Step 6: Adaptive Tuning (Balanced Objective)")
    print("   [Running 2 iterations for demo - may take a moment...]")
    adaptive_res = run_pipeline_from_schema(
        schema,
        seed="demo-adaptive",
        target_rows=200,
        reference_csv="demo_reference.csv",
        adaptive_tune=True,
        tune_iterations=2,
        tune_budget=100,
        objective="balanced",
        ml_target_column="salary",
        out_csv="demo_adaptive.csv",
    )
    if print_result(adaptive_res, "Adaptive Tuning"):
        adapt_info = adaptive_res.get("generation_report", {}).get("adaptive_tuning", {})
        history = adapt_info.get("history", [])
        if history:
            print(f"   Iterations: {len(history)}")
            if len(history) >= 2:
                first = history[0]
                last = history[-1]
                print(f"   Initial Objective: {first.get('objective', 0):.2f}")
                print(f"   Final Objective: {last.get('objective', 0):.2f}")
                improvement = last.get('objective', 0) - first.get('objective', 0)
                print(f"   Improvement: {improvement:+.2f}")
    
    # Summary
    print_section("Summary - Generated Files")
    files = [
        "demo_basic.csv",
        "demo_reference.csv",
        "demo_llm.csv",
        "demo_relational.csv",
        "demo_evaluated.csv",
        "demo_adaptive.csv",
    ]
    
    for f in files:
        path = Path(f)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            rows = len(pd.read_csv(path))
            print(f"  [OK] {f:30s} - {rows:4d} rows, {size_kb:6.1f} KB")
        else:
            print(f"  [X] {f:30s} - Not found")
    
    # Feature Matrix
    print_section("Feature Matrix")
    print("\nFeature                    | Status")
    print("-" * 60)
    print("Basic Generation           | [OK]")
    print("LLM Priors Extraction      | " + ("[OK]" if llm_res.get("ok") else "[--]"))
    print("Relational Learning        | " + ("[OK]" if rel_res.get("ok") else "[--]"))
    print("Relational Generation      | " + ("[OK]" if rel_res.get("ok") else "[--]"))
    print("Realism Evaluation        | " + ("[OK]" if eval_res.get("ok") else "[--]"))
    print("Privacy Simulation         | " + ("[OK]" if eval_res.get("ok") else "[--]"))
    print("ML Benchmarking            | " + ("[OK]" if eval_res.get("ok") else "[--]"))
    print("Adaptive Tuning            | " + ("[OK]" if adaptive_res.get("ok") else "[--]"))
    
    print_section("Demo Complete!")
    print("\nAll major features demonstrated successfully!")
    print("\nNext Steps:")
    print("  1. Inspect generated CSV files")
    print("  2. Check artifacts in /tmp/openschema_artifacts/")
    print("  3. Try your own schemas")
    print("  4. Experiment with different objectives and parameters")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

