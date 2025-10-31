from __future__ import annotations

import hashlib
import random as py_random
from datetime import datetime, timedelta
from typing import List

import numpy as np
from faker import Faker


def _stable_hash_to_int(value: str, bits: int = 64) -> int:
    """Map a string to a stable non-negative integer within 2**bits.

    Uses SHA-256 and truncates to the requested bit width for portability.
    """
    h = hashlib.sha256(value.encode("utf-8")).digest()
    int_val = int.from_bytes(h, byteorder="big", signed=False)
    mask = (1 << bits) - 1
    return int_val & mask


def normalize_seed(seed_input: int | str) -> int:
    """Normalize user-provided seed (int or str) to a 64-bit integer.

    - For strings, compute SHA-256 and reduce to 64-bit via masking.
    - For ints, coerce to Python int and mask to 64-bit non-negative.
    """
    if isinstance(seed_input, str):
        return _stable_hash_to_int(seed_input, bits=64)
    # ensure deterministic 64-bit domain
    return int(seed_input) & ((1 << 64) - 1)


def init_seed(seed: int | str) -> np.random.Generator:
    """Initialize deterministic RNG state across Python random, NumPy, and Faker.

    - Accepts int or str seed; strings are mapped via stable hash to a 64-bit int.
    - Seeds `random`, `Faker`, and returns a NumPy `Generator` from default_rng.
    """
    int_seed = normalize_seed(seed)

    py_random.seed(int_seed)
    # Note: we do not mutate NumPy's legacy global state to avoid cross-talk;
    # callers should use the returned Generator.
    rng = np.random.default_rng(int_seed)
    Faker.seed(int_seed)
    return rng


def derive_subseed(master_seed: int, label: str) -> int:
    """Derive a deterministic sub-seed from a master seed and label.

    Combines the master integer seed with a label string using a stable hash,
    returning a 64-bit integer suitable for initializing separate RNGs.
    """
    master64 = normalize_seed(master_seed)
    mixed = f"{master64}::{label}"
    return _stable_hash_to_int(mixed, bits=64)


def safe_div(a, b) -> float:
    """Return a/b, or 0.0 if denominator is zero."""
    if b == 0:
        return 0.0
    return float(a) / float(b)


def percent(part, total) -> float:
    """Return percentage (0-100) or 0.0 if total is zero."""
    if total == 0:
        return 0.0
    return float(part) * 100.0 / float(total)


def sample_datetimes_uniform(start: datetime, end: datetime, n: int, rng: np.random.Generator) -> List[str]:
    """Sample n datetimes uniformly in [start, end] and return ISO strings.

    Handles swapped bounds and zero-span intervals deterministically.
    """
    if n <= 0:
        return []
    if end < start:
        start, end = end, start
    span_seconds = (end - start).total_seconds()
    if span_seconds == 0:
        return [start.isoformat() for _ in range(n)]
    u = rng.random(n)
    return [(start + timedelta(seconds=float(x) * span_seconds)).isoformat() for x in u]


def human_readable_bytes(n: int) -> str:
    """Convert byte count to human readable string with binary units."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(max(0, n))
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.2f} {units[idx]}"


# Backwards-compatible aliases (if previously used)
timedelta_random = None  # deprecated; use sample_datetimes_uniform
human_readable_size = human_readable_bytes


def deterministic_uuid(namespace_seed: int, index: int, name: str) -> str:
    """Create a deterministic UUID-like string from inputs using SHA-256.

    The function hashes the tuple (namespace_seed, index, name) and
    returns a UUID string built from the first 16 bytes of the digest.
    """
    ns64 = normalize_seed(namespace_seed)
    payload = f"{ns64}:{index}:{name}".encode("utf-8")
    dig = hashlib.sha256(payload).digest()
    # Construct a UUID from first 16 bytes for compactness
    import uuid as _uuid

    return str(_uuid.UUID(bytes=dig[:16]))


