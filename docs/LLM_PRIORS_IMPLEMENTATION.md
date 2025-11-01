# LLM Priors Extractor Implementation Summary

## Overview

Successfully integrated Gemini (and other LLM) support as a priors extractor for OpenSchema. The LLM is used **only** to produce priors (semantic distributions, conditional rules, example rows), which are then consumed by OpenSchema's deterministic generator to create reproducible datasets.

## Files Created/Modified

### New Files

1. **`openschema/llm/__init__.py`** - Package initialization
2. **`openschema/llm/gemini_client.py`** - LLM client wrapper supporting:
   - Gemini (via google-generativeai)
   - OpenAI (via openai)
   - Mock mode for testing
   - Async API calls
   - Error handling (LLMError, LLMNetworkError, LLMParseError)

3. **`openschema/llm/prior_extractor.py`** - Core extraction logic:
   - `LLMPriorsExtractor` class with caching
   - `extract_priors_from_description()` function
   - Prompt building from schema + description
   - JSON validation and parsing
   - PII redaction (email, phone, SSN, credit cards, IBAN)
   - Cache management with SHA256-based keys

4. **`examples/llm_prompts/priors_schema_prompt.json`** - Prompt template and few-shot examples

5. **`tests/test_llm_priors_extractor.py`** - Comprehensive tests:
   - Cache hit/miss tests
   - Parsing validation
   - PII redaction
   - Network error fallback
   - Integration smoke tests

### Modified Files

1. **`openschema/pipeline.py`**:
   - Added LLM priors extraction before generation
   - Merges priors into schema metadata
   - Includes `llm_priors_cache_key` in fingerprint
   - Stores LLM metadata in `generation_report['llm']`

2. **`cli.py`**:
   - Added flags: `--use-llm-priors`, `--llm-model`, `--llm-temperature`, `--llm-cache-dir`, `--llm-bypass-cache`, `--llm-max-tokens`

## Key Features

### 1. Deterministic & Reproducible
- All RNG uses `normalize_seed()`
- LLM responses cached with SHA256 keys
- Cache key included in pipeline fingerprint
- Same inputs → same cached priors → same generated data

### 2. Privacy-Safe
- PII redaction via regex patterns:
  - Emails: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
  - Phones: US-style patterns
  - SSN: `\b\d{3}-\d{2}-\d{4}\b`
  - Credit cards: 16-digit patterns
  - IBAN: Alphanumeric patterns
- Redaction counts tracked in `generation_report['llm']['redactions']`
- LLM prompt instructs no PII

### 3. Robust Error Handling
- Network errors → fallback to cache if available
- Invalid JSON → fallback to cache
- Parsing errors → fallback to relational_learner or schema-only generation
- All errors logged in `generation_report['llm']['warnings']`

### 4. Caching
- Cache directory: `~/.openschema/llm_cache/` (configurable)
- Cache key = SHA256(model + prompt_hash + schema_fp + description + sample_hash + params)
- Cache files: `{cache_key}.json`
- Bypass cache with `--llm-bypass-cache`

### 5. Priors JSON Schema
```json
{
  "schema_hint": { "columns": [...], "notes": "..." },
  "priors": {
    "<column>": {
      "type": "categorical|numeric|datetime|text",
      "categories": [...], "probs": [...],  // if categorical
      "distribution": { "type": "...", "params": {...} },  // if numeric
      "conditionals": [...],  // optional
      "examples": [...],  // optional
      "notes": "..."
    }
  },
  "dependencies": [{ "parent": "...", "child": "...", "explanation": "..." }],
  "examples": [{...}, ...]  // up to 50 example rows
}
```

## Usage Examples

### Basic Usage
```bash
python -m cli generate \
  --schema-file examples/ecommerce_fraud_schema.json \
  --target-rows 50000 \
  --use-llm-priors \
  --llm-model gemini \
  --llm-temperature 0.0 \
  --seed simba42
```

### With Reference CSV
```bash
python -m cli generate \
  --schema-file examples/ecommerce_fraud_schema.json \
  --target-rows 50000 \
  --use-llm-priors \
  --use-relational-generation \
  --reference-csv ecommerce_v2.csv \
  --llm-model gemini \
  --seed simba42
```

### Bypass Cache
```bash
python -m cli generate \
  --schema-file examples/ecommerce_fraud_schema.json \
  --use-llm-priors \
  --llm-bypass-cache
```

## Environment Variables

- `GEMINI_API_KEY` - Gemini API key (or `GEMINI_API_KEY` env var)
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI models)

## Integration Flow

1. **Schema Validation** → Normalized schema
2. **LLM Priors Extraction** (if `use_llm_priors=True`):
   - Build prompt from schema + description + optional sample CSV
   - Check cache
   - If not cached, call LLM
   - Validate and parse JSON response
   - Redact PII
   - Cache result
   - Merge priors into `schema['metadata']['llm_priors']`
3. **Relational Learning** (if `learn_relations=True` and reference CSV)
4. **Generation** (using relational generator if priors available)
5. **Fingerprinting** (includes `llm_priors_cache_key`)

## Testing

All tests in `tests/test_llm_priors_extractor.py`:
- ✅ Cache hit/miss
- ✅ Valid priors parsing
- ✅ Invalid JSON fallback
- ✅ PII redaction
- ✅ Network error fallback
- ✅ Integration smoke tests

Run: `pytest tests/test_llm_priors_extractor.py -v`

## Acceptance Criteria Status

✅ **1. Tests pass**: All tests in `test_llm_priors_extractor.py` passing  
✅ **2. CLI integration**: `--use-llm-priors` produces `generation_report['llm']`  
✅ **3. Caching**: Cached priors used on subsequent runs unless bypassed  
⏳ **4. Data alignment**: Generator consumption of LLM priors (format conversion needed)  
✅ **5. PII redaction**: Enforced and recorded in `redactions` metadata  

## Next Steps / Future Improvements

1. **LLM Priors Format Conversion**: Currently LLM priors are stored but not directly consumed by relational generator (needs format adapter)
2. **CLI Preview Command**: `python -m cli llm-priors --schema-file X --out priors.json` (optional)
3. **Telemetry**: Optional token usage tracking (if user consents)
4. **Local LLM Support**: Add support for local LLMs (Ollama, etc.)

## Notes

- LLM calls are expensive - always cache!
- Use `temperature=0.0` for reproducible priors
- PII redaction is a safety net - LLM prompt also instructs no PII
- Cache keys ensure reproducibility across runs
- Generator remains fully deterministic - LLM only affects priors extraction

