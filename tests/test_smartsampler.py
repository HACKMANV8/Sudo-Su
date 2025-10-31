from __future__ import annotations

import numpy as np
import pandas as pd

from openschema.optimizer.smartsampler import smart_adapt


def _toy_generator(schema, n):
    rng = np.random.default_rng(0)
    # schema unused in toy; produce simple relation label = (x+y>0)
    x = rng.normal(0, 1, size=n)
    y = rng.normal(0, 1, size=n)
    label = (x + y > 0).astype(int)
    return pd.DataFrame({"x": x, "y": y, "label": label})


def test_smart_adapt_history_length():
    rng = np.random.default_rng(1)
    ref = pd.DataFrame({
        "x": rng.normal(0, 1, size=400),
        "y": rng.normal(0, 1, size=400),
        "label": (rng.normal(0, 1, size=400) > 0).astype(int),
    })
    schema = {"fields": [
        {"name": "x", "type": "float", "mean": 0.0, "std": 1.0},
        {"name": "y", "type": "float", "mean": 0.0, "std": 1.0},
        {"name": "label", "type": "category", "categories": [0,1], "probs": [0.5,0.5]},
    ]}
    res = smart_adapt(schema, ref, _toy_generator, target_column="label", iterations=2, budget=300, seed=0)
    # history includes baseline + iterations
    assert len(res["history"]) == 1 + 2

