from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import logging

from ..conditional import sample_categorical_conditional, sample_numeric_conditional
from ..copula import (
    fit_gaussian_covariance,
    gaussian_to_ranks,
    ranks_from_array,
    ranks_to_gaussian,
    ranks_to_values,
    sample_from_gaussian_copula,
)
from ..utils import (
    derive_subseed,
    deterministic_uuid,
    normalize_seed,
    sample_datetimes_uniform,
)

log = logging.getLogger(__name__)


def _topological_sort_fields(fields: List[Dict[str, Any]], dependency_graph: List[Dict[str, Any]]) -> List[str]:
    """Topologically sort field names based on dependency graph.
    
    Returns ordered list of field names to generate.
    """
    field_names = [f["name"] for f in fields]
    if not dependency_graph:
        # Heuristic: categorical first, then numeric
        order = []
        for f in fields:
            if f.get("type") == "category":
                order.append(f["name"])
        for f in fields:
            if f.get("type") in {"int", "float"}:
                order.append(f["name"])
        for f in fields:
            if f.get("type") not in {"category", "int", "float"}:
                order.append(f["name"])
        return order
    
    # Build graph
    graph: Dict[str, List[str]] = {name: [] for name in field_names}
    in_degree = {name: 0 for name in field_names}
    
    for dep in dependency_graph:
        parent = dep.get("parent")
        child = dep.get("child")
        if parent in field_names and child in field_names:
            graph[parent].append(child)
            in_degree[child] += 1
    
    # Kahn's algorithm
    queue = [name for name in field_names if in_degree[name] == 0]
    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Add any remaining (no dependencies)
    for name in field_names:
        if name not in result:
            result.append(name)
    
    return result


def generate_relational(
    schema: Dict[str, Any],
    n_rows: int,
    seed: int,
    learned_priors: Dict[str, Any],
    chunk_size: Optional[int] = None,
) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Generate relational dataset using learned priors.
    
    Args:
        schema: Schema dict
        n_rows: Number of rows to generate
        seed: Seed for reproducibility
        learned_priors: Output from RelationalLearner.fit
        chunk_size: Optional chunk size for large datasets
    
    Returns:
        (DataFrame, generation_report)
    """
    t0 = time.time()
    normalized_seed = normalize_seed(seed)
    rng_master = np.random.default_rng(normalized_seed)
    
    fields = schema.get("fields", [])
    field_dict = {f["name"]: f for f in fields}
    
    dependency_graph = (schema.get("metadata") or {}).get("dependency_graph", [])
    generation_order = _topological_sort_fields(fields, dependency_graph)
    
    categorical_priors = learned_priors.get("categorical_priors", {})
    conditional_numeric = learned_priors.get("conditional_numeric", {})
    conditional_categorical = learned_priors.get("conditional_categorical", {})
    global_numeric = learned_priors.get("global_numeric", {})
    copula_corr = learned_priors.get("copula_corr")
    empirical_cdf = learned_priors.get("empirical_cdf", {})
    
    col_data: Dict[str, List[Any]] = {}
    warnings: List[str] = []
    
    # Determine numeric columns that need copula
    num_cols = [f["name"] for f in fields if f.get("type") in {"int", "float"}]
    cat_cols = [f["name"] for f in fields if f.get("type") == "category"]
    
    # Track which numerics are conditionally generated vs copula
    conditionally_generated_numerics = set()
    copula_numerics = []
    
    # Generate fields in topological order
    for field_name in generation_order:
        field = field_dict.get(field_name)
        if not field:
            continue
        
        ftype = field.get("type")
        rng_field = np.random.default_rng(derive_subseed(normalized_seed, f"rel_{field_name}"))
        
        if ftype == "category":
            # Categorical generation
            if field_name in conditional_categorical:
                # Has parent dependency
                parent_cols = list(conditional_categorical[field_name].keys())
                if parent_cols and parent_cols[0] in col_data:
                    # Sample conditional on parent
                    parent_col = parent_cols[0]
                    cpt = conditional_categorical[field_name][parent_col]
                    parent_values = col_data[parent_col]
                    vals = [sample_categorical_conditional(str(pv), cpt, rng_field) for pv in parent_values]
                else:
                    # Fallback to global prior
                    prior = categorical_priors.get(field_name, {})
                    cats = prior.get("categories", field.get("categories", ["A", "B"]))
                    probs = prior.get("probs")
                    if probs:
                        vals = rng_field.choice(cats, size=n_rows, p=np.array(probs)).tolist()
                    else:
                        vals = rng_field.choice(cats, size=n_rows).tolist()
            else:
                # Global categorical prior
                prior = categorical_priors.get(field_name, {})
                cats = prior.get("categories", field.get("categories", ["A", "B"]))
                probs = prior.get("probs")
                if probs:
                    vals = rng_field.choice(cats, size=n_rows, p=np.array(probs)).tolist()
                else:
                    vals = rng_field.choice(cats, size=n_rows).tolist()
            
            col_data[field_name] = vals
        
        elif ftype in {"int", "float"}:
            # Numeric generation
            # Check if conditional on categorical parent
            has_conditional = False
            if field_name in conditional_numeric:
                for parent_col in conditional_numeric[field_name].keys():
                    if parent_col in col_data:
                        # Generate conditionally
                        cond_stats = conditional_numeric[field_name][parent_col]
                        global_stats = global_numeric.get(field_name, {"mean": 0.0, "std": 1.0})
                        parent_values = col_data[parent_col]
                        vals = [
                            sample_numeric_conditional(
                                str(pv),
                                cond_stats,
                                global_stats["mean"],
                                global_stats["std"],
                                rng_field,
                            )
                            for pv in parent_values
                        ]
                        # Clamp to schema bounds
                        fmin = field.get("min")
                        fmax = field.get("max")
                        if fmin is not None:
                            vals = [max(float(fmin), v) for v in vals]
                        if fmax is not None:
                            vals = [min(float(fmax), v) for v in vals]
                        col_data[field_name] = vals
                        conditionally_generated_numerics.add(field_name)
                        has_conditional = True
                        break
            
            if not has_conditional:
                # Will use copula later
                copula_numerics.append(field_name)
                # Placeholder for now
                col_data[field_name] = [0.0] * n_rows
        
        elif ftype == "string":
            # String generation (simple)
            fmt = (field.get("format") or "").lower()
            if fmt == "uuid":
                ns = derive_subseed(normalized_seed, f"uuid::{field_name}")
                vals = [deterministic_uuid(ns, i, field_name) for i in range(n_rows)]
            else:
                from faker import Faker
                faker = Faker()
                faker.seed(derive_subseed(normalized_seed, f"str_{field_name}"))
                vals = [faker.word() for _ in range(n_rows)]
            col_data[field_name] = vals
        
        elif ftype == "bool":
            p = field.get("p", 0.5)
            vals = (rng_field.random(n_rows) < p).astype(int).tolist()
            col_data[field_name] = vals
        
        elif ftype == "datetime":
            from datetime import datetime
            lo = field.get("min") or datetime(2020, 1, 1)
            hi = field.get("max") or datetime(2021, 1, 1)
            rng_dates = np.random.default_rng(derive_subseed(normalized_seed, f"date_{field_name}"))
            vals = sample_datetimes_uniform(lo, hi, n_rows, rng_dates)
            col_data[field_name] = vals
    
    # Copula step for correlated numerics
    if copula_numerics and copula_corr:
        rng_copula = np.random.default_rng(derive_subseed(normalized_seed, "copula"))
        
        if isinstance(copula_corr, dict):
            # New format with gaussian_cov
            cov_matrix = np.array(copula_corr.get("gaussian_cov", copula_corr.get("spearman", [])))
            copula_cols = copula_corr.get("numeric_columns", copula_numerics)
        else:
            # Legacy: just correlation matrix
            cov_matrix = np.array(copula_corr)
            copula_cols = copula_numerics
        
        if cov_matrix.size > 0 and len(copula_cols) > 0:
            # Filter to columns we're actually generating
            available_cols = [c for c in copula_cols if c in copula_numerics]
            if len(available_cols) > 1:
                # Subset covariance matrix
                try:
                    col_indices = [copula_cols.index(c) for c in available_cols]
                    if len(col_indices) == len(available_cols) and max(col_indices) < cov_matrix.shape[0]:
                        sub_cov = cov_matrix[np.ix_(col_indices, col_indices)]
                        
                        # Sample from copula
                        latent_samples = sample_from_gaussian_copula(sub_cov, n_rows, rng_copula)
                        
                        # Convert to ranks
                        ranks = gaussian_to_ranks(latent_samples)
                        
                        # Map to empirical values
                        empirical_list = [empirical_cdf.get(col, [0.0]) for col in available_cols]
                        values_matrix = ranks_to_values(ranks, empirical_list)
                        
                        # Assign to columns
                        for idx, col in enumerate(available_cols):
                            if idx < values_matrix.shape[1]:
                                col_data[col] = values_matrix[:, idx].tolist()
                                
                                # Clamp to schema bounds
                                field = field_dict.get(col, {})
                                fmin = field.get("min")
                                fmax = field.get("max")
                                if fmin is not None or fmax is not None:
                                    vals = col_data[col]
                                    if fmin is not None:
                                        vals = [max(float(fmin), v) for v in vals]
                                    if fmax is not None:
                                        vals = [min(float(fmax), v) for v in vals]
                                    col_data[col] = vals
                except (ValueError, IndexError) as e:
                    log.warning("Copula subsetting failed: %s, falling back to independent", e)
                    # Fall through to independent generation
            else:
                # Single column or no copula - use global distribution
                for col in copula_numerics:
                    global_stats = global_numeric.get(col, {"mean": 0.0, "std": 1.0})
                    rng_col = np.random.default_rng(derive_subseed(normalized_seed, f"rel_{col}"))
                    vals = rng_col.normal(loc=global_stats["mean"], scale=global_stats["std"], size=n_rows).tolist()
                    # Clamp
                    field = field_dict.get(col, {})
                    fmin = field.get("min")
                    fmax = field.get("max")
                    if fmin is not None:
                        vals = [max(float(fmin), v) for v in vals]
                    if fmax is not None:
                        vals = [min(float(fmax), v) for v in vals]
                    col_data[col] = vals
    
    # Handle remaining numeric columns without copula
    for col in copula_numerics:
        if col_data.get(col) == [0.0] * n_rows:  # Still placeholder
            global_stats = global_numeric.get(col, {"mean": 0.0, "std": 1.0})
            rng_col = np.random.default_rng(derive_subseed(normalized_seed, f"rel_{col}"))
            vals = rng_col.normal(loc=global_stats["mean"], scale=global_stats["std"], size=n_rows).tolist()
            field = field_dict.get(col, {})
            fmin = field.get("min")
            fmax = field.get("max")
            if fmin is not None:
                vals = [max(float(fmin), v) for v in vals]
            if fmax is not None:
                vals = [min(float(fmax), v) for v in vals]
            col_data[col] = vals
    
    # Convert to DataFrame
    df = pd.DataFrame(col_data, columns=[f["name"] for f in fields if f["name"] in col_data])
    
    # Type conversions
    for f in fields:
        name = f.get("name")
        if name in df.columns:
            ftype = f.get("type")
            if ftype == "int":
                df[name] = df[name].astype(int)
            elif ftype == "float":
                df[name] = df[name].astype(float)
            elif ftype == "bool":
                df[name] = df[name].astype(int)
    
    generation_report = {
        "rows_generated": int(n_rows),
        "used_priors_cache_key": learned_priors.get("metadata", {}).get("cache_key", ""),
        "conditionally_generated_numerics": list(conditionally_generated_numerics),
        "copula_numerics": copula_numerics,
        "warnings": warnings,
        "execution_time_seconds": float(time.time() - t0),
    }
    
    return df, generation_report

