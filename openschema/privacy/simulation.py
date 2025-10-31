from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..artifacts import _save_png  # reuse tiny PNG writer


def _standardize_numeric(df: pd.DataFrame, cols: List[str]) -> np.ndarray:
    if not cols:
        return np.zeros((len(df), 0), dtype=float)
    arr = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    mean = arr.mean(axis=0)
    std = arr.std(axis=0)
    std[std == 0] = 1.0
    return (arr - mean) / std


def _cat_mismatch_penalty(a: pd.DataFrame, b: pd.DataFrame, cols: List[str]) -> np.ndarray:
    if not cols:
        return np.zeros((len(a),), dtype=float)
    # Exact match score: penalty per mismatch aggregated
    pen = np.zeros((len(a),), dtype=float)
    for c in cols:
        av = a[c].astype(str).to_numpy()
        bv = b[c].astype(str).to_numpy()
        pen += (av != bv).astype(float)
    return pen


def _attacker_samples(reference_df: pd.DataFrame, size: int, rng: np.random.Generator) -> pd.DataFrame:
    n = len(reference_df)
    if n == 0:
        return reference_df.head(0).copy()
    idx = rng.integers(0, n, size=size)
    return reference_df.iloc[idx].reset_index(drop=True)


def _nearest_neighbor_distance(
    query_numeric: np.ndarray,
    pool_numeric: np.ndarray,
    query_cat_df: pd.DataFrame,
    pool_cat_df: pd.DataFrame,
    k: int = 5,
) -> np.ndarray:
    if pool_numeric.shape[1] == 0:
        # No numeric features: distance purely from categorical mismatches
        dists = []
        for i in range(len(query_cat_df)):
            q = query_cat_df.iloc[[i]].reset_index(drop=True)
            pen = _cat_mismatch_penalty(pd.concat([q] * len(pool_cat_df), ignore_index=True), pool_cat_df.reset_index(drop=True), list(query_cat_df.columns))
            dists.append(float(pen.min()))
        return np.array(dists, dtype=float)
    tree = cKDTree(pool_numeric)
    dd, ii = tree.query(query_numeric, k=min(k, len(pool_numeric)))
    if k == 1 or np.ndim(ii) == 1:
        ii = ii.reshape(-1, 1)
        dd = dd.reshape(-1, 1)
    best = []
    for row in range(len(query_numeric)):
        cand_idx = ii[row]
        base = dd[row]
        # Adjust by categorical penalty
        qcat = query_cat_df.iloc[[row]].reset_index(drop=True)
        pcat = pool_cat_df.iloc[cand_idx].reset_index(drop=True)
        # Broadcast to same length
        qrep = pd.concat([qcat] * len(pcat), ignore_index=True)
        pen = _cat_mismatch_penalty(qrep, pcat, list(query_cat_df.columns))
        total = base + pen  # combine
        best.append(float(np.min(total)))
    return np.array(best, dtype=float)


def simulate_privacy_risk(
    synthetic_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    quasi_identifiers: List[str],
    attacker_sample_size: int = 1000,
    noise_level: float = 0.01,
) -> Dict[str, Any]:
    rng = np.random.default_rng(0)
    qi = [c for c in quasi_identifiers if c in synthetic_df.columns and c in reference_df.columns]
    if not qi:
        return {"error": "No quasi-identifiers available in both datasets"}

    num_cols = [c for c in qi if pd.api.types.is_numeric_dtype(reference_df[c])]
    cat_cols = [c for c in qi if c not in num_cols]

    # Standardize numeric for distance
    gen_num = _standardize_numeric(synthetic_df, num_cols)
    ref_num = _standardize_numeric(reference_df, num_cols)
    syn_cat = synthetic_df[cat_cols] if cat_cols else synthetic_df.iloc[:, :0]
    ref_cat = reference_df[cat_cols] if cat_cols else reference_df.iloc[:, :0]

    # Adaptive threshold based on reference self distances (nearest neighbor)
    if len(reference_df) > 1 and gen_num.shape[1] > 0:
        tree_r = cKDTree(ref_num)
        d_ref, idx = tree_r.query(ref_num, k=2)  # first is self
        self_nn = d_ref[:, 1]
        thr = float(np.quantile(self_nn, 0.1))
    else:
        thr = 0.5

    # Attacker samples
    att = _attacker_samples(reference_df[qi], attacker_sample_size, rng)
    att_num = _standardize_numeric(att, num_cols)
    att_cat = att[cat_cols] if cat_cols else att.iloc[:, :0]

    d_top = _nearest_neighbor_distance(att_num, gen_num, att_cat, syn_cat, k=5)
    reid_rate = float((d_top < thr).mean() if len(d_top) > 0 else 0.0)

    # Simulate noise addition
    synth_noised = synthetic_df.copy()
    for c in num_cols:
        std = float(np.std(synthetic_df[c].to_numpy(dtype=float))) or 1.0
        noise = rng.laplace(loc=0.0, scale=noise_level * std, size=len(synthetic_df))
        synth_noised[c] = pd.to_numeric(synth_noised[c], errors="coerce").fillna(0.0).to_numpy(dtype=float) + noise
    gen_num_noised = _standardize_numeric(synth_noised, num_cols)
    d_top_noised = _nearest_neighbor_distance(att_num, gen_num_noised, att_cat, synth_noised[cat_cols] if cat_cols else synth_noised.iloc[:, :0], k=5)
    reid_rate_after = float((d_top_noised < thr).mean() if len(d_top_noised) > 0 else 0.0)

    delta = float(reid_rate - reid_rate_after)
    details = {
        "quasi_identifiers": qi,
        "threshold": thr,
        "num_qi": num_cols,
        "cat_qi": cat_cols,
    }
    recommendation = "Increase noise_level or generalize high-risk quasi-identifiers" if reid_rate > 0.05 else "Risk appears low; verify with domain review"
    return {
        "reidentification_rate": reid_rate,
        "reidentification_rate_after_noise": reid_rate_after,
        "delta": delta,
        "details": details,
        "recommendation": recommendation,
    }


def plot_privacy_tradeoff(
    synthetic_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    quasi_identifiers: List[str],
    noise_levels: List[float],
    out_path: str,
) -> str:
    rates = []
    for nl in noise_levels:
        r = simulate_privacy_risk(synthetic_df, reference_df, quasi_identifiers, attacker_sample_size=min(1000, len(reference_df)), noise_level=nl)
        rates.append(r.get("reidentification_rate_after_noise", 0.0))
    # Draw simple plot
    H, W = 300, 600
    img = np.full((H, W), 255, dtype=np.uint8)
    xs = np.linspace(20, W - 20, len(noise_levels))
    maxr = max(rates) if rates else 1.0
    maxr = max(maxr, 1e-6)
    ys = H - 20 - (np.array(rates) / maxr) * (H - 40)
    for i in range(1, len(xs)):
        x0, y0 = int(xs[i - 1]), int(ys[i - 1])
        x1, y1 = int(xs[i]), int(ys[i])
        # simple Bresenham-like
        n = max(1, abs(x1 - x0))
        for t in range(n + 1):
            x = int(x0 + (x1 - x0) * t / n)
            y = int(y0 + (y1 - y0) * t / n)
            if 0 <= y < H and 0 <= x < W:
                img[y, x] = 60
    _save_png(img, out_path)
    return out_path


