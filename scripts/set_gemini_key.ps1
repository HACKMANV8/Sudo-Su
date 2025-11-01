# PowerShell script to set Gemini API key
# Run this before generating data with LLM priors

$env:GEMINI_API_KEY="AIzaSyDZ10YYFoP-AgcrW9MXzk3syyWzBj9defs"

Write-Host ""
Write-Host "Gemini API key set for this session." -ForegroundColor Green
Write-Host "API Key: $($env:GEMINI_API_KEY.Substring(0,20))..." -ForegroundColor Gray
Write-Host ""
Write-Host "Next: Run your generate command" -ForegroundColor Yellow
Write-Host "Example: python -m cli generate --schema-file examples/simple_test_schema.json --target-rows 100 --use-llm-priors --llm-model gemini --seed test" -ForegroundColor Cyan
Write-Host ""

