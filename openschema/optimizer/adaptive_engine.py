from __future__ import annotations

import copy
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..metrics.realism import evaluate_realism
from ..privacy.simulation import simulate_privacy_risk
from ..benchmark.ml_benchmark import evaluate_ml_utility


def _safe_schema_params(schema: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(schema)


def _tweak_params(schema: Dict[str, Any], rng: np.random.Generator, alpha: float = 0.08) -> Dict[str, Any]:
    sc = copy.deepcopy(schema)
    for f in sc.get("fields", []):
        t = f.get("type")
        if t in {"int", "float"}:
            if isinstance(f.get("mean"), (int, float)):
                f["mean"] = float(f["mean"]) * (1.0 + float(rng.uniform(-alpha, alpha)))
            if isinstance(f.get("std"), (int, float)):
                f["std"] = max(1e-9, float(f["std"]) * (1.0 + float(rng.uniform(-alpha, alpha))))
            # keep min/max sane
            if isinstance(f.get("min"), (int, float)) and isinstance(f.get("max"), (int, float)):
                if f["min"] > f["max"]:
                    f["min"], f["max"] = f["max"], f["min"]
        elif t == "category" and f.get("categories") and f.get("probs"):
            p = np.array(list(f["probs"]), dtype=float)
            noise = rng.uniform(-alpha, alpha, size=p.shape)
            p = np.clip(p + noise, 1e-12, None)
            p = p / p.sum()
            f["probs"] = p.tolist()
    return sc


def _normalize_utility_score(report: Dict[str, Any]) -> float:
    # Classification accuracy in [0,1] -> [0,100]; regression negative RMSE -> map to [0,100] heuristically
    s = float(report.get("real_test_score", 0.0))
    if report.get("is_classification", True):
        return max(0.0, min(100.0, 100.0 * s))
    # assume s is -RMSE; cap at RMSE in [0, 10] -> score [100..0]
    rmse = -s
    return float(max(0.0, min(100.0, 100.0 * (1.0 - (rmse / 10.0)))))


def _privacy_risk_to_score(report: Dict[str, Any]) -> float:
    # Higher is worse; convert rate in [0,1] to [0,100]
    rate = float(report.get("reidentification_rate", 0.0))
    return float(max(0.0, min(100.0, 100.0 * rate)))


def _objective_score(objective: str, realism_score: float, utility_score: float, privacy_risk_score: float) -> float:
    if objective == "realism":
        return realism_score
    if objective == "utility":
        return utility_score
    if objective == "privacy":
        # Invert risk for privacy objective (lower risk = higher score)
        return 100.0 - privacy_risk_score
    # balanced
    return 0.45 * realism_score + 0.35 * utility_score - 0.20 * privacy_risk_score


def run_adaptive_tuning(
    schema: Dict[str, Any],
    reference_df: pd.DataFrame,
    generator_callable: Callable[[Dict[str, Any], int], Tuple[pd.DataFrame, Dict[str, Any]] | pd.DataFrame],
    objective: str = "balanced",
    iterations: int = 5,
    budget: int = 10000,
    seed: int = 0,
    ml_target_column: Optional[str] = None,
    quasi_identifiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    current = _safe_schema_params(schema)
    best_params = copy.deepcopy(current)
    best_score = -1e9
    history: List[Dict[str, Any]] = []

    # Baseline evaluation
    gen_out = generator_callable(current, budget)
    if isinstance(gen_out, tuple):
        df_base = gen_out[0]
        _ = gen_out[1]
    else:
        df_base = gen_out
    # Realism
    # derive numeric/categorical cols from schema
    num_cols = [f["name"] for f in current.get("fields", []) if f.get("type") in {"int", "float"} and f["name"] in df_base.columns and f["name"] in reference_df.columns]
    cat_cols = [f["name"] for f in current.get("fields", []) if f.get("type") == "category" and f["name"] in df_base.columns and f["name"] in reference_df.columns]
    real_rep = evaluate_realism(df_base, reference_df, current, num_cols, cat_cols)
    realism_score = float(real_rep.get("composite_score", 0.0))
    # Privacy
    qis = quasi_identifiers or num_cols + cat_cols
    priv_rep = simulate_privacy_risk(df_base, reference_df, qis, attacker_sample_size=min(budget, len(reference_df)), noise_level=0.0)
    priv_score = _privacy_risk_to_score(priv_rep)
    # Utility
    if ml_target_column and ml_target_column in df_base.columns and ml_target_column in reference_df.columns:
        util_rep = evaluate_ml_utility(df_base, reference_df, ml_target_column, seed=seed)
        util_score = _normalize_utility_score(util_rep)
    else:
        util_rep = {"real_test_score": 0.0, "is_classification": True}
        util_score = 50.0
    base_obj = _objective_score(objective, realism_score, util_score, priv_score)
    best_score = base_obj
    best_report = {"realism": real_rep, "privacy": priv_rep, "utility": util_rep, "objective_score": base_obj}
    history.append({"iter": 0, "objective": base_obj, "realism": realism_score, "utility": util_score, "privacy_risk": priv_score})

    # Iterations
    for i in range(1, iterations + 1):
        cand = _tweak_params(best_params, rng, alpha=0.10)
        gen_out = generator_callable(cand, budget)
        if isinstance(gen_out, tuple):
            df = gen_out[0]
        else:
            df = gen_out
        num_cols = [f["name"] for f in cand.get("fields", []) if f.get("type") in {"int", "float"} and f["name"] in df.columns and f["name"] in reference_df.columns]
        cat_cols = [f["name"] for f in cand.get("fields", []) if f.get("type") == "category" and f["name"] in df.columns and f["name"] in reference_df.columns]
        real_rep = evaluate_realism(df, reference_df, cand, num_cols, cat_cols)
        realism_score = float(real_rep.get("composite_score", 0.0))
        qis = quasi_identifiers or num_cols + cat_cols
        priv_rep = simulate_privacy_risk(df, reference_df, qis, attacker_sample_size=min(budget, len(reference_df)), noise_level=0.0)
        priv_score = _privacy_risk_to_score(priv_rep)
        if ml_target_column and ml_target_column in df.columns and ml_target_column in reference_df.columns:
            util_rep = evaluate_ml_utility(df, reference_df, ml_target_column, seed=seed)
            util_score = _normalize_utility_score(util_rep)
        else:
            util_rep = {"real_test_score": 0.0, "is_classification": True}
            util_score = 50.0
        obj = _objective_score(objective, realism_score, util_score, priv_score)
        history.append({"iter": i, "objective": obj, "realism": realism_score, "utility": util_score, "privacy_risk": priv_score})
        if obj > best_score:
            best_score = obj
            best_params = cand
            best_report = {"realism": real_rep, "privacy": priv_rep, "utility": util_rep, "objective_score": obj}

    # Final dataset with best params
    gen_out = generator_callable(best_params, budget)
    if isinstance(gen_out, tuple):
        final_df, final_gen_report = gen_out
    else:
        final_df, final_gen_report = gen_out, {}
    # recompute final reports for consistency
    num_cols = [f["name"] for f in best_params.get("fields", []) if f.get("type") in {"int", "float"} and f["name"] in final_df.columns and f["name"] in reference_df.columns]
    cat_cols = [f["name"] for f in best_params.get("fields", []) if f.get("type") == "category" and f["name"] in final_df.columns and f["name"] in reference_df.columns]
    final_real = evaluate_realism(final_df, reference_df, best_params, num_cols, cat_cols)
    qis = quasi_identifiers or num_cols + cat_cols
    final_priv = simulate_privacy_risk(final_df, reference_df, qis, attacker_sample_size=min(budget, len(reference_df)), noise_level=0.0)
    if ml_target_column and ml_target_column in final_df.columns and ml_target_column in reference_df.columns:
        final_util = evaluate_ml_utility(final_df, reference_df, ml_target_column, seed=seed)
    else:
        final_util = {"real_test_score": 0.0, "is_classification": True}
    final_gen_report = {**final_gen_report, "realism": final_real, "privacy": final_priv, "utility": final_util}

    return {
        "best_params": best_params,
        "history": history,
        "final_generation_report": final_gen_report,
        "execution_time_seconds": float(time.time() - t0),
    }


