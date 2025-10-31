# Sudo-Su

## Configuration

This project reads environment variables from a local `.env` file (not committed).

1. Copy the example and add your key:
	- `cp .env.example .env`
	- Edit `.env` and set `GOOGLE_API_KEY="your_key_here"` (or `GEMINI_API_KEY`).

2. Keep secrets out of git:
	- `.env` is already in `.gitignore`.
	- Don’t commit real keys; only commit `.env.example`.

## Run

Activate your virtual environment and run the pipeline:

```
python main.py
```

Outputs are written to `data/processed_data.csv` and `data/expanded_dataset_gemini.csv`.