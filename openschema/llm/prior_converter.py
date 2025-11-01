from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..utils import normalize_seed

log = logging.getLogger(__name__)


def convert_llm_priors_to_relational(
    llm_priors: Dict[str, Any],
    schema: Dict[str, Any],
    update_schema: bool = True,
) -> Dict[str, Any]:
    """Convert LLM priors format to relational priors format expected by generate_relational.
    
    Args:
        llm_priors: LLM priors dict with "priors", "dependencies", "examples" keys
        schema: Schema dict with fields
    
    Returns:
        Relational priors dict in the format expected by generate_relational
    """
    fields = schema.get("fields", [])
    field_dict = {f["name"]: f for f in fields}
    
    # Initialize relational structure
    categorical_priors: Dict[str, Dict[str, Any]] = {}
    conditional_numeric: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {}
    conditional_categorical: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
    global_numeric: Dict[str, Dict[str, float]] = {}
    copula_corr = None
    empirical_cdf: Dict[str, List[float]] = {}
    
    llm_priors_dict = llm_priors.get("priors", {})
    llm_dependencies = llm_priors.get("dependencies", [])
    llm_examples = llm_priors.get("examples", [])
    
    # Process priors
    for col_name, col_prior in llm_priors_dict.items():
        field = field_dict.get(col_name)
        if not field:
            continue
        
        ptype = col_prior.get("type")
        ftype = field.get("type")
        
        if ptype == "categorical" and ftype == "category":
            # Extract categories and probabilities
            categories = col_prior.get("categories", field.get("categories", []))
            probs = col_prior.get("probs", [])
            
            # Normalize probabilities
            if probs and len(probs) == len(categories):
                total = sum(probs)
                if total > 0:
                    probs = [p / total for p in probs]
                else:
                    probs = [1.0 / len(categories)] * len(categories) if categories else []
            else:
                probs = [1.0 / len(categories)] * len(categories) if categories else []
            
            categorical_priors[col_name] = {
                "categories": categories,
                "probs": probs,
                "samples": col_prior.get("samples", len(llm_examples)),
            }
        
        elif ptype == "numeric" and ftype in {"int", "float"}:
            # Extract numeric distribution parameters
            dist_info = col_prior.get("distribution", {})
            
            # Get mean/std from distribution or direct params
            mean = dist_info.get("mean") if isinstance(dist_info, dict) else col_prior.get("mean")
            std = dist_info.get("std") if isinstance(dist_info, dict) else col_prior.get("std")
            min_val = dist_info.get("min") if isinstance(dist_info, dict) else col_prior.get("min")
            max_val = dist_info.get("max") if isinstance(dist_info, dict) else col_prior.get("max")
            
            # Use schema bounds as fallback
            if mean is None:
                mean = field.get("mean", 0.0)
            if std is None:
                std = field.get("std", 1.0) or 1.0
            if min_val is None:
                min_val = field.get("min")
            if max_val is None:
                max_val = field.get("max")
            
            global_numeric[col_name] = {
                "mean": float(mean),
                "std": float(std or 1.0),
                "min": float(min_val) if min_val is not None else None,
                "max": float(max_val) if max_val is not None else None,
            }
            
            # Build empirical CDF from examples if available
            if llm_examples and col_name in llm_examples[0] if llm_examples else False:
                example_vals = []
                for ex in llm_examples:
                    if col_name in ex:
                        try:
                            val = float(ex[col_name])
                            example_vals.append(val)
                        except (ValueError, TypeError):
                            pass
                if example_vals:
                    empirical_cdf[col_name] = sorted(example_vals)
    
    # Process dependencies
    for dep in llm_dependencies:
        if not isinstance(dep, dict):
            continue
        
        parent = dep.get("parent") or dep.get("from")
        child = dep.get("child") or dep.get("to")
        condition = dep.get("condition") or dep.get("rule")
        
        if not parent or not child:
            continue
        
        parent_field = field_dict.get(parent)
        child_field = field_dict.get(child)
        
        if not parent_field or not child_field:
            continue
        
        # Conditional numeric: child is numeric, parent is categorical
        if child_field.get("type") in {"int", "float"} and parent_field.get("type") == "category":
            if child not in conditional_numeric:
                conditional_numeric[child] = {}
            if parent not in conditional_numeric[child]:
                conditional_numeric[child][parent] = {}
            
            # Parse condition to extract per-category stats
            # Format: "if parent == 'value' then child ~ normal(mean, std)"
            # For now, extract mean/std if provided in condition
            if isinstance(condition, dict):
                # Direct mapping: {"Electronics": {"mean": 800, "std": 400}, ...}
                for cat_val, stats in condition.items():
                    if isinstance(stats, dict):
                        mean_val = stats.get("mean", global_numeric.get(child, {}).get("mean", 0.0))
                        std_val = stats.get("std", global_numeric.get(child, {}).get("std", 1.0))
                        conditional_numeric[child][parent][str(cat_val)] = {
                            "mean": float(mean_val),
                            "std": float(std_val or 1.0),
                            "samples": stats.get("samples", 10),
                        }
            elif isinstance(condition, str) and "normal" in condition.lower():
                # Try to parse "normal(mean, std)" from string
                # For now, use global stats as fallback
                pass
        
        # Conditional categorical: both are categorical
        elif child_field.get("type") == "category" and parent_field.get("type") == "category":
            if child not in conditional_categorical:
                conditional_categorical[child] = {}
            if parent not in conditional_categorical[child]:
                conditional_categorical[child][parent] = {}
            
            # Parse condition to extract CPT
            # Format: {"parent_val": {"child_val1": prob1, "child_val2": prob2, ...}}
            if isinstance(condition, dict):
                conditional_categorical[child][parent] = condition
    
    # Build dependency graph for topological sort
    dependency_graph: List[Dict[str, str]] = []
    for dep in llm_dependencies:
        if isinstance(dep, dict):
            parent = dep.get("parent") or dep.get("from")
            child = dep.get("child") or dep.get("to")
            if parent and child:
                dependency_graph.append({"parent": parent, "child": child})
    
    # Store dependency graph in result metadata and optionally update schema
    result_metadata = {
        "fitted_on": "from_llm",
        "rows": len(llm_examples),
        "cache_key": "llm_priors",
        "dependency_graph": dependency_graph,
    }
    
    # Update schema metadata with dependency graph if requested
    if update_schema and dependency_graph:
        if "metadata" not in schema:
            schema["metadata"] = {}
        schema["metadata"]["dependency_graph"] = dependency_graph
    
    # Compute simple copula correlation if we have multiple numeric columns
    num_cols = [f["name"] for f in fields if f.get("type") in {"int", "float"}]
    if len(num_cols) > 1 and llm_examples:
        # Try to compute correlation from examples
        try:
            import pandas as pd
            import numpy as np
            
            df_ex = pd.DataFrame(llm_examples)
            num_df = df_ex[num_cols].apply(pd.to_numeric, errors="coerce").dropna()
            if len(num_df) > 1:
                corr_matrix = num_df.corr(method="spearman").to_numpy()
                corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
                corr_matrix = (corr_matrix + corr_matrix.T) / 2
                np.fill_diagonal(corr_matrix, 1.0)
                
                from ..copula import ranks_from_array, ranks_to_gaussian, fit_gaussian_covariance
                ranks_list = []
                for col in num_cols:
                    if col in num_df.columns:
                        ranks = ranks_from_array(num_df[col].to_numpy())
                        ranks_list.append(ranks)
                if ranks_list:
                    ranks_matrix = np.column_stack(ranks_list)
                    gaussian_latents = ranks_to_gaussian(ranks_matrix)
                    copula_cov = fit_gaussian_covariance(gaussian_latents)
                    
                    copula_corr = {
                        "spearman": corr_matrix.tolist(),
                        "gaussian_cov": copula_cov.tolist(),
                        "numeric_columns": num_cols,
                    }
        except Exception as e:
            log.warning("Failed to compute copula from LLM examples: %s", e)
    
    result = {
        "version": 1,
        "metadata": result_metadata,
        "categorical_priors": categorical_priors,
        "conditional_numeric": conditional_numeric,
        "conditional_categorical": conditional_categorical,
        "global_numeric": global_numeric,
        "copula_corr": copula_corr,
        "empirical_cdf": empirical_cdf,
        "warnings": [],
        "execution_time_seconds": 0.0,
    }
    
    return result

