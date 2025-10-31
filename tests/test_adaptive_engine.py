from __future__ import annotations

import numpy as np
import pandas as pd

from openschema.optimizer.adaptive_engine import run_adaptive_tuning


def _toy_generator(schema, n):
    rng = np.random.default_rng(0)
    x = rng.normal(float(schema['fields'][0].get('mean', 0.0)), float(schema['fields'][0].get('std', 1.0)), size=n)
    y = rng.normal(float(schema['fields'][1].get('mean', 0.0)), float(schema['fields'][1].get('std', 1.0)), size=n)
    label = (x + y > 0).astype(int)
    return pd.DataFrame({"x": x, "y": y, "label": label}), {}


def test_adaptive_engine_history_and_params():
    rng = np.random.default_rng(1)
    ref = pd.DataFrame({
        "x": rng.normal(0, 1, size=400),
        "y": rng.normal(0, 1, size=400),
        "label": (rng.normal(0, 1, size=400) > 0).astype(int),
    })
    schema = {"name": "toy", "fields": [
        {"name": "x", "type": "float", "mean": 0.0, "std": 1.0},
        {"name": "y", "type": "float", "mean": 0.0, "std": 1.0},
        {"name": "label", "type": "category", "categories": [0,1], "probs": [0.5, 0.5]},
    ]}
    res = run_adaptive_tuning(schema, ref, _toy_generator, objective='balanced', iterations=2, budget=300, seed=0, ml_target_column='label')
    assert len(res["history"]) == 1 + 2
    assert res["best_params"] and isinstance(res["best_params"], dict)

