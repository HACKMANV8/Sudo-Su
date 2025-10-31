from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats as scistats

from ..conditional import compute_categorical_cpt, compute_numeric_conditionals
from ..copula import fit_gaussian_covariance, ranks_from_array, ranks_to_gaussian
from ..utils import derive_subseed

log = logging.getLogger(__name__)


class RelationalLearner:
    def __init__(self, cache_dir: str = "/tmp/openschema_relcache", min_samples: int = 20, smoothing_alpha: float = 1.0):
        self.cache_dir = cache_dir
        self.min_samples = min_samples
        self.smoothing_alpha = smoothing_alpha
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_key(self, reference_csv_path: str, schema_fingerprint: str) -> str:
        """Generate cache key from reference path and schema fingerprint."""
        payload = f"{reference_csv_path}:{schema_fingerprint}:relational-v1:min_samples={self.min_samples}:alpha={self.smoothing_alpha}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def fit(self, reference_csv_path: str, schema: Dict[str, Any], schema_fingerprint: str = "", seed: int = 0) -> Dict[str, Any]:
        """Learn conditional distributions and correlations from reference CSV.
        
        Returns learned priors dict with categorical_priors, conditional_numeric, etc.
        """
        t0 = time.time()
        cache_key = self._cache_key(reference_csv_path, schema_fingerprint)
        cache_path = self._cache_path(cache_key)
        
        # Check cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                log.info("RelationalLearner: cache hit for %s", cache_key[:16])
                return cached
            except Exception:
                pass
        
        # Load reference data
        df = pd.read_csv(reference_csv_path)
        n_rows_ref = len(df)
        warnings: List[str] = []
        
        fields = schema.get("fields", [])
        field_names = {f.get("name"): f for f in fields}
        
        # Validate columns
        schema_cols = set(f.get("name") for f in fields)
        ref_cols = set(df.columns)
        missing = schema_cols - ref_cols
        if missing:
            warnings.append(f"Schema columns not in reference: {missing}")
        
        categorical_priors: Dict[str, Dict[str, Any]] = {}
        conditional_numeric: Dict[str, Dict[str, Dict[str, Dict[str, float]]]]] = {}
        conditional_categorical: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        global_numeric: Dict[str, Dict[str, float]] = {}
        
        # Get dependency graph from schema metadata
        dependency_graph = (schema.get("metadata") or {}).get("dependency_graph", [])
        
        # Identify categorical and numeric columns
        cat_cols = [f["name"] for f in fields if f.get("type") == "category" and f["name"] in df.columns]
        num_cols = [f["name"] for f in fields if f.get("type") in {"int", "float"} and f["name"] in df.columns]
        
        # 1. Categorical priors (global frequencies with smoothing)
        rng_learner = np.random.default_rng(derive_subseed(seed, "relational_learner"))
        for col in cat_cols:
            field = field_names.get(col, {})
            cat_vals = df[col].astype(str)
            counts = cat_vals.value_counts()
            total = len(cat_vals.dropna())
            
            # Use schema categories if provided, otherwise infer
            schema_cats = field.get("categories")
            if schema_cats:
                all_cats = [str(c) for c in schema_cats]
            else:
                all_cats = sorted(counts.index.tolist())
            
            # Dirichlet smoothing
            smoothed_counts = {}
            for cat in all_cats:
                smoothed_counts[cat] = float(counts.get(cat, 0) + self.smoothing_alpha)
            
            total_smoothed = sum(smoothed_counts.values())
            probs = [smoothed_counts[cat] / total_smoothed for cat in all_cats]
            
            categorical_priors[col] = {
                "categories": all_cats,
                "probs": probs,
                "samples": int(total),
            }
        
        # 2. Global numeric statistics
        for col in num_cols:
            num_vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(num_vals) > 0:
                global_numeric[col] = {
                    "mean": float(num_vals.mean()),
                    "std": float(num_vals.std(ddof=0) or 1e-9),
                    "min": float(num_vals.min()),
                    "max": float(num_vals.max()),
                }
            else:
                global_numeric[col] = {"mean": 0.0, "std": 1.0, "min": 0.0, "max": 1.0}
        
        # 3. Conditional numeric: numeric column depends on categorical parent
        for num_col in num_cols:
            conditional_numeric[num_col] = {}
            # Check dependency graph first
            parents = []
            for dep in dependency_graph:
                if isinstance(dep, dict) and dep.get("child") == num_col:
                    parents.append(dep.get("parent"))
            
            # Auto-detect: if a categorical column name suggests it might be a parent
            # (e.g., "product_category" -> "purchase_amount")
            if not parents:
                for cat_col in cat_cols:
                    if ("category" in cat_col.lower() or "product" in cat_col.lower()) and ("amount" in num_col.lower() or "price" in num_col.lower() or "cost" in num_col.lower()):
                        parents.append(cat_col)
            
            for parent_col in parents:
                if parent_col in cat_cols:
                    cond_stats = compute_numeric_conditionals(df, parent_col, num_col, self.min_samples)
                    conditional_numeric[num_col][parent_col] = {}
                    for pval, stats in cond_stats.items():
                        if stats:
                            conditional_numeric[num_col][parent_col][pval] = {
                                "mean": stats["mean"],
                                "std": stats["std"],
                                "samples": stats["samples"],
                            }
                        else:
                            warnings.append(f"Insufficient samples for {num_col}|{parent_col}={pval} (< {self.min_samples})")
        
        # 4. Conditional categorical: child category depends on parent category
        for child_col in cat_cols:
            conditional_categorical[child_col] = {}
            parents = []
            for dep in dependency_graph:
                if isinstance(dep, dict) and dep.get("child") == child_col:
                    parents.append(dep.get("parent"))
            
            for parent_col in parents:
                if parent_col in cat_cols and parent_col != child_col:
                    cpt = compute_categorical_cpt(df, parent_col, child_col, self.smoothing_alpha)
                    conditional_categorical[child_col][parent_col] = cpt
        
        # 5. Copula correlation matrix for numeric columns
        copula_corr = None
        if len(num_cols) > 1:
            num_df = df[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
            if len(num_df) > 1:
                # Compute Spearman correlation
                corr_matrix = num_df.corr(method="spearman").to_numpy()
                # Handle NaN
                corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
                # Ensure symmetric and valid
                corr_matrix = (corr_matrix + corr_matrix.T) / 2
                np.fill_diagonal(corr_matrix, 1.0)
                copula_corr = corr_matrix.tolist()
                
                # Also compute Gaussian latent covariance for copula
                ranks_list = []
                for col in num_cols:
                    if col in num_df.columns:
                        ranks = ranks_from_array(num_df[col].to_numpy())
                        ranks_list.append(ranks)
                if ranks_list:
                    ranks_matrix = np.column_stack(ranks_list)
                    gaussian_latents = ranks_to_gaussian(ranks_matrix)
                    copula_cov = fit_gaussian_covariance(gaussian_latents)
                    # Store both
                    copula_corr = {
                        "spearman": corr_matrix.tolist(),
                        "gaussian_cov": copula_cov.tolist(),
                        "numeric_columns": num_cols,
                    }
        
        # Empirical CDF data for copula sampling
        empirical_cdf: Dict[str, List[float]] = {}
        for col in num_cols:
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors="coerce").dropna().to_numpy()
                empirical_cdf[col] = sorted(vals.tolist())
        
        result = {
            "version": 1,
            "metadata": {
                "fitted_on": datetime.now().isoformat(),
                "rows": int(n_rows_ref),
                "cache_key": cache_key,
            },
            "categorical_priors": categorical_priors,
            "conditional_numeric": conditional_numeric,
            "conditional_categorical": conditional_categorical,
            "global_numeric": global_numeric,
            "copula_corr": copula_corr,
            "empirical_cdf": empirical_cdf,
            "warnings": warnings,
            "execution_time_seconds": float(time.time() - t0),
        }
        
        # Cache result
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
        except Exception as e:
            log.warning("Failed to cache relational priors: %s", e)
        
        return result

