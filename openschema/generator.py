from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Dict, List, Tuple, Optional, Literal, Callable

import numpy as np
import pandas as pd
from faker import Faker

from .utils import (
    init_seed,
    sample_datetimes_uniform,
    derive_subseed,
    normalize_seed,
    deterministic_uuid,
    compute_file_hash,
)
from .conditional import learn_conditionals_from_csv
from .copula import apply_rank_copula
from .anomalies import generate_anomalies


ROLE_SALARY_DEFAULTS: Dict[str, Tuple[float, float]] = {
    "engineer": (70000.0, 10000.0),
    "manager": (90000.0, 15000.0),
    "hr": (60000.0, 8000.0),
    "finance": (80000.0, 12000.0),
    "contractor": (40000.0, 10000.0),
}


def _md5_of_series(strings: List[str]) -> str:
    m = hashlib.md5()
    for s in strings:
        m.update(s.encode("utf-8"))
    return m.hexdigest()


def _ensure_unique(values: List[Any], name: str, rng: np.random.Generator, report_repairs: List[str]) -> List[Any]:
    n = len(values)
    seen = set()
    result = []
    repaired = False
    for i, v in enumerate(values):
        key = v
        if key in seen:
            repaired = True
            # Append deterministic suffix based on index to make unique
            suffix = str(i)
            key = f"{v}_{suffix}"
        seen.add(key)
        result.append(key)
    if repaired:
        report_repairs.append(f"Field '{name}': duplicate values repaired via deterministic suffixes")
    return result


def _uuid5_sequence(seed: int, n: int) -> List[str]:
    ns = uuid.UUID(int=seed & ((1 << 128) - 1))
    return [str(uuid.uuid5(ns, f"idx-{i}")) for i in range(n)]


