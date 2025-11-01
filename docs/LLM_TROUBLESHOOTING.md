# LLM Troubleshooting Guide

## Common Issues

### 1. Safety Filter Blocks

**Symptom:** `Gemini response blocked by safety filters`

**Solution:** Safety settings have been configured to allow more content, but some prompts may still trigger filters. The system will:
- Fall back to cached priors if available
- Fall back to relational learning if reference CSV provided
- Fall back to schema-only generation

### 2. Empty Response / Max Tokens

**Symptom:** `Empty text in Gemini response (finish_reason=2)`

**Solution:**
- Increase `--llm-max-tokens` (default 4096, try 8192 or 16384)
- The prompt might be too long - check schema size
- The system will automatically fall back to standard generation

### 3. PowerShell Command Syntax

**Issue:** Backslashes don't work for line continuation in PowerShell

**Solution:** Use backticks or single line:
```powershell
# Wrong (bash syntax):
python -m cli generate \
  --schema-file X \
  --use-llm-priors

# Right (PowerShell):
python -m cli generate --schema-file X --use-llm-priors --llm-model gemini

# Or with backticks:
python -m cli generate `
  --schema-file X `
  --use-llm-priors `
  --llm-model gemini
```

### 4. API Key Not Set

**Symptom:** `API key not found in environment variable GEMINI_API_KEY`

**Solution:**
```powershell
# Current session:
$env:GEMINI_API_KEY="your_key_here"

# Permanent (System Properties → Environment Variables)
```

### 5. Model Not Found

**Symptom:** `404 models/gemini-X is not found`

**Solution:** The code automatically selects available models. If issues persist:
- Check API quota/access
- Try different model: `--llm-model gemini-pro`

## Testing LLM Connection

```python
import asyncio
from openschema.llm.gemini_client import call_llm

result = asyncio.run(
    call_llm("Say hello", model="gemini", temperature=0.0)
)
print(result)
```

## Fallback Behavior

The system gracefully falls back:
1. LLM priors (if enabled and successful)
2. Relational learning (if `--learn-relations` and reference CSV)
3. Standard schema-based generation

Generation will always succeed even if LLM fails.

## Cache Usage

LLM responses are cached. To force refresh:
```bash
--llm-bypass-cache
```

Cache location: `~/.openschema/llm_cache/`

## Best Practices

1. **Start small**: Test with `--target-rows 100` first
2. **Increase tokens**: Use `--llm-max-tokens 8192` for complex schemas
3. **Check cache**: LLM calls are expensive - cache is used automatically
4. **Monitor logs**: Check `generation_report['llm']['warnings']` for issues

