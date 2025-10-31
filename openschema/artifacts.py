from __future__ import annotations

import os
import struct
import zlib
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _save_png(array: np.ndarray, out_path: str) -> None:
    h, w = array.shape[:2]
    if array.ndim == 2:
        # grayscale to RGB
        array = np.stack([array] * 3, axis=-1)
    array = array.astype(np.uint8)
    # PNG writer (RGB8)
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    # IHDR
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    # IDAT
    raw = b"".join([b"\x00" + array[y].tobytes() for y in range(h)])
    idat = zlib.compress(raw, 6)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(out_path, "wb") as f:
        f.write(data)


def create_numeric_histograms(df: pd.DataFrame, schema: Dict[str, Any], out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []
    fields = [f["name"] for f in schema.get("fields", []) if f.get("type") in {"int", "float"}]
    for name in fields:
        if name not in df.columns:
            continue
        s = pd.to_numeric(df[name], errors="coerce").dropna()
        if s.empty:
            continue
        hist, edges = np.histogram(s.to_numpy(), bins=20)
        H, W = 400, 600
        img = np.full((H, W), 255, dtype=np.uint8)
        m = hist.max() or 1
        bar_w = max(1, W // len(hist))
        for i, v in enumerate(hist):
            h = int((v / m) * (H - 20))
            x0 = i * bar_w
            img[H - h - 1 : H - 1, x0 : x0 + bar_w] = 40
        path = os.path.join(out_dir, f"hist_{name}.png")
        _save_png(img, path)
        paths.append(path)
    return paths


def create_categorical_bars(df: pd.DataFrame, schema: Dict[str, Any], out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []
    fields = [f["name"] for f in schema.get("fields", []) if f.get("type") == "category"]
    for name in fields:
        if name not in df.columns:
            continue
        vc = df[name].value_counts()
        if vc.empty:
            continue
        H, W = 400, 600
        img = np.full((H, W), 255, dtype=np.uint8)
        m = vc.max() or 1
        bar_w = max(1, W // len(vc))
        for i, v in enumerate(vc.to_numpy()):
            h = int((v / m) * (H - 20))
            x0 = i * bar_w
            img[H - h - 1 : H - 1, x0 : x0 + bar_w] = 60
        path = os.path.join(out_dir, f"bar_{name}.png")
        _save_png(img, path)
        paths.append(path)
    return paths


def create_correlation_heatmap(df: pd.DataFrame, numeric_fields: List[str], out_path: str) -> str:
    sub = df[numeric_fields].apply(pd.to_numeric, errors="coerce").dropna()
    if sub.empty:
        img = np.full((50, 50), 200, dtype=np.uint8)
        _save_png(img, out_path)
        return out_path
    corr = sub.corr(method="spearman").to_numpy()
    corr = (corr - corr.min()) / (corr.max() - corr.min() + 1e-9)
    img = (255 - (corr * 255)).astype(np.uint8)
    _save_png(img, out_path)
    return out_path


def create_label_pie(df: pd.DataFrame, label_field: str, out_path: str) -> str:
    vc = df[label_field].value_counts()
    total = vc.sum() or 1
    H, W = 400, 400
    img = np.full((H, W), 255, dtype=np.uint8)
    # Draw a simple ring with proportion as radius shading
    pct = float(vc.iloc[0] / total)
    rad_inner = 80
    rad = int(80 + 80 * pct)
    cy, cx = H // 2, W // 2
    yy, xx = np.ogrid[:H, :W]
    dist2 = (yy - cy) ** 2 + (xx - cx) ** 2
    img[(dist2 < rad**2) & (dist2 > rad_inner**2)] = 100
    _save_png(img, out_path)
    return out_path


def create_role_salary_scatter(df: pd.DataFrame, role_field: str, salary_field: str, out_path: str) -> str:
    if role_field not in df.columns or salary_field not in df.columns:
        img = np.full((100, 100), 220, dtype=np.uint8)
        _save_png(img, out_path)
        return out_path
    H, W = 400, 600
    img = np.full((H, W), 255, dtype=np.uint8)
    roles = pd.Categorical(df[role_field]).codes
    sal = pd.to_numeric(df[salary_field], errors="coerce").fillna(0).to_numpy()
    if sal.max() == sal.min():
        sal = sal + 1
    x = (roles - roles.min()) / max(1, (roles.max() - roles.min()))
    y = (sal - sal.min()) / (sal.max() - sal.min())
    xs = (x * (W - 10)).astype(int)
    ys = (H - 10 - (y * (H - 10))).astype(int)
    img[ys, xs] = 0
    _save_png(img, out_path)
    return out_path


def create_all_artifacts(df: pd.DataFrame, schema: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    artifacts: Dict[str, Any] = {}
    num_paths = create_numeric_histograms(df, schema, out_dir)
    cat_paths = create_categorical_bars(df, schema, out_dir)
    num_fields = [f["name"] for f in schema.get("fields", []) if f.get("type") in {"int", "float"}]
    heat_path = os.path.join(out_dir, "corr_heatmap.png")
    create_correlation_heatmap(df, num_fields, heat_path)
    artifacts["numeric_histograms"] = num_paths
    artifacts["categorical_bars"] = cat_paths
    artifacts["correlation_heatmap"] = heat_path
    # Optional extras
    if "role" in df.columns and "salary" in df.columns:
        scatter = os.path.join(out_dir, "role_salary_scatter.png")
        create_role_salary_scatter(df, "role", "salary", scatter)
        artifacts["role_salary_scatter"] = scatter
    return artifacts