def generate_from_schema(
    schema: Dict[str, Any],
    seed: int | str = 42,
    fast_mode: bool = True,
    max_rows_limit: int = 5_000_000,
    force: bool = False,
    source_csv: Optional[str] = None,
    mode: Optional[str] = None,
    target_rows: Optional[int] = None,
    additional_rows: Optional[int] = None,
    preview_rows: Optional[int] = None,
    chunk_size: Optional[int] = None,
    on_chunk_generated: Optional[Callable[[pd.DataFrame, Dict[str, Any]], None]] = None,
    gen_mode: Literal['fast','hf'] = 'fast',
    use_rank_copula: bool = False,
    repair_policy: Literal['append_index','uuid_suffix','fail'] = 'append_index',
    anomaly_spec: Optional[Dict[str, Any]] = None,
) -> tuple[pd.DataFrame, Dict[str, Any]]:
    start_time = time.time()
    rng_master = init_seed(seed)
    master_norm = normalize_seed(seed)
    # Derive subsystem RNGs to avoid cross-talk
    rng_fields = np.random.default_rng(derive_subseed(master_norm, "fields"))
    rng_ids = np.random.default_rng(derive_subseed(master_norm, "ids"))
    rng_text = np.random.default_rng(derive_subseed(master_norm, "text"))
    rng_dates = np.random.default_rng(derive_subseed(master_norm, "dates"))
    faker = Faker()

    n_rows = int(schema.get("n_rows", 0))
    if preview_rows is not None:
        n_rows = int(preview_rows)
    if n_rows <= 0:
        n_rows = 0
    if n_rows > max_rows_limit and not force:
        raise ValueError(
            f"Requested rows {n_rows} exceeds safety limit {max_rows_limit}. "
            f"Use --force to override (may consume significant memory/CPU)."
        )

    fields: List[Dict[str, Any]] = schema.get("fields", [])
    col_data: Dict[str, List[Any]] = {}
    repairs: List[str] = []
    warnings: List[str] = []
    original_row_count: int = 0
    csv_hash: Optional[str] = None

    # Ingestion: if source_csv provided, load and seed augmentation params
    df_existing: Optional[pd.DataFrame] = None
    if source_csv:
        df_existing = pd.read_csv(source_csv)
        csv_hash = compute_file_hash(source_csv, algo="md5")
        original_row_count = len(df_existing)
        # Validate columns present
        missing = [f["name"] for f in fields if f["name"] not in df_existing.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        # Empirical distributions for categories
        empirical_probs: Dict[str, np.ndarray] = {}
        for f in fields:
            if f.get("type") == "category":
                s = df_existing[f["name"]].dropna()
                vc = s.value_counts()
                if len(vc) > 0:
                    probs = (vc / vc.sum()).reindex(f.get("categories", list(vc.index))).fillna(0.0).to_numpy()
                    if probs.sum() > 0:
                        empirical_probs[f["name"]] = probs
        # Conditional role->salary
        cond_means: Dict[str, Tuple[float, float]] = {}
        if "role" in df_existing.columns and "salary" in df_existing.columns:
            g = df_existing.groupby("role")["salary"].agg(["mean", "std"]).fillna(0.0)
            if len(g) >= 1:
                for r, row in g.iterrows():
                    cond_means[str(r)] = (float(row["mean"]), float(row["std"]) or 1.0)
                # override defaults if present
                ROLE_SALARY_DEFAULTS.update(cond_means)

        # Determine rows to add
        if (mode or "").lower() == "append":
            if not target_rows:
                raise ValueError("append mode requires target_rows")
            if target_rows < original_row_count:
                warnings.append("target_rows less than existing rows; no rows appended")
                additional_rows = 0
            else:
                additional_rows = target_rows - original_row_count
        elif (mode or "").lower() == "augment":
            if additional_rows is None:
                raise ValueError("augment mode requires additional_rows")
        else:
            # default: generate from scratch
            pass

        # For append/augment, set generation rows to additional_rows
        if (mode or "") in {"append", "augment"}:
            n_rows = int(additional_rows or 0)

    # Handle class balance if specified at top level for a 'label' field
    class_balance = schema.get("class_balance")
    precomputed_label = None
    if class_balance and "label" in {f.get("name") for f in fields}:
        # Expect mapping like {'1': p, '0': 1-p}
        p1 = None
        if isinstance(class_balance, dict):
            if "1" in class_balance:
                p1 = float(class_balance["1"])
            elif 1 in class_balance:
                p1 = float(class_balance[1])
        if p1 is not None:
            n1 = int(round(p1 * n_rows))
            n0 = n_rows - n1
            labels = np.array([1] * n1 + [0] * n0, dtype=int)
            perm = rng_fields.permutation(n_rows)
            labels = labels[perm]
            precomputed_label = labels.tolist()

    # Conditional overrides from schema metadata
    overrides = (schema.get("metadata") or {}).get("conditional_overrides") or {}
    if isinstance(overrides, dict) and overrides:
        for role, vals in overrides.items():
            try:
                mu = float(vals.get("mean"))
                sd = float(vals.get("std", 1.0)) or 1.0
                ROLE_SALARY_DEFAULTS[str(role)] = (mu, sd)
            except Exception:
                warnings.append(f"Invalid conditional_overrides for role {role}")
    
    # Extract LLM priors from metadata if available
    llm_priors_dict = (schema.get("metadata") or {}).get("llm_priors", {})
    llm_conditional_mappings = {}
    if llm_priors_dict:
        llm_deps = llm_priors_dict.get("dependencies", [])
        for dep in llm_deps:
            if isinstance(dep, dict):
                parent = dep.get("parent") or dep.get("from")
                child = dep.get("child") or dep.get("to")
                condition = dep.get("condition") or dep.get("rule")
                
                # Store conditional mappings for numeric fields
                if parent and child and isinstance(condition, dict):
                    # Map format: {field_name: {parent_col: {parent_val: {mean, std}}}}
                    if child not in llm_conditional_mappings:
                        llm_conditional_mappings[child] = {}
                    llm_conditional_mappings[child][parent] = condition

    # Detect conditional driver (role)
    role_field_name = None
    for f in fields:
        if f.get("name") == "role" or (f.get("metadata") or {}).get("conditional_driver"):
            role_field_name = f.get("name")
            break

    # If role exists and salary fields exist, sample role first
    role_values: List[str] | None = None
    if role_field_name:
        role_field = next(f for f in fields if f.get("name") == role_field_name)
        cats = role_field.get("categories") or []
        probs = role_field.get("probs")
        if not cats:
            warnings.append("Role field has no categories; defaulting to 'engineer'")
            role_values = ["engineer"] * n_rows
        else:
            if probs is None:
                probs = np.full(len(cats), 1.0 / len(cats))
            role_values = rng_fields.choice(cats, size=n_rows, p=np.array(probs)).tolist()
        col_data[role_field_name] = role_values

    # Generate remaining fields
    for f in fields:
        name = f.get("name")
        ftype = f.get("type")
        unique = bool(f.get("unique", False))

        if role_field_name and name == role_field_name:
            continue

        if name == "label" and precomputed_label is not None:
            col_data[name] = precomputed_label
            continue

        if ftype == "category":
            # Check LLM priors for categorical distribution
            llm_col_prior = None
            if llm_priors_dict:
                llm_priors_cols = llm_priors_dict.get("priors", {})
                llm_col_prior = llm_priors_cols.get(name)
            
            if llm_col_prior and llm_col_prior.get("type") == "categorical":
                # Use LLM-provided categories and probabilities
                cats = llm_col_prior.get("categories", f.get("categories", []))
                probs = llm_col_prior.get("probs", f.get("probs"))
            else:
                # Use schema categories
                cats = f.get("categories") or []
                probs = f.get("probs")
            
            if not cats:
                vals = [None] * n_rows
            else:
                p = None if probs is None else np.array(probs)
                vals = rng_fields.choice(cats, size=n_rows, p=p).tolist()
            if unique:
                vals = _ensure_unique(vals, name, rng_fields, repairs)
            col_data[name] = vals

        elif ftype == "int":
            # Check LLM priors for numeric distribution
            llm_col_prior = None
            if llm_priors_dict:
                llm_priors_cols = llm_priors_dict.get("priors", {})
                llm_col_prior = llm_priors_cols.get(name)
            
            # Override schema params with LLM priors if available
            if llm_col_prior and llm_col_prior.get("type") == "numeric":
                dist_info = llm_col_prior.get("distribution", {})
                if isinstance(dist_info, dict):
                    if f.get("mean") is None:
                        f["mean"] = dist_info.get("mean")
                    if f.get("std") is None:
                        f["std"] = dist_info.get("std")
                    if f.get("min") is None:
                        f["min"] = dist_info.get("min")
                    if f.get("max") is None:
                        f["max"] = dist_info.get("max")
            
            dist = (f.get("distribution") or "uniform").lower()
            if role_field_name and "salary" in name and role_values is not None:
                # Conditional per-role salary
                means_stds = ROLE_SALARY_DEFAULTS
                mu = np.array([means_stds.get(r, means_stds["engineer"])[0] for r in role_values])
                sd = np.array([means_stds.get(r, means_stds["engineer"])[1] for r in role_values])
                arr = rng_fields.normal(loc=mu, scale=sd)
                vals = np.round(arr).astype(int).tolist()
            elif dist == "normal":
                mu = float(f.get("mean", 0))
                sd = float(f.get("std", 1))
                vals = np.round(rng_fields.normal(loc=mu, scale=sd, size=n_rows)).astype(int).tolist()
            else:
                lo = int(f.get("min", 0))
                hi = int(f.get("max", 100))
                if unique:
                    domain = hi - lo + 1
                    if domain < n_rows:
                        raise ValueError(
                            f"Uniqueness impossible: field '{name}' needs {n_rows} unique ints in range [{lo},{hi}] (size {domain}). "
                            f"Increase max, widen range, or disable unique."
                        )
                    vals = rng_fields.choice(np.arange(lo, hi + 1), size=n_rows, replace=False).astype(int).tolist()
                else:
                    vals = rng_fields.integers(lo, hi + 1, size=n_rows).tolist()
            if unique:
                # Already ensured in uniform branch; for other branches, fallback to suffix if collisions
                if dist != "uniform" and (len(set(vals)) < len(vals)):
                    vals = _ensure_unique(vals, name, rng_fields, repairs)
                    warnings.append(f"Unique repairs applied for field '{name}' by suffixing duplicates")
            col_data[name] = vals

        elif ftype == "float":
            # Check LLM priors for numeric distribution
            llm_col_prior = None
            if llm_priors_dict:
                llm_priors_cols = llm_priors_dict.get("priors", {})
                llm_col_prior = llm_priors_cols.get(name)
            
            # Override schema params with LLM priors if available
            if llm_col_prior and llm_col_prior.get("type") == "numeric":
                dist_info = llm_col_prior.get("distribution", {})
                if isinstance(dist_info, dict):
                    if f.get("mean") is None:
                        f["mean"] = dist_info.get("mean")
                    if f.get("std") is None:
                        f["std"] = dist_info.get("std")
                    if f.get("min") is None:
                        f["min"] = dist_info.get("min")
                    if f.get("max") is None:
                        f["max"] = dist_info.get("max")
            
            dist = (f.get("distribution") or "uniform").lower()
            # Check for conditional generation (category -> amount)
            conditional_driver = None
            conditional_mappings = None
            # Look for category fields that might drive this numeric field
            for cat_f in fields:
                if cat_f.get("type") == "category":
                    cat_name = cat_f.get("name")
                    if cat_name in col_data and cat_name:
                        # Check if schema has conditional mappings
                        meta = f.get("metadata") or {}
                        cond_map = meta.get("conditional_on")
                        if cond_map and cat_name in cond_map:
                            conditional_driver = cat_name
                            conditional_mappings = cond_map[cat_name]
                            break
                        # Check LLM priors for conditional mappings
                        if name in llm_conditional_mappings and cat_name in llm_conditional_mappings[name]:
                            conditional_driver = cat_name
                            conditional_mappings = llm_conditional_mappings[name][cat_name]
                            break
                        # Auto-detect common patterns: category -> amount/price
                        if ("category" in cat_name.lower() or "product" in cat_name.lower()) and ("amount" in name.lower() or "price" in name.lower() or "cost" in name.lower()):
                            conditional_driver = cat_name
                            # Default realistic mappings
                            conditional_mappings = {
                                "electronics": {"mean": 800, "std": 400},
                                "clothing": {"mean": 150, "std": 100},
                                "food": {"mean": 50, "std": 30},
                                "books": {"mean": 25, "std": 15},
                                "toys": {"mean": 100, "std": 60}
                            }
                            break
            
            if conditional_driver and conditional_mappings:
                category_values = col_data[conditional_driver]
                vals = []
                for cat in category_values:
                    mapping = conditional_mappings.get(str(cat), {})
                    if mapping:
                        mu = float(mapping.get("mean", f.get("mean", 150)))
                        sd = float(mapping.get("std", f.get("std", 50)))
                        val = rng_fields.normal(loc=mu, scale=sd)
                        # Clamp to min/max if specified
                        if f.get("min") is not None:
                            val = max(float(f.get("min")), val)
                        if f.get("max") is not None:
                            val = min(float(f.get("max")), val)
                        vals.append(val)
                    else:
                        # Fallback to normal distribution
                        mu = float(f.get("mean", 0.0))
                        sd = float(f.get("std", 1.0))
                        vals.append(rng_fields.normal(loc=mu, scale=sd))
                vals = vals
            elif dist == "normal":
                mu = float(f.get("mean", 0.0))
                sd = float(f.get("std", 1.0))
                vals = rng_fields.normal(loc=mu, scale=sd, size=n_rows).tolist()
            else:
                lo = float(f.get("min", 0.0))
                hi = float(f.get("max", 100.0))
                vals = (lo + (hi - lo) * rng_fields.random(n_rows)).tolist()
            if unique:
                vals = _ensure_unique(vals, name, rng_fields, repairs)
            col_data[name] = vals

        elif ftype == "string":
            fmt = (f.get("format") or "").lower()
            # If crawl examples provided, sample deterministically
            crawl_examples = (schema.get("metadata", {}).get("crawl_examples", {}) or {}).get(name)
            if crawl_examples:
                ex_rng = np.random.default_rng(derive_subseed(master_norm, f"examples::{name}"))
                vals = ex_rng.choice(list(crawl_examples), size=n_rows, replace=True).tolist()
            elif fmt == "uuid":
                ns = derive_subseed(master_norm, f"uuid::{name}")
                vals = [deterministic_uuid(ns, i, name) for i in range(n_rows)]
            elif fmt == "email":
                vals = [Faker().email() for _ in range(n_rows)]
            elif fmt == "name":
                vals = [Faker().name() for _ in range(n_rows)]
            else:
                vals = [Faker().word() for _ in range(n_rows)]
            if unique:
                vals = _ensure_unique(vals, name, rng_fields, repairs)
            col_data[name] = vals

        elif ftype == "datetime":
            lo = f.get("min")
            hi = f.get("max")
            if not lo or not hi:
                # Default to a recent year range
                from datetime import datetime

                lo = datetime(2020, 1, 1)
                hi = datetime(2021, 1, 1)
            vals = sample_datetimes_uniform(lo, hi, n_rows, rng_dates)
            col_data[name] = vals

        elif ftype == "bool":
            p = None
            cb = f.get("class_balance") or {}
            if "1" in cb:
                p = float(cb["1"])
            if p is None:
                p = float(f.get("p", 0.5))
            vals = (rng_fields.random(n_rows) < p).astype(int).tolist()
            col_data[name] = vals

        elif ftype == "ip":
            # Faker is deterministic after init_seed; generate IPv4 values
            vals = [Faker().ipv4() for _ in range(n_rows)]
            if unique:
                vals = _ensure_unique(vals, name, rng, repairs)
            col_data[name] = vals

        else:
            raise ValueError(f"Unsupported field type: {ftype}")

    df = pd.DataFrame(col_data, columns=[f.get("name") for f in fields if f.get("name") in col_data])

    # Rank-copula adjustment if requested later

    # If augment/append, integrate with existing CSV
    if df_existing is not None and (mode or "") in {"append", "augment"}:
        add_n = int(additional_rows or 0)
        if add_n > 0:
            # Use empirical category probs where available
            for f in fields:
                if f.get("type") == "category" and f["name"] in df.columns and f.get("probs") is None:
                    cats = f.get("categories") or []
                    # We already sampled earlier; for simplicity, keep as-is since row count matches
                    pass
            # Ensure unique key not colliding with existing
            for f in fields:
                if f.get("unique") and f.get("type") == "string" and (f.get("format") or "").lower() == "uuid":
                    name = f["name"]
                    existing_set = set(df_existing[name].astype(str).tolist())
                    vals = df[name].astype(str).tolist()
                    fixed: List[str] = []
                    idx = 0
                    for v in vals:
                        nv = v
                        while nv in existing_set:
                            idx += 1
                            nv = deterministic_uuid(derive_subseed(master_norm, f"uuid::{name}"), idx + n_rows, name)
                        existing_set.add(nv)
                        fixed.append(nv)
                    df[name] = fixed
            combined = pd.concat([df_existing, df.iloc[:add_n]], ignore_index=True)
        else:
            combined = df_existing.copy()
        df = combined

    duration = time.time() - start_time

    # Apply rank copula if requested
    if use_rank_copula and df_existing is not None:
        num_cols = [f["name"] for f in fields if f.get("type") in {"int", "float"} and f["name"] in df.columns]
        if num_cols and len(df_existing) >= 10 and len(df) > 0:
            df = apply_rank_copula(df_existing, df, num_cols)

    # Anomaly injection
    injected = []
    if anomaly_spec and isinstance(anomaly_spec, dict):
        n_anom = int(anomaly_spec.get("n", 0) or 0)
        if n_anom > 0:
            an_rng = np.random.default_rng(derive_subseed(master_norm, "anomalies"))
            df_anom = generate_anomalies(schema, n_anom, anomaly_spec, an_rng)
            df = pd.concat([df, df_anom], ignore_index=True)
            injected = df_anom.head(5).to_dict(orient="records")

    # Stats
    per_field_stats: Dict[str, Dict[str, Any]] = {}
    for col in df.columns:
        s = df[col]
        stats: Dict[str, Any] = {
            "nunique": int(s.nunique(dropna=False)),
            "null_frac": float(s.isna().mean()) if hasattr(s, "isna") else 0.0,
        }
        if pd.api.types.is_numeric_dtype(s):
            stats["mean"] = float(s.mean())
            stats["std"] = float(s.std(ddof=0))
        per_field_stats[col] = stats

    # Fingerprint: combine normalized_seed + schema hash + csv hash
    import json as _json
    schema_hash = hashlib.md5(_json.dumps(schema, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    csv_md5 = hashlib.md5(df.to_csv(index=False).encode("utf-8")).hexdigest()

    report: Dict[str, Any] = {
        "seed": seed,
        "normalized_seed": int(master_norm),
        "user_seed_raw": seed,
        "rows_generated": int(len(df)),
        "duration_seconds": float(duration),
        "warnings": warnings,
        "repairs": repairs,
        "suggestions": [],
        "per_field_stats": per_field_stats,
        "schema_hash": schema_hash,
        "csv_hash": csv_md5,
        "fingerprint": hashlib.md5(f"{master_norm}:{schema_hash}:{csv_md5}".encode("utf-8")).hexdigest(),
        "source_csv_hash": csv_hash,
        "original_row_count": original_row_count,
        "added_rows": int(len(df)) - int(original_row_count),
        "injected_anomalies": injected,
    }

    # Progressive chunk callback
    if chunk_size and on_chunk_generated:
        for i in range(0, len(df), int(chunk_size)):
            ch = df.iloc[i : i + int(chunk_size)]
            on_chunk_generated(ch, {"offset": i, "rows": len(ch)})

    return df, report


