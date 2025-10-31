from __future__ import annotations

import numpy as np
import pandas as pd

from openschema.metrics.realism import evaluate_realism


def test_realism_basic_scoring():
    rng = np.random.default_rng(0)
    n = 2000
    ref = pd.DataFrame({
        "x": rng.normal(0, 1, n),
        "y": rng.normal(10, 2, n),
        "role": rng.choice(["a", "b", "c"], size=n)
    })
    gen = pd.DataFrame({
        "x": rng.normal(0.1, 1.1, n),
        "y": rng.normal(9.8, 2.2, n),
        "role": rng.choice(["a", "b", "c"], size=n)
    })
    schema = {"fields": [
        {"name": "x", "type": "float"},
        {"name": "y", "type": "float"},
        {"name": "role", "type": "category"}
    ]}
    rep = evaluate_realism(gen, ref, schema)
    assert 0 <= rep["composite_score"] <= 100
    assert "x" in rep["feature_stats"] and "role" in rep["categorical_stats"]


def test_realism_identical_is_high():
    rng = np.random.default_rng(1)
    n = 1000
    ref = pd.DataFrame({
        "x": rng.normal(0, 1, n),
        "role": rng.choice(["a", "b"], size=n)
    })
    gen = ref.copy()
    schema = {"fields": [
        {"name": "x", "type": "float"},
        {"name": "role", "type": "category"}
    ]}
    rep = evaluate_realism(gen, ref, schema)
    assert rep["composite_score"] > 95


