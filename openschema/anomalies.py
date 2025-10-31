from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def generate_anomalies(schema: Dict[str, Any], n_anomalies: int, anomaly_spec: Dict[str, Any], rng: np.random.Generator) -> pd.DataFrame:
    fields = schema.get("fields", [])
    cols = [f["name"] for f in fields]
    data: Dict[str, List[Any]] = {c: [] for c in cols}
    t = (anomaly_spec or {}).get("type", "large_exfil")
    for i in range(n_anomalies):
        for f in fields:
            name = f["name"]
            ftype = f.get("type")
            if t == "large_exfil" and name in {"bytes_out", "bytes"} and ftype in {"int", "float"}:
                val = float(1e9) * (1.0 + 0.1 * i)
                data[name].append(val if ftype == "float" else int(val))
            elif t == "out_of_hours" and ftype == "datetime":
                # 03:00 fixed
                data[name].append(pd.Timestamp("2020-01-01 03:00:00"))
            elif t == "suspicious_ip_mix" and ftype == "ip":
                data[name].append(f"10.0.{(i//256)%256}.{i%256}")
            elif t == "rare_file_types" and name in {"file_ext", "extension"}:
                data[name].append(".key")
            else:
                # Fallback plausible defaults
                if ftype == "int":
                    data[name].append(int(rng.integers(0, 1000)))
                elif ftype == "float":
                    data[name].append(float(rng.random()))
                elif ftype == "string":
                    data[name].append(f"anom_{i}")
                elif ftype == "bool":
                    data[name].append(int(rng.random() < 0.1))
                elif ftype == "datetime":
                    data[name].append(pd.Timestamp("2020-01-01"))
                elif ftype == "ip":
                    data[name].append("10.0.0.1")
                elif ftype == "category":
                    cats = f.get("categories") or ["A", "B"]
                    data[name].append(cats[i % len(cats)])
                else:
                    data[name].append(None)
    return pd.DataFrame(data)


