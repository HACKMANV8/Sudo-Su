# OpenSchema Quick Start Guide

## 🚀 Simple Test

### 1. Set API Key (PowerShell)
```powershell
$env:GEMINI_API_KEY="AIzaSyBdAwAvxU4JJAiQwtjn1YtzIyeiuyc2v8I"
```

### 2. Generate Data
```powershell
python -m cli generate `
  --schema-file examples/simple_test_schema.json `
  --target-rows 100 `
  --use-llm-priors `
  --llm-model gemini `
  --seed test
```

## 📊 What You Get

- **Simple Employee Dataset**: 4 fields (ID, department, salary, experience)
- **Realistic Distributions**: Proper category frequencies and numeric ranges
- **LLM-Enhanced Priors** (optional): Better semantic understanding
- **Always Works**: Falls back gracefully if LLM unavailable

## ✅ Success Indicators

```
Generated 100 rows | seed=...
Validation: OK | Realism: 1.00
CSV: output.csv
```

## 📁 Schema Location

`examples/simple_test_schema.json` - Simple 4-field employee schema

## 🔧 Common Commands

**Basic generation:**
```powershell
python -m cli generate --schema-file examples/simple_test_schema.json --target-rows 100
```

**With LLM priors:**
```powershell
python -m cli generate --schema-file examples/simple_test_schema.json --target-rows 100 --use-llm-priors --llm-model gemini
```

**With relational learning:**
```powershell
python -m cli generate --schema-file examples/simple_test_schema.json --target-rows 100 --learn-relations --use-relational-generation --reference-csv data.csv
```

## 💡 Tips

1. **Start simple**: Use `simple_test_schema.json` first
2. **LLM optional**: Works great without LLM too
3. **Seed matters**: Same seed = same data (deterministic)
4. **Check output**: Always verify `Validation: OK`

## 🎯 Next Steps

- Try with your own schema
- Experiment with different objectives (`--objective realism|utility|privacy|balanced`)
- Use relational learning with reference data
- Combine features: `--use-llm-priors --learn-relations --use-relational-generation`

