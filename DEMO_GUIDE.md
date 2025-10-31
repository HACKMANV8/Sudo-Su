# OpenSchema Demo Guide

## Quick Start (5-Minute Demo)

### 1. Basic Generation
```bash
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 1000 \
  --seed demo \
  --out demo_output.csv
```

**What to show:**
- CSV generated with proper structure
- Validation passes
- Realism score displayed
- Fingerprint for reproducibility

---

### 2. Realism Evaluation (with reference data)
```bash
# First, create a reference dataset
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 500 \
  --seed reference \
  --out demo_reference.csv

# Then evaluate against it
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 1000 \
  --seed demo \
  --evaluate-realism \
  --reference-csv demo_reference.csv \
  --out demo_synthetic.csv
```

**What to show:**
- `generation_report['realism']` with composite score
- Feature-by-feature breakdown
- KS statistics, EMD, Spearman correlation

---

### 3. Privacy Risk Simulation
```bash
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 1000 \
  --simulate-privacy \
  --privacy-reference-csv demo_reference.csv \
  --privacy-sample-size 500 \
  --quasi-identifiers user_age,purchase_amount,category \
  --out demo_private.csv
```

**What to show:**
- `generation_report['privacy_simulation']` with reidentification rate
- Privacy-utility tradeoff plot (if generated)
- Rate before/after noise addition

---

### 4. ML Utility Benchmark
```bash
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 1000 \
  --ml-benchmark \
  --ml-target-column is_fraud \
  --reference-csv demo_reference.csv \
  --out demo_ml.csv
```

**What to show:**
- `generation_report['ml_benchmark']` with train/test scores
- Classification accuracy or regression RMSE
- Confusion matrix (if classification)

---

### 5. Adaptive Tuning (THE KEY FEATURE)

**Full balanced optimization:**
```bash
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 5000 \
  --adaptive-tune \
  --tune-iterations 3 \
  --tune-budget 2000 \
  --objective balanced \
  --ml-target-column is_fraud \
  --reference-csv demo_reference.csv \
  --out demo_tuned.csv
```

**What to show:**
- `generation_report['adaptive_tuning']`:
  - `history`: per-iteration scores
  - `best_params`: optimized schema
  - `final_generation_report`: combined metrics
- Improvement in balanced objective (0.45×realism + 0.35×utility - 0.20×privacy)
- Compare initial vs. final metrics

**Different objectives:**
```bash
# Maximize realism
--objective realism

# Maximize ML utility
--objective utility

# Maximize privacy (minimize risk)
--objective privacy

# Balanced (default)
--objective balanced
```

---

## Full Demo Script (Automated)

Run the complete demo:
```bash
python scripts/demo_full.py
```

This script:
1. Generates a reference dataset
2. Creates initial synthetic data
3. Runs adaptive tuning
4. Shows before/after comparison
5. Lists generated files and artifacts

---

## Demo Checklist

### Before Demo:
- [ ] Run `pytest -q` - all tests pass
- [ ] Run `python -m cli smoke` - smoke test passes
- [ ] Check artifacts directory exists: `/tmp/openschema_artifacts/`
- [ ] Prepare example schema (or use `examples/example_schema_samples.json`)

### During Demo (5 min):

**Minute 1: Problem & Solution**
- "We generate synthetic data that balances realism, utility, and privacy"
- Show schema structure

**Minute 2: Basic Generation**
```bash
python -m cli generate --schema-file examples/example_schema_samples.json --target-rows 1000 --seed demo
```
- Show CSV output
- Explain reproducibility (seed → fingerprint)

**Minute 3: Evaluation Features**
- Show realism evaluation
- Show privacy simulation
- Show ML benchmark

**Minute 4: Adaptive Tuning (THE KEY)**
```bash
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --adaptive-tune \
  --tune-iterations 3 \
  --objective balanced \
  --reference-csv demo_reference.csv
```
- Show history of improvements
- Show final balanced score
- Explain the 0.45/0.35/0.20 weighting

**Minute 5: Results & Artifacts**
- Show generated CSV
- Show artifacts (if time)
- Explain fingerprint reproducibility

---

## Quick Command Reference

### Essential Flags:
- `--schema-file`: JSON schema path
- `--target-rows`: Number of rows to generate
- `--seed`: Reproducibility seed (int or string)
- `--out`: Output CSV path

### Evaluation Flags:
- `--evaluate-realism --reference-csv <path>`: Compare to reference
- `--simulate-privacy --privacy-reference-csv <path>`: Privacy risk
- `--ml-benchmark --ml-target-column <col> --reference-csv <path>`: ML utility

### Optimization Flags:
- `--adaptive-tune`: Run adaptive tuning
- `--tune-iterations N`: Number of iterations (default: 5)
- `--tune-budget N`: Rows per iteration (default: 5000)
- `--objective balanced|realism|utility|privacy`: Objective function

### Crawl4AI Flags (optional):
- `--use-crawl4ai`: Enable web scraping
- `--crawl-mode cache|llm|scrape`: Mode selection
- `--crawl-timeout N`: Timeout in seconds

---

## Troubleshooting

**"No module named openschema"**
- Run from project root
- Or: `python -m cli` instead of `python cli.py`

**"Reference CSV not found"**
- Generate reference first, or use existing CSV

**"Adaptive tuning failed"**
- Ensure `--reference-csv` is provided
- Check that target column exists in schema
- Reduce `--tune-budget` if too slow

**"Tests failing"**
- Run `pytest -q` to see which
- Most common: missing dependencies (scipy, scikit-learn)

---

## Success Criteria

✅ All tests pass (`pytest -q`)  
✅ Smoke test passes (`python -m cli smoke`)  
✅ Can generate data from schema  
✅ Adaptive tuning produces improvement in objective score  
✅ Generated CSV is valid and realistic

