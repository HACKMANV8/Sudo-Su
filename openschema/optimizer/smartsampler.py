from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from ..benchmark.ml_benchmark import evaluate_ml_utility


def _tweak_schema(schema: Dict[str, Any], rng: np.random.Generator, alpha: float = 0.05) -> Dict[str, Any]:
    sc = copy.deepcopy(schema)
    for f in sc.get("fields", []):
        t = f.get("type")
        if t in {"int", "float"}:
            for k in ("mean", "std", "min", "max"):
                if k in f and isinstance(f[k], (int, float)):
                    f[k] = float(f[k]) * (1.0 + rng.uniform(-alpha, alpha))
        if t == "category" and f.get("categories") and f.get("probs"):
            p = np.array(f["probs"], dtype=float)
            noise = rng.uniform(-alpha, alpha, size=len(p))
            p = np.clip(p + noise, 0.0, None)
            s = p.sum() or 1.0
            f["probs"] = (p / s).tolist()
    return sc


def smart_adapt(
    schema: Dict[str, Any],
    reference_df: pd.DataFrame,
    generator_callable: Callable[[Dict[str, Any], int], pd.DataFrame],
    target_column: str,
    iterations: int = 5,
    budget: int = 10000,
    seed: int = 0,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    best_schema = copy.deepcopy(schema)
    history: List[Dict[str, Any]] = []

    # Baseline
    df0 = generator_callable(best_schema, budget)
    base = evaluate_ml_utility(df0, reference_df, target_column, seed=seed)
    best_score = float(base.get("real_test_score", 0.0))
    history.append({"iter": 0, "score": best_score})

    for i in range(1, iterations + 1):
        cand = _tweak_schema(best_schema, rng, alpha=0.1)
        df = generator_callable(cand, budget)
        res = evaluate_ml_utility(df, reference_df, target_column, seed=seed)
        score = float(res.get("real_test_score", 0.0))
        history.append({"iter": i, "score": score})
        if score > best_score:
            best_score = score
            best_schema = cand
    rec = "Consider adopting best_params into schema to improve ML utility" if best_score > history[0]["score"] else "No improvement observed under current budget"
    return {"best_params": best_schema, "history": history, "recommendation": rec}


