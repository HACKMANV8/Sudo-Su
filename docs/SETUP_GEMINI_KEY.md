# Setting Gemini API Key in PowerShell

## Quick Setup (Current Session Only)

Run this in your PowerShell session:

```powershell
$env:GEMINI_API_KEY="AIzaSyBdAwAvxU4JJAiQwtjn1YtzIyeiuyc2v8I"
```

Then run your command:

```powershell
python -m cli generate --schema-file examples/simple_test_schema.json --target-rows 100 --use-llm-priors --llm-model gemini --seed test
```

## Permanent Setup (Recommended)

### Option 1: System Environment Variables (Windows)

1. Press `Win + X` → **System** → **Advanced system settings**
2. Click **Environment Variables**
3. Under **User variables**, click **New**
4. Variable name: `GEMINI_API_KEY`
5. Variable value: `AIzaSyBdAwAvxU4JJAiQwtjn1YtzIyeiuyc2v8I`
6. Click **OK** on all dialogs
7. **Restart your terminal/PowerShell** for changes to take effect

### Option 2: PowerShell Profile (Persists Across Sessions)

Add to your PowerShell profile:

```powershell
# Edit profile
notepad $PROFILE

# Add this line:
$env:GEMINI_API_KEY="AIzaSyBdAwAvxU4JJAiQwtjn1YtzIyeiuyc2v8I"
```

## Verify API Key is Set

```powershell
echo $env:GEMINI_API_KEY
```

Should display your API key.

## Test Command

```powershell
python -m cli generate `
  --schema-file examples/simple_test_schema.json `
  --target-rows 100 `
  --use-llm-priors `
  --llm-model gemini `
  --seed test
```

## Security Note

⚠️ **Never commit API keys to git!** Add to `.gitignore`:

```
.env
*.key
GEMINI_API_KEY
```

