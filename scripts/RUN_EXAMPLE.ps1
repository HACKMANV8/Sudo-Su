# Complete example: Set API key and generate data
# Run this entire script

# Set API key
$env:GEMINI_API_KEY="AIzaSyDZ10YYFoP-AgcrW9MXzk3syyWzBj9defs"

Write-Host "🚀 Generating data with LLM priors..." -ForegroundColor Cyan

# Run generation
python -m cli generate `
  --schema-file examples/simple_test_schema.json `
  --target-rows 100 `
  --use-llm-priors `
  --llm-model gemini `
  --seed test `
  --out test_output.csv

Write-Host "`n✅ Done! Check test_output.csv" -ForegroundColor Green

