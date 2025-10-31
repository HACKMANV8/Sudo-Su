# OpenSchema Project Status

## What This Project Does

**OpenSchema** is a synthetic data generation system that:
1. **Generates** synthetic datasets from JSON schemas
2. **Evaluates** how realistic the data is (vs. reference data)
3. **Simulates** privacy risks (reidentification)
4. **Benchmarks** ML utility (train on synthetic, test on real)
5. **Optimizes** all three together using adaptive tuning

Think of it as: "Generate fake data that's realistic, private, AND useful for ML."

---

## Project Structure

```
openschema/
├── generator.py          # Core data generation
├── validator.py          # Schema validation
├── pipeline.py          # Orchestrates everything
├── metrics/
│   └── realism.py       # Statistical comparison to reference
├── privacy/
│   └── simulation.py    # Reidentification risk assessment
├── benchmark/
│   └── ml_benchmark.py  # ML utility testing
└── optimizer/
    ├── smartsampler.py  # ML-only optimization
    └── adaptive_engine.py  # Multi-objective optimization
```

---

## Current Bugs

### 1. Missing `logging` import ✅ FIXED
- **Location**: `openschema/pipeline.py`
- **Fix**: Added `import logging`

### 2. "'bool' object is not callable" ❌ NEEDS FIX
- **Likely location**: `explain_label_simple` call or field type handling
- **Symptoms**: Crashes during realism evaluation
- **Needs investigation**: Check if field type is being confused with boolean value

### 3. Unicode emoji errors ✅ FIXED
- **Location**: `scripts/demo_full.py`
- **Fix**: Replaced all emojis with ASCII alternatives

---

## What Works

✅ Basic data generation from schema
✅ Schema validation
✅ CSV output
✅ Reproducibility (seeds)
✅ Most tests pass (35/35)

---

## What's Broken

❌ Full demo script crashes during realism evaluation
❌ Adaptive tuning may have issues if realism fails
❌ Some features untested in integration

---

## How to Use (When Fixed)

### Basic generation:
```bash
python -m cli generate --schema-file examples/example_schema_samples.json --target-rows 1000
```

### Full pipeline:
```bash
# 1. Generate reference
python -m cli generate --schema-file schema.json --target-rows 500 --out ref.csv

# 2. Generate + evaluate
python -m cli generate --schema-file schema.json \
  --target-rows 1000 \
  --evaluate-realism --reference-csv ref.csv \
  --simulate-privacy --privacy-reference-csv ref.csv \
  --ml-benchmark --ml-target-column target_col

# 3. Adaptive tuning (THE KEY FEATURE)
python -m cli generate --schema-file schema.json \
  --target-rows 5000 \
  --adaptive-tune --tune-iterations 3 \
  --objective balanced \
  --reference-csv ref.csv
```

---

## Next Steps to Fix

1. ✅ Fix logging import (DONE)
2. ❌ Debug the 'bool' object error
3. ❌ Test full pipeline end-to-end
4. ❌ Simplify demo script to handle errors gracefully

