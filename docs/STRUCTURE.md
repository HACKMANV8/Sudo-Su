# Repository Structure

This document describes the organization of the OpenSchema repository.

## Directory Structure

```
Sudo-Su/
├── openschema/          # Core Python package
│   ├── generator/       # Data generation modules
│   ├── learners/        # Prior learning from reference data
│   ├── llm/             # LLM integration (Gemini, etc.)
│   ├── optimizer/       # Adaptive tuning and optimization
│   ├── metrics/         # Evaluation metrics (realism, etc.)
│   ├── privacy/         # Privacy simulation
│   ├── benchmark/       # ML benchmarking
│   ├── connectors/      # External integrations (Crawl4AI)
│   └── ...
├── backend/             # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API routes
│   │   └── services/    # Business logic
│   └── tests/           # Backend tests
├── frontend/             # React frontend application
│   ├── src/
│   │   ├── components/  # React components
│   │   └── firebase/    # Firebase configuration
│   └── ...
├── examples/            # Example schemas and prompts
│   └── llm_prompts/      # LLM prompt templates
├── scripts/             # Utility scripts and demos
│   ├── demo_*.py        # Demonstration scripts
│   └── *.ps1            # PowerShell utilities
├── tests/                # Test suite
├── data/                 # Reference data (gitignored)
│   └── *.csv            # Reference datasets
├── output/               # Generated outputs (gitignored)
│   └── *.csv            # Generated synthetic datasets
└── docs/                 # Documentation
    ├── README.md        # Documentation index
    └── *.md             # Various guides and docs
```

## Key Files

- `cli.py` - Command-line interface entry point
- `README.md` - Main project README
- `requirements.txt` - Python dependencies
- `.gitignore` - Git ignore rules

## Data Organization

### `data/` Directory
- Contains reference CSV files used for learning priors, benchmarking, etc.
- Files are gitignored
- Example: `ecommerce_transactions.csv`, `ecommerce_v2.csv`

### `output/` Directory
- Contains generated synthetic datasets
- All CSV outputs are gitignored
- Includes demo outputs and test files

### `docs/` Directory
- All project documentation
- Setup guides, implementation notes, troubleshooting
- See `docs/README.md` for index

## Package Structure

### `openschema/`
Core package with modular components:

- **generator/** - Data generation
  - `generator.py` - Main generator
  - `relational_generator.py` - Relational/correlated generation

- **learners/** - Prior learning
  - `relational_learner.py` - Learn from reference CSV

- **llm/** - LLM integration
  - `gemini_client.py` - Gemini API client
  - `prior_extractor.py` - Extract priors from LLM
  - `prior_converter.py` - Convert LLM priors to internal format

- **optimizer/** - Optimization
  - `adaptive_engine.py` - Adaptive tuning loop
  - `smartsampler.py` - SmartSampler auto-adaptation

- **metrics/** - Evaluation
  - `realism.py` - Realism metrics

- **privacy/** - Privacy
  - `simulation.py` - Privacy risk simulation

- **benchmark/** - ML Benchmarking
  - `ml_benchmark.py` - ML utility evaluation

## Backend Structure

### `backend/app/`
FastAPI application with:
- REST API routes in `api/v1/routes/`
- Service layer in `services/`
- Main application in `main.py`

## Frontend Structure

### `frontend/`
React application with:
- Components in `src/components/`
- Firebase integration in `src/firebase/`
- Main entry in `src/main.jsx`

## Scripts

### `scripts/`
Utility and demonstration scripts:
- `demo_complete.py` - Complete feature demonstration
- `demo_full.py` - Full pipeline demo
- `evaluate_*.py` - Evaluation scripts
- `*.ps1` - PowerShell utilities

## Tests

### `tests/`
Comprehensive test suite:
- Unit tests for each module
- Integration tests
- Smoke tests

## Best Practices

1. **CSV Files**: Always place generated CSVs in `output/` and reference data in `data/`
2. **Documentation**: Add new docs to `docs/` and update `docs/README.md`
3. **Scripts**: New utility scripts go in `scripts/`
4. **Tests**: Follow existing test patterns in `tests/`

