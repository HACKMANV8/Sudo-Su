# OpenSchema

A powerful engine for generating reproducible synthetic datasets from normalized schema JSON. OpenSchema provides deterministic data generation with support for conditional sampling, relational generation, ML benchmarking, privacy simulation, and LLM-powered priors extraction.

## Features

- **Schema-Driven Generation**: Generate data from JSON schemas with support for multiple field types
- **Deterministic & Reproducible**: Seed-based generation ensures exact reproducibility
- **Relational Generation**: Preserve conditional relationships and correlations from reference data
- **LLM Integration**: Extract priors and conditional rules using Gemini or other LLMs
- **ML Benchmarking**: Evaluate synthetic data utility for machine learning tasks
- **Privacy Simulation**: Assess re-identification risk in synthetic datasets
- **Adaptive Tuning**: Iteratively optimize generation parameters based on multiple objectives
- **Crawl4AI Integration**: Enrich schemas with real-world priors from web scraping

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Generation

```bash
python -m cli generate \
  --schema-file examples/simple_test_schema.json \
  --target-rows 1000 \
  --seed demo \
  --out output/generated.csv
```

### With LLM Priors

```bash
# Set your Gemini API key
$env:GEMINI_API_KEY="your-api-key"

python -m cli generate \
  --schema-file examples/simple_test_schema.json \
  --target-rows 1000 \
  --use-llm-priors \
  --seed demo \
  --out output/generated.csv
```

### Relational Generation

```bash
python -m cli generate \
  --schema-file examples/ecommerce_fraud_schema.json \
  --target-rows 1000 \
  --learn-relations \
  --use-relational-generation \
  --reference-csv data/ecommerce_transactions.csv \
  --seed demo \
  --out output/relational.csv
```

### Smoke Test

```bash
python cli.py smoke
```

## Project Structure

```
Sudo-Su/
├── openschema/          # Core package
│   ├── generator/       # Data generators
│   ├── learners/        # Prior learning modules
│   ├── llm/             # LLM integration
│   ├── optimizer/       # Adaptive tuning
│   ├── metrics/         # Evaluation metrics
│   ├── privacy/         # Privacy simulation
│   └── ...
├── examples/            # Example schemas and prompts
├── scripts/             # Utility scripts
├── tests/               # Test suite
├── data/                # Reference data (gitignored)
├── output/              # Generated outputs (gitignored)
└── docs/                # Documentation
```

## Determinism & Reproducibility

OpenSchema uses seed-based generation for full reproducibility:

- **Seeds**: Accept integers or strings (normalized via SHA-256)
- **Sub-seeds**: Derived per subsystem/field to avoid cross-talk
- **Fingerprints**: Reports include `normalized_seed`, `schema_hash`, `csv_hash`, and combined `fingerprint`

## Documentation

See the `docs/` directory for detailed guides:
- `QUICK_START.md` - Quick start guide
- `SETUP_LLM.md` - LLM integration setup
- `DEMO_GUIDE.md` - Demo scripts guide
- And more...

## CLI Usage

```bash
python -m cli generate --help
```

Key flags:
- `--schema-file`: Path to schema JSON
- `--target-rows`: Number of rows to generate
- `--seed`: Seed for reproducibility
- `--use-llm-priors`: Enable LLM priors extraction
- `--learn-relations`: Learn from reference CSV
- `--use-relational-generation`: Use relational generator
- `--adaptive-tune`: Enable adaptive parameter tuning
- `--ml-benchmark`: Run ML utility evaluation

## Testing

```bash
pytest tests/
```

## License

See LICENSE file for details.
