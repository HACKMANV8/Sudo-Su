from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats as scistats


ALLOWED_TYPES = {"int", "float", "string", "datetime", "category", "bool", "ip"}


def _safe_coerce_series(s: pd.Series, ftype: str) -> pd.Series:
    if ftype == "int":
        return pd.to_numeric(s, errors="coerce").dropna().round().astype("Int64").reindex(s.index)
    if ftype == "float":
        return pd.to_numeric(s, errors="coerce").astype(float)
    if ftype == "bool":
        mapping = {"true": 1, "false": 0, True: 1, False: 0, 1: 1, 0: 0, "1": 1, "0": 0}
        coerced = s.map(lambda x: mapping.get(str(x).lower(), np.nan) if isinstance(x, str) else mapping.get(x, np.nan))
        return coerced.astype("Int64")
    if ftype == "datetime":
        return pd.to_datetime(s, errors="coerce")
    # string, category, ip: keep as is (coercion not strict)
    return s


def _null_frac(s: pd.Series) -> float:
    return float(s.isna().mean()) if hasattr(s, "isna") else 0.0


def validate_dataframe(df: pd.DataFrame, schema: Dict[str, Any], tolerance: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    tol = tolerance or {}
    failures: List[str] = []
    per_field: Dict[str, Dict[str, Any]] = {}

    for f in schema.get("fields", []):
        name = f.get("name")
        ftype = f.get("type")
        if name not in df.columns:
            failures.append(f"Missing field: {name}")
            continue
        if ftype not in ALLOWED_TYPES:
            failures.append(f"Unsupported type in schema for {name}: {ftype}")
            continue

        s = df[name]
        original = s
        s = _safe_coerce_series(s, ftype)

        # Type conformance rough check
        if ftype in {"int", "float"} and not pd.api.types.is_numeric_dtype(s):
            failures.append(f"{name}: not numeric/coercible")

        # Ranges for numeric
        if ftype in {"int", "float"}:
            vmin = f.get("min")
            vmax = f.get("max")
            if vmin is not None and pd.notna(vmin):
                below = int((s.dropna() < vmin).sum())
                if below > 0:
                    failures.append(f"{name}: {below} values below min {vmin}")
            if vmax is not None and pd.notna(vmax):
                above = int((s.dropna() > vmax).sum())
                if above > 0:
                    failures.append(f"{name}: {above} values above max {vmax}")

        # Null fraction
        allowed_null = float(f.get("nullable", 0.0)) + float(tol.get(name, 0.0))
        nf = _null_frac(s)
        if nf > allowed_null + 1e-9:
            failures.append(f"{name}: null_frac {nf:.3f} exceeds allowed {allowed_null:.3f}")

        # Uniqueness
        if f.get("unique"):
            # Skip strict uniqueness for UUID-formatted strings; generally guaranteed by generator
            if ftype == "string" and (f.get("format") or "").lower() == "uuid":
                pass
            else:
                nunique = int(pd.Series(s).nunique(dropna=True))
                total = int(len(s.dropna()))
                if nunique != total:
                    failures.append(f"{name}: uniqueness violated ({nunique} unique of {len(df)})")

        # Datetime not in future (basic heuristic: if 'historical' metadata flag or name suggests)
        if ftype == "datetime":
            meta = f.get("metadata", {}) or {}
            historical = bool(meta.get("historical", False) or ("join" in name or "start" in name))
            if historical:
                # Compare with naive 'now' to match typical tz-naive series
                now = pd.Timestamp.utcnow().tz_localize(None)
                future = int((s.dropna() > now).sum())
                if future > 0:
                    failures.append(f"{name}: {future} timestamps are in the future for historical field")

        # Per-field stats
        stats: Dict[str, Any] = {
            "nunique": int(pd.Series(s).nunique(dropna=True)),
            "null_frac": nf,
        }
        if ftype in {"int", "float"}:
            sd = s.dropna()
            if len(sd) > 0:
                stats.update({
                    "mean": float(sd.mean()),
                    "std": float(sd.std(ddof=0)),
                    "min": float(sd.min()),
                    "max": float(sd.max()),
                })
        per_field[name] = stats

    # Class balance check if present
    cb = schema.get("class_balance")
    if cb and "label" in df.columns:
        target = float(cb.get("1") if "1" in cb else cb.get(1))
        if target is not None:
            p = float((df["label"] == 1).mean())
            tol_cb = float(tol.get("class_balance", 0.01))
            if abs(p - target) > tol_cb + 1e-9:
                failures.append(f"label: class balance {p:.3f} differs from target {target:.3f} by > {tol_cb:.3f}")

    ok = len(failures) == 0
    return {"ok": ok, "failures": failures, "per_field": per_field}


def _safe_entropy(values: pd.Series) -> float:
    vc = values.value_counts(dropna=True)
    if len(vc) == 0:
        return 0.0
    p = (vc / vc.sum()).to_numpy()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def score_realism(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    score = 1.0
    messages: List[str] = []

    # Numeric stats
    for f in schema.get("fields", []):
        name = f.get("name")
        if name not in df.columns:
            continue
        t = f.get("type")
        s = df[name]
        if t in {"int", "float"}:
            sd = pd.to_numeric(s, errors="coerce").dropna()
            if len(sd) > 3:
                skew = float(scistats.skew(sd))
                kurt = float(scistats.kurtosis(sd))
                # Penalize extreme values
                if abs(skew) > 2:
                    score *= 0.9
                    messages.append(f"{name}: high skew {skew:.2f}")
                if abs(kurt) > 7:
                    score *= 0.9
                    messages.append(f"{name}: high kurtosis {kurt:.2f}")

    # Category stats
    for f in schema.get("fields", []):
        name = f.get("name")
        if name not in df.columns:
            continue
        if f.get("type") == "category":
            s = df[name]
            ent = _safe_entropy(s)
            vc = s.value_counts(dropna=True)
            top_prop = float((vc.iloc[0] / vc.sum()) if len(vc) else 0.0)
            if top_prop > 0.9:
                score *= 0.9
                messages.append(f"{name}: top-1 proportion {top_prop:.2f} too high")

    # Relationship check: role -> salary
    if {"role", "salary"}.issubset(df.columns):
        g = df.groupby("role")["salary"].mean()
        if len(g) >= 2:
            try:
                base = float(g.min()) + 1e-9
                spread = float((g.max() - g.min()) / base)
                if spread < 0.05:
                    score *= 0.9
                    messages.append("role→salary mapping weak (means too similar)")
            except Exception:
                pass

    score = max(0.0, min(1.0, score))
    return {"realism_score": score, "explanations": messages}


def generate_validation_report(df: pd.DataFrame, schema: Dict[str, Any]) -> str:
    res = validate_dataframe(df, schema)
    realism = score_realism(df, schema)

    lines: List[str] = []
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"Rows: {len(df)}  |  Columns: {len(df.columns)}")
    lines.append(f"Status: {'OK' if res['ok'] else 'FAIL'}")
    lines.append(f"Realism score: {realism['realism_score']:.2f}")
    lines.append("")
    if res["failures"]:
        lines.append("## Failures")
        for msg in res["failures"][:10]:
            lines.append(f"- {msg}")
        if len(res["failures"]) > 10:
            lines.append(f"- ... and {len(res['failures']) - 10} more")
        lines.append("")

    lines.append("## Per-field stats")
    for k, v in res["per_field"].items():
        parts = ", ".join(f"{kk}={vv}" for kk, vv in v.items())
        lines.append(f"- {k}: {parts}")

    # Sample rows
    lines.append("")
    lines.append("## Sample rows")
    try:
        lines.append(df.head(3).to_markdown(index=False))
    except ImportError:
        # Fallback if tabulate not installed
        lines.append(df.head(3).to_string(index=False))

    # Suggestions
    if realism["explanations"]:
        lines.append("")
        lines.append("## Warnings / Suggestions")
        for m in realism["explanations"]:
            lines.append(f"- {m}")

    return "\n".join(lines)


