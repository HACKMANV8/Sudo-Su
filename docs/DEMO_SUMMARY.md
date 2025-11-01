# OpenSchema Demo - What to Do

## TL;DR - The 30-Second Answer

**Show this:** Adaptive tuning that balances realism, utility, and privacy.

**Command:**
```bash
# Generate reference first
python -m cli generate --schema-file examples/example_schema_samples.json \
  --target-rows 500 --seed ref --out demo_ref.csv

# Run adaptive tuning
python -m cli generate --schema-file examples/example_schema_samples.json \
  --target-rows 2000 --adaptive-tune --tune-iterations 3 \
  --objective balanced --reference-csv demo_ref.csv --out demo_tuned.csv
```

**What to point out:**
- `generation_report['adaptive_tuning']['history']` shows improvement over iterations
- Final objective score combines: 45% realism + 35% utility - 20% privacy risk
- Generated CSV is optimized for the balanced objective

---

## Full Demo Flow (5 Minutes)

### Option 1: Automated Script
```bash
python scripts/demo_full.py
```
This runs everything and shows before/after metrics.

### Option 2: Manual Step-by-Step
See `DEMO_GUIDE.md` for detailed commands.

---

## What Makes This Impressive

1. **Multi-Objective Optimization**
   - Not just generating data, but optimizing it
   - Balances 3 competing goals: realism vs utility vs privacy

2. **Iterative Improvement**
   - Shows history of attempts
   - Demonstrates convergence toward better solution

3. **Reproducibility**
   - Same seed → same output
   - Fingerprint for exact run identification

4. **Production-Ready**
   - Comprehensive validation
   - Privacy simulation
   - ML utility benchmarking
   - Realism metrics

---

## Key Features to Highlight

✅ **Adaptive Tuning** - The star feature  
✅ **Realism Evaluation** - Statistical comparison to reference  
✅ **Privacy Simulation** - Reidentification risk assessment  
✅ **ML Benchmarking** - Utility for machine learning  
✅ **Reproducibility** - Deterministic seeds and fingerprints  
✅ **Crawl4AI Integration** - Web-scraped priors (optional)

---

## Common Questions

**Q: What does "balanced" objective mean?**  
A: Weighted sum: 0.45×realism + 0.35×utility - 0.20×privacy_risk  
   (Higher is better, privacy risk is minimized)

**Q: How long does adaptive tuning take?**  
A: Depends on `tune_iterations` × `tune_budget`. For 3 iterations × 2000 rows ≈ 30-60 seconds.

**Q: Can I use my own schema?**  
A: Yes! Just create a JSON file with the schema format (see `examples/example_schema_samples.json`).

**Q: What if I don't have a reference CSV?**  
A: Generate one first, or skip evaluation features (they won't run).

---

## Success Looks Like

✅ Command runs without errors  
✅ `generation_report['adaptive_tuning']` is present  
✅ `history` shows improvement in objective score  
✅ Generated CSV is valid and has expected columns  
✅ Final metrics show better balance than initial

