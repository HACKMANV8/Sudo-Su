from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scistats


def _safe_numeric(arr: pd.Series) -> np.ndarray:
    return pd.to_numeric(arr, errors="coerce").dropna().to_numpy()


def _topk_counts(s: pd.Series, k: int = 10) -> Tuple[List[str], np.ndarray]:
    vc = s.astype(str).value_counts()
    cats = list(vc.index[:k])
    counts = vc.values[:k].astype(float)
    if counts.sum() == 0:
        return cats, counts
    return cats, counts / counts.sum()


def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = p.astype(float) + 1e-12
    q = q.astype(float) + 1e-12
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return 0.5 * (scistats.entropy(p, m) + scistats.entropy(q, m))


def evaluate_realism(
    generated_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    schema: Dict[str, Any],
    numeric_cols: Optional[List[str]] = None,
    categorical_cols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    t0 = time.time()
    # Derive columns if not supplied
    if numeric_cols is None or categorical_cols is None:
        num = []
        cat = []
        for f in schema.get("fields", []):
            n = f.get("name")
            t = f.get("type")
            if n in generated_df.columns and n in reference_df.columns:
                if t in {"int", "float"}:
                    num.append(n)
                elif t == "category":
                    cat.append(n)
        numeric_cols = num if numeric_cols is None else numeric_cols
        categorical_cols = cat if categorical_cols is None else categorical_cols

    feature_stats: Dict[str, Any] = {}
    categorical_stats: Dict[str, Any] = {}
    contrib_scores: List[Tuple[str, float]] = []

    # Numeric metrics
    for col in numeric_cols or []:
        g = _safe_numeric(generated_df[col])
        r = _safe_numeric(reference_df[col])
        if len(g) == 0 or len(r) == 0:
            feature_stats[col] = None
            continue
        mean_gen = float(np.mean(g))
        mean_ref = float(np.mean(r))
        # KS
        ks = scistats.ks_2samp(g, r, alternative="two-sided", method="auto")
        ks_stat = float(ks.statistic)
        ks_pvalue = float(ks.pvalue)
        # Wasserstein (EMD)
        emd = float(scistats.wasserstein_distance(g, r))
        # Spearman between samples (if lengths differ, align by min length)
        m = min(len(g), len(r))
        if m > 1:
            rho = float(scistats.spearmanr(g[:m], r[:m]).correlation or 0.0)
        else:
            rho = 0.0
        feature_stats[col] = {
            "mean_gen": mean_gen,
            "mean_ref": mean_ref,
            "ks_stat": ks_stat,
            "ks_pvalue": ks_pvalue,
            "emd": emd,
            "spearman_rho": rho,
        }
        # Contribution: higher KS/EMD and lower |rho| worse
        std_ref = float(np.std(r)) + 1e-9
        emd_norm = min(1.0, emd / (std_ref * 3.0))  # 3-sigma scale
        contrib = 0.5 * ks_stat + 0.3 * emd_norm + 0.2 * (1 - abs(rho))
        contrib_scores.append((col, float(contrib)))

    # Categorical metrics
    for col in categorical_cols or []:
        if col not in generated_df.columns or col not in reference_df.columns:
            continue
        k = 10
        cats_g, p = _topk_counts(generated_df[col], k)
        cats_r, q = _topk_counts(reference_df[col], k)
        # Align
        all_cats = list(dict.fromkeys(cats_g + cats_r))
        pv = np.array([p[cats_g.index(c)] if c in cats_g and len(p) > 0 else 0.0 for c in all_cats], dtype=float)
        qv = np.array([q[cats_r.index(c)] if c in cats_r and len(q) > 0 else 0.0 for c in all_cats], dtype=float)
        # Jaccard over top-k sets
        inter = len(set(cats_g) & set(cats_r))
        union = len(set(cats_g) | set(cats_r)) or 1
        topk_overlap = float(inter / union)
        js = float(_js_divergence(pv, qv))
        # Chi-square on contingency (scale to counts)
        # Use 1e5 total to keep integer counts
        total = 100000
        obs = np.vstack([np.round(pv * total), np.round(qv * total)])
        try:
            chi2, pval, _, _ = scistats.chi2_contingency(obs, correction=False)
            chi2_pvalue = float(pval)
        except Exception:
            chi2_pvalue = 0.0
        categorical_stats[col] = {
            "top_k_overlap": topk_overlap,
            "js_divergence": js,
            "chi2_pvalue": chi2_pvalue,
        }
        contrib = 0.5 * js + 0.3 * (1 - topk_overlap) + 0.2 * (1 - chi2_pvalue)
        contrib_scores.append((col, float(contrib)))

    # Composite score (0-100). Higher is better.
    # Numeric per-feature normalized score: ks->(1-ks), emd->exp(-emd/std*3), rho->abs(rho)
    numeric_scores = []
    for col in numeric_cols or []:
        st = feature_stats.get(col)
        if not st:
            continue
        ks_score = 1.0 - float(st["ks_stat"])  # in [0,1]
        # approximate scale via std of ref; fallback to 1
        r = _safe_numeric(reference_df[col])
        std_ref = float(np.std(r)) + 1e-9
        emd_score = float(np.exp(-float(st["emd"]) / (std_ref * 3.0)))
        rho_score = abs(float(st["spearman_rho"]))
        numeric_scores.append(0.4 * ks_score + 0.3 * emd_score + 0.3 * rho_score)

    categorical_scores = []
    for col in categorical_cols or []:
        st = categorical_stats.get(col)
        if not st:
            continue
        js = float(st["js_divergence"])  # 0 good
        topk = float(st["top_k_overlap"])  # 1 good
        chi2 = float(st["chi2_pvalue"])  # 1 good
        cat_score = 0.5 * (1 - min(1.0, js)) + 0.3 * topk + 0.2 * chi2
        categorical_scores.append(cat_score)

    if numeric_scores:
        num_score = float(np.mean(numeric_scores))
    else:
        num_score = 0.5
    if categorical_scores:
        cat_score = float(np.mean(categorical_scores))
    else:
        cat_score = 0.5
    composite = 0.6 * num_score + 0.4 * cat_score
    composite_score = float(max(0.0, min(1.0, composite)) * 100.0)

    # Feature ranking by contribution (higher = more gap)
    contrib_scores.sort(key=lambda t: t[1], reverse=True)
    feature_ranking = [f for f, _ in contrib_scores[:10]]

    return {
        "feature_stats": feature_stats,
        "categorical_stats": categorical_stats,
        "composite_score": composite_score,
        "feature_ranking": feature_ranking,
        "execution_time_seconds": float(time.time() - t0),
    }


def summarize_realism_report(report: Dict[str, Any]) -> str:
    score = report.get("composite_score", 0.0)
    top = report.get("feature_ranking", [])[:3]
    return f"Realism {score:.1f}/100. Most divergent: {', '.join(top) if top else 'n/a'}."


