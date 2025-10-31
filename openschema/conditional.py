from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def learn_conditionals_from_csv(df: pd.DataFrame, schema: Dict[str, Any], min_samples: int = 10) -> Dict[str, Dict[str, Dict[str, tuple]]]:
    mappings: Dict[str, Dict[str, Dict[str, tuple]]] = {}
    fields = schema.get("fields", [])
    cat_fields = [f["name"] for f in fields if f.get("type") == "category"]
    num_fields = [f["name"] for f in fields if f.get("type") in {"int", "float"}]
    drivers = [c for c in cat_fields if c in df.columns and c in {"role", "category", "country"}]
    for driver in drivers:
        grp = df.groupby(driver)
        dmap: Dict[str, Dict[str, tuple]] = {}
        for cat, sub in grp:
            if len(sub) < min_samples:
                continue
            stats: Dict[str, tuple] = {}
            for nf in num_fields:
                if nf in sub.columns:
                    s = pd.to_numeric(sub[nf], errors="coerce").dropna()
                    if len(s) >= min_samples:
                        stats[nf] = (float(s.mean()), float(s.std(ddof=0) or 1.0))
            if stats:
                dmap[str(cat)] = stats
        if dmap:
            mappings[driver] = dmap
    return mappings


def apply_conditionals_sampling(rng: np.random.Generator, driver_series: pd.Series, numeric_field_mappings: Dict[str, Dict[str, tuple]], n_rows: int, field_name: str) -> np.ndarray:
    means = np.zeros(n_rows, dtype=float)
    stds = np.ones(n_rows, dtype=float)
    cats = driver_series.astype(str).to_numpy()
    for cat, (mu, sd) in numeric_field_mappings.items():
        mask = cats == str(cat)
        means[mask] = float(mu)
        stds[mask] = float(sd or 1.0)
    return rng.normal(loc=means, scale=stds)


def compute_categorical_cpt(df: pd.DataFrame, parent_col: str, child_col: str, smoothing_alpha: float = 1.0) -> Dict[str, Dict[str, Any]]:
    """Compute conditional probability table (CPT) for child given parent.
    
    Returns:
        {parent_value: {categories: [...], probs: [...], samples: N}}
    """
    cpt: Dict[str, Dict[str, Any]] = {}
    if parent_col not in df.columns or child_col not in df.columns:
        return cpt
    
    for parent_val, group in df.groupby(parent_col):
        child_vals = group[child_col].astype(str)
        counts = child_vals.value_counts()
        total = len(child_vals)
        
        # Dirichlet smoothing: add alpha to each count
        all_categories = set(df[child_col].astype(str).unique())
        smoothed_counts = {}
        for cat in all_categories:
            smoothed_counts[cat] = float(counts.get(cat, 0) + smoothing_alpha)
        
        # Normalize to probabilities
        total_smoothed = sum(smoothed_counts.values())
        probs = [smoothed_counts[cat] / total_smoothed for cat in sorted(all_categories)]
        
        cpt[str(parent_val)] = {
            "categories": sorted(all_categories),
            "probs": probs,
            "samples": int(total),
        }
    
    return cpt


def compute_numeric_conditionals(df: pd.DataFrame, parent_col: str, numeric_col: str, min_samples: int = 10) -> Dict[str, Optional[Dict[str, float]]]:
    """Compute per-parent-group statistics for numeric column.
    
    Returns:
        {parent_value: {mean: float, std: float, samples: int} or None if insufficient}
    """
    conditionals: Dict[str, Optional[Dict[str, float]]] = {}
    if parent_col not in df.columns or numeric_col not in df.columns:
        return conditionals
    
    for parent_val, group in df.groupby(parent_col):
        num_vals = pd.to_numeric(group[numeric_col], errors="coerce").dropna()
        if len(num_vals) < min_samples:
            conditionals[str(parent_val)] = None
        else:
            conditionals[str(parent_val)] = {
                "mean": float(num_vals.mean()),
                "std": float(num_vals.std(ddof=0) or 1e-9),
                "samples": int(len(num_vals)),
            }
    
    return conditionals


def sample_categorical_conditional(parent_value: str, cpt: Dict[str, Dict[str, Any]], rng: np.random.Generator) -> str:
    """Sample child category given parent value using CPT."""
    entry = cpt.get(str(parent_value))
    if not entry or not entry.get("categories"):
        # Fallback: uniform over all seen categories
        all_cats = set()
        for e in cpt.values():
            all_cats.update(e.get("categories", []))
        if all_cats:
            return rng.choice(list(all_cats))
        return "unknown"
    
    cats = entry["categories"]
    probs = entry["probs"]
    return rng.choice(cats, p=np.array(probs))


def sample_numeric_conditional(parent_value: str, conditional_stats: Dict[str, Optional[Dict[str, float]]], global_mean: float, global_std: float, rng: np.random.Generator) -> float:
    """Sample numeric value conditional on parent, fallback to global if None."""
    stats = conditional_stats.get(str(parent_value))
    if stats:
        mu = stats["mean"]
        sd = max(stats["std"], 1e-9)
        return float(rng.normal(loc=mu, scale=sd))
    else:
        return float(rng.normal(loc=global_mean, scale=max(global_std, 1e-9)))


