from __future__ import annotations

import math
import random as py_random
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

import numpy as np
from faker import Faker


def init_seed(seed: int) -> np.random.Generator:
    """Seed Python's random, NumPy, and Faker; return a NumPy Generator.

    This ensures deterministic behavior across standard library `random`,
    NumPy RNG, and Faker outputs for a given seed.
    """
    # Seed stdlib random
    py_random.seed(seed)
    # Seed NumPy global RNG (legacy API) for code that may use np.random.*
    np.random.seed(seed)
    # Create and return a modern Generator
    rng = np.random.default_rng(seed)
    # Seed Faker global
    Faker.seed(seed)
    return rng


def safe_div(a, b):
    if b == 0:
        return 0
    return a / b


def percent(part, total) -> float:
    if total == 0:
        return 0.0
    return float(part) * 100.0 / float(total)


def timedelta_random(start: datetime, end: datetime, n: int, rng: np.random.Generator) -> List[datetime]:
    if n <= 0:
        return []
    if end < start:
        start, end = end, start
    span_seconds = (end - start).total_seconds()
    if span_seconds == 0:
        return [start for _ in range(n)]
    u = rng.random(n)
    return [start + timedelta(seconds=float(x) * span_seconds) for x in u]


def human_readable_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(max(0, num_bytes))
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.2f} {units[idx]}"


