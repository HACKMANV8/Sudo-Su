# LLM Setup Guide

## Setting Up Gemini API Key

### Option 1: Environment Variable (Recommended)

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="AIzaSyDZ10YYFoP-AgcrW9MXzk3syyWzBj9defs"
```

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=AIzaSyDZ10YYFoP-AgcrW9MXzk3syyWzBj9defs
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="AIzaSyDZ10YYFoP-AgcrW9MXzk3syyWzBj9defs"
```

### Option 2: System Environment Variables

1. Open System Properties → Environment Variables
2. Add new User variable:
   - Name: `GEMINI_API_KEY`
   - Value: Your API key

### Option 3: In .env file (if using python-dotenv)

Create a `.env` file in project root:
```
GEMINI_API_KEY=AIzaSyDZ10YYFoP-AgcrW9MXzk3syyWzBj9defs
```

## Installing Dependencies

```bash
pip install google-generativeai  # For Gemini
pip install openai  # For OpenAI (optional)
```

## Getting Your API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Copy and set it as environment variable

## Testing the Setup

```bash
python -m cli generate \
  --schema-file examples/ecommerce_fraud_schema.json \
  --target-rows 100 \
  --use-llm-priors \
  --llm-model gemini \
  --seed test
```

## Security Notes

⚠️ **Important**: 
- Never commit API keys to version control
- Use environment variables, not hardcoded keys
- Rotate keys if exposed
- The `.env.example` file is for reference only (no real keys)

## Troubleshooting

- **ModuleNotFoundError**: Install `google-generativeai`
- **API Key Error**: Check environment variable is set correctly
- **Network Error**: Check internet connection and API quota

