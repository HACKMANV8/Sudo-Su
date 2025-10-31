#!/bin/bash
# Quick 2-minute OpenSchema demo

set -e

echo "🚀 OpenSchema Quick Demo"
echo "========================"

# 1. Generate reference data
echo ""
echo "📊 Step 1: Generate reference dataset..."
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 500 \
  --seed reference-42 \
  --out demo_ref.csv

# 2. Generate initial synthetic
echo ""
echo "🔄 Step 2: Generate initial synthetic data..."
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 1000 \
  --seed demo-42 \
  --evaluate-realism \
  --reference-csv demo_ref.csv \
  --out demo_initial.csv

# 3. Show adaptive tuning (the key feature)
echo ""
echo "🎯 Step 3: Adaptive tuning (balanced objective)..."
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --target-rows 2000 \
  --seed demo-42 \
  --adaptive-tune \
  --tune-iterations 2 \
  --tune-budget 1000 \
  --objective balanced \
  --reference-csv demo_ref.csv \
  --out demo_tuned.csv

echo ""
echo "✅ Demo complete! Check: demo_ref.csv, demo_initial.csv, demo_tuned.csv"

