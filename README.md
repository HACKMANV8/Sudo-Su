OpenSchema core engine: generate reproducible synthetic datasets from normalized schema JSON (no NLP included). It provides a schema model/validation layer, deterministic utilities and seeding, a vectorized data generator with conditional sampling and CSV augmentation, a validation/realism scoring module, a pipeline orchestrator, a CLI, and a minimal backend scaffold.

Install:

```bash
pip install -r requirements.txt
```

Smoke demo:

```bash
python cli.py smoke
```

Generate example (append to target rows from CSV):

```bash
python -m cli generate \
  --schema-file examples/example_schema_samples.json \
  --source-csv data/input.csv --mode append --target-rows 10000 \
  --seed demo --out data/output.csv
```

Determinism & seeds: You can pass an int or string seed; strings are normalized via SHA-256 to a 64-bit integer. Sub-seeds are derived per subsystem/field to avoid cross-talk. Reports include `normalized_seed`, `schema_hash`, `csv_hash`, and a combined `fingerprint` for exact run identification.

Note: NLP → schema handled externally by teammate.

Hackathon acceptance:
- All tests `pytest` pass
- `python cli.py smoke` prints PASS

Reproducibility and seeds:
- You can pass an int or string seed. Strings are normalized via SHA-256 to a 64-bit integer.
- Sub-seeds are derived per subsystem/field to avoid cross-talk.
- The generator report includes `normalized_seed`, `schema_hash`, `csv_hash`, and a combined `fingerprint` for exact run identification.

"""OpenSchema core engine package (skeleton).

This repository hosts the core engine foundation. NLP-to-Schema is assumed
to be provided externally and integrated at higher layers.
"""

__all__: list[str] = []

# Sudo-Su