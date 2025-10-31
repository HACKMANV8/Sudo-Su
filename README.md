OpenSchema core engine: generate reproducible synthetic datasets from normalized schema JSON (no NLP included).

pip install -r requirements.txt

python cli.py smoke

NL→schema handled externally by teammate.

Determinism: utilities seed Python `random`, NumPy `default_rng`, and `Faker` using stable hashing for string seeds.

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