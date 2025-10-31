from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from openschema.learners.relational_learner import RelationalLearner
from openschema.generator.relational_generator import generate_relational


@pytest.fixture
def toy_reference_csv(tmp_path):
    """Create a toy reference CSV with dependencies."""
    csv_path = tmp_path / "reference.csv"
    
    # Create realistic data with dependencies
    rng = np.random.default_rng(42)
    n = 500
    
    # Department -> salary dependency
    departments = rng.choice(["engineering", "sales", "hr"], size=n, p=[0.5, 0.3, 0.2])
    salaries = []
    for dept in departments:
        if dept == "engineering":
            salaries.append(rng.normal(120000, 20000))
        elif dept == "sales":
            salaries.append(rng.normal(80000, 15000))
        else:  # hr
            salaries.append(rng.normal(70000, 10000))
    
    # Correlated numerics: age and experience
    age = rng.normal(35, 10, size=n)
    experience = age - 20 + rng.normal(0, 2, size=n)  # Strong correlation
    
    df = pd.DataFrame({
        "department": departments,
        "salary": salaries,
        "age": age,
        "experience": experience,
        "location": rng.choice(["NYC", "SF", "Austin"], size=n, p=[0.4, 0.4, 0.2]),
    })
    
    df.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def toy_schema():
    """Create a toy schema matching the reference data."""
    return {
        "name": "toy_hr",
        "n_rows": 1000,
        "fields": [
            {"name": "department", "type": "category", "categories": ["engineering", "sales", "hr"]},
            {"name": "salary", "type": "float", "min": 40000, "max": 200000},
            {"name": "age", "type": "int", "min": 22, "max": 65},
            {"name": "experience", "type": "float", "min": 0, "max": 40},
            {"name": "location", "type": "category", "categories": ["NYC", "SF", "Austin"]},
        ],
        "metadata": {
            "dependency_graph": [
                {"parent": "department", "child": "salary"},
            ],
        },
    }


def test_relational_learner_fit(toy_reference_csv, toy_schema):
    """Test RelationalLearner.fit produces expected keys."""
    learner = RelationalLearner(min_samples=10, smoothing_alpha=1.0)
    schema_fp = "test_fingerprint_123"
    
    result = learner.fit(toy_reference_csv, toy_schema, schema_fp, seed=42)
    
    assert "version" in result
    assert "categorical_priors" in result
    assert "conditional_numeric" in result
    assert "global_numeric" in result
    assert "copula_corr" in result
    assert "warnings" in result
    
    # Check categorical priors
    assert "department" in result["categorical_priors"]
    assert "categories" in result["categorical_priors"]["department"]
    assert "probs" in result["categorical_priors"]["department"]
    
    # Check conditional numeric (salary depends on department)
    assert "salary" in result["conditional_numeric"]
    assert "department" in result["conditional_numeric"]["salary"]
    
    # Check global numeric stats
    assert "salary" in result["global_numeric"]
    assert "mean" in result["global_numeric"]["salary"]
    
    # Check copula correlation
    if result["copula_corr"]:
        assert isinstance(result["copula_corr"], dict) or isinstance(result["copula_corr"], list)


def test_relational_generator_dependencies(toy_reference_csv, toy_schema):
    """Test relational generator preserves department->salary dependency."""
    learner = RelationalLearner(min_samples=10, smoothing_alpha=1.0)
    schema_fp = "test_fp_456"
    learned_priors = learner.fit(toy_reference_csv, toy_schema, schema_fp, seed=42)
    
    # Generate data
    df_gen, report = generate_relational(toy_schema, n_rows=500, seed=42, learned_priors=learned_priors)
    
    assert len(df_gen) == 500
    assert "department" in df_gen.columns
    assert "salary" in df_gen.columns
    
    # Check that mean salary per department is within reasonable range of learned means
    # Engineering should have highest salary
    dept_means = df_gen.groupby("department")["salary"].mean()
    
    eng_mean = dept_means.get("engineering", 0)
    sales_mean = dept_means.get("sales", 0)
    hr_mean = dept_means.get("hr", 0)
    
    # Learned priors should have engineering > sales > hr
    learned_salary_stats = learned_priors["conditional_numeric"]["salary"]["department"]
    learned_eng = learned_salary_stats.get("engineering", {}).get("mean", 0)
    learned_sales = learned_salary_stats.get("sales", {}).get("mean", 0)
    
    # Generated means should be within ±30% of learned (allowing for variance)
    assert abs(eng_mean - learned_eng) / learned_eng < 0.3, f"Engineering salary mismatch: {eng_mean} vs {learned_eng}"
    assert abs(sales_mean - learned_sales) / learned_sales < 0.3, f"Sales salary mismatch: {sales_mean} vs {learned_sales}"
    
    # Engineering should be highest
    assert eng_mean > sales_mean > hr_mean, "Department salary order not preserved"


def test_relational_generator_copula_correlation(toy_reference_csv, toy_schema):
    """Test copula preserves Spearman correlation between numeric columns."""
    learner = RelationalLearner(min_samples=10, smoothing_alpha=1.0)
    schema_fp = "test_fp_789"
    learned_priors = learner.fit(toy_reference_csv, toy_schema, schema_fp, seed=42)
    
    # Generate data
    df_gen, report = generate_relational(toy_schema, n_rows=500, seed=42, learned_priors=learned_priors)
    
    # Check correlation between age and experience
    from scipy.stats import spearmanr
    corr_gen, _ = spearmanr(df_gen["age"], df_gen["experience"])
    
    # Reference correlation should be high (we created it that way)
    ref_df = pd.read_csv(toy_reference_csv)
    corr_ref, _ = spearmanr(ref_df["age"], ref_df["experience"])
    
    # Generated correlation should be positive and similar sign
    assert corr_gen > 0, "Generated correlation should be positive"
    assert abs(corr_gen - corr_ref) < 0.2, f"Correlation mismatch: {corr_gen} vs {corr_ref}"


def test_relational_pipeline_end_to_end(toy_reference_csv, toy_schema, tmp_path):
    """Test full pipeline with relational learning and generation."""
    from openschema.pipeline import run_pipeline_from_schema
    
    out_csv = str(tmp_path / "output.csv")
    
    result = run_pipeline_from_schema(
        toy_schema,
        seed=42,
        out_csv=out_csv,
        target_rows=500,
        reference_csv=toy_reference_csv,
        learn_relations=True,
        use_relational_generation=True,
        rel_min_samples=10,
    )
    
    assert result.get("ok"), f"Pipeline failed: {result.get('error')}"
    
    gen_report = result.get("generation_report", {})
    relational_info = gen_report.get("relational", {})
    
    assert relational_info.get("learned"), "Relational learning should succeed"
    assert relational_info.get("generation"), "Relational generation should succeed"
    assert "cache_key" in relational_info
    
    # Check output file
    df_out = pd.read_csv(out_csv)
    assert len(df_out) == 500
    assert "department" in df_out.columns
    assert "salary" in df_out.columns


def test_relational_determinism(toy_reference_csv, toy_schema, tmp_path):
    """Test that same seed produces identical output."""
    from openschema.pipeline import run_pipeline_from_schema
    
    out1 = str(tmp_path / "out1.csv")
    out2 = str(tmp_path / "out2.csv")
    
    result1 = run_pipeline_from_schema(
        toy_schema,
        seed=42,
        out_csv=out1,
        target_rows=100,
        reference_csv=toy_reference_csv,
        learn_relations=True,
        use_relational_generation=True,
    )
    
    result2 = run_pipeline_from_schema(
        toy_schema,
        seed=42,
        out_csv=out2,
        target_rows=100,
        reference_csv=toy_reference_csv,
        learn_relations=True,
        use_relational_generation=True,
    )
    
    assert result1.get("ok") and result2.get("ok")
    
    df1 = pd.read_csv(out1)
    df2 = pd.read_csv(out2)
    
    # DataFrames should be identical (deterministic)
    pd.testing.assert_frame_equal(df1, df2)


def test_relational_fallback_insufficient_samples(toy_reference_csv, toy_schema):
    """Test fallback when conditional branch has insufficient samples."""
    learner = RelationalLearner(min_samples=1000, smoothing_alpha=1.0)  # High threshold
    schema_fp = "test_fp_fallback"
    
    result = learner.fit(toy_reference_csv, toy_schema, schema_fp, seed=42)
    
    # Should have warnings about insufficient samples
    warnings = result.get("warnings", [])
    assert len(warnings) > 0, "Should have warnings for insufficient samples"
    
    # Generation should still work (uses global fallback)
    df_gen, report = generate_relational(toy_schema, n_rows=100, seed=42, learned_priors=result)
    assert len(df_gen) == 100
    assert "salary" in df_gen.columns


def test_relational_cache(toy_reference_csv, toy_schema):
    """Test that learner cache works correctly."""
    learner = RelationalLearner(min_samples=10, smoothing_alpha=1.0)
    schema_fp = "test_cache_123"
    
    # First call
    result1 = learner.fit(toy_reference_csv, toy_schema, schema_fp, seed=42)
    
    # Second call should use cache
    import time
    t0 = time.time()
    result2 = learner.fit(toy_reference_csv, toy_schema, schema_fp, seed=42)
    t1 = time.time()
    
    # Should be very fast (cache hit)
    assert t1 - t0 < 0.1, "Cache should be fast"
    
    # Results should be identical
    assert result1["cache_key"] == result2["cache_key"]

