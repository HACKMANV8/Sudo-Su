# Developer Notes / Roadmap

## Near-term features
- LLM integration guide: Plug NL→schema at `openschema.schema_model.validate_schema` boundary. Provide an adapter layer that maps LLM outputs into normalized schema dict; avoid coupling core to model serving.
- CTGAN/SDV integration plan: Add `openschema/models/` with pluggable generators. Keep current deterministic path as default; allow `mode: 'model'` with model+params. Benchmark and expose config through CLI and backend workers.
- CSV-augmentation plugin design: Define `Augmentor` interface to register feature-specific augmentation (e.g., datetime jitter, geo IP enrichment). Load via entry points or local registry.
- Privacy & differential privacy checklist: k-anonymity thresholding, column masking, regex redaction for emails/phones, DP noise addition for numeric columns, config gates and audit logs.

## Reliability & ops
- Celery job orchestration: retries, idempotent uploads, webhook backoff
- Structured logging + Sentry DSN from env
- Metrics: rows/sec, job durations, histogram buckets

## Backlog
- Date domain inference from CSV for smarter min/max
- More conditional mappings (department→salary bands)
- Better uniqueness enforcement strategies
