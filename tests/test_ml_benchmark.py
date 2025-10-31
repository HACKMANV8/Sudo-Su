from __future__ import annotations

import numpy as np
import pandas as pd

from openschema.benchmark.ml_benchmark import evaluate_ml_utility


def test_evaluate_ml_utility_keys():
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({
        "x": rng.normal(0, 1, size=500),
        "y": rng.normal(2, 1.5, size=500),
        "label": rng.integers(0, 2, size=500)
    })
    synth = pd.DataFrame({
        "x": ref["x"] + rng.normal(0, 0.1, size=500),
        "y": ref["y"] + rng.normal(0, 0.1, size=500),
        "label": ref["label"]
    })
    res = evaluate_ml_utility(synth, ref, target_column="label", seed=1)
    for k in ["synthetic_train_score", "real_test_score", "delta", "execution_time_seconds"]:
        assert k in res

