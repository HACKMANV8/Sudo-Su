from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from faker import Faker

from .utils import (
    init_seed,
    sample_datetimes_uniform,
    derive_subseed,
    normalize_seed,
    deterministic_uuid,
)


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
    if n_rows <= 0:
        n_rows = 0
    if n_rows > max_rows_limit:
        raise ValueError(f"Requested rows {n_rows} exceeds max_rows_limit {max_rows_limit}")

    fields: List[Dict[str, Any]] = schema.get("fields", [])
    col_data: Dict[str, List[Any]] = {}
    repairs: List[str] = []
    warnings: List[str] = []

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
                vals = rng_fields.integers(lo, hi + 1, size=n_rows).tolist()
            if unique:
                vals = _ensure_unique(vals, name, rng_fields, repairs)
            col_data[name] = vals

        elif ftype == "float":
            dist = (f.get("distribution") or "uniform").lower()
            if dist == "normal":
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
            if fmt == "uuid":
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

    duration = time.time() - start_time

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
        "per_field_stats": per_field_stats,
        "schema_hash": schema_hash,
        "csv_hash": csv_md5,
        "fingerprint": hashlib.md5(f"{master_norm}:{schema_hash}:{csv_md5}".encode("utf-8")).hexdigest(),
    }

    return df, report


