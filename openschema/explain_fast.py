from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy import stats as scistats


def explain_label_simple(df: pd.DataFrame, label_field: str, schema: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
    out: Dict[str, Any] = {"summary": "", "numeric": [], "categorical": []}
    if label_field not in df.columns:
        return out
    y = pd.to_numeric(df[label_field], errors="coerce").fillna(0).astype(int)
    # Numeric correlations
    numeric = [f["name"] for f in schema.get("fields", []) if f.get("type") in {"int", "float"}]
    num_scores = []
    for col in numeric:
        if col in df.columns:
            x = pd.to_numeric(df[col], errors="coerce").fillna(0)
            if x.nunique() > 1:
                rho, _ = scistats.spearmanr(x, y)
                num_scores.append((col, float(rho)))
    num_scores.sort(key=lambda t: abs(t[1]), reverse=True)
    out["numeric"] = num_scores[:top_k]
    # Categorical lift
    cat_fields = [f["name"] for f in schema.get("fields", []) if f.get("type") == "category"]
    lifts: List[tuple] = []
    p_label = y.mean() or 1e-9
    for col in cat_fields:
        if col in df.columns:
            for v, sub in df.groupby(col):
                p = pd.to_numeric(sub[label_field], errors="coerce").fillna(0).astype(int).mean()
                lifts.append((f"{col}={v}", float((p / p_label) if p_label > 0 else 0.0)))
    lifts.sort(key=lambda t: t[1], reverse=True)
    out["categorical"] = lifts[:top_k]
    # Summary text
    parts = []
    if out["numeric"]:
        parts.append("Top numeric correlates: " + ", ".join([f"{n} (rho={r:.2f})" for n, r in out["numeric"]]))
    if out["categorical"]:
        parts.append("Top categorical lifts: " + ", ".join([f"{n} (x{l:.2f})" for n, l in out["categorical"]]))
    out["summary"] = ". ".join(parts)
    # Sample rows
    pos = df[y == 1].head(2)
    neg = df[y == 0].head(2)
    out["samples"] = {
        "positive_examples": pos.to_dict(orient="records"),
        "negative_examples": neg.to_dict(orient="records"),
    }
    return out


