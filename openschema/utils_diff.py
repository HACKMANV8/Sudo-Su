from __future__ import annotations

import hashlib
from typing import Dict


def _canonical_bytes(path: str) -> bytes:
    out = bytearray()
    with open(path, "rb") as f:
        for line in f:
            line = line.replace(b"\r\n", b"\n").replace(b"\r", b"\n").rstrip() + b"\n"
            out.extend(line)
    return bytes(out)


def canonical_csv_diff(path_a: str, path_b: str, sample_n: int = 5) -> Dict[str, object]:
    a = _canonical_bytes(path_a)
    b = _canonical_bytes(path_b)
    md5_a = hashlib.md5(a).hexdigest()
    md5_b = hashlib.md5(b).hexdigest()
    if md5_a == md5_b:
        return {"equal": True, "md5": md5_a}
    # Simple line-based diff sample
    lines_a = a.split(b"\n")
    lines_b = b.split(b"\n")
    diffs = []
    for i, (la, lb) in enumerate(zip(lines_a, lines_b)):
        if la != lb:
            diffs.append({"index": i, "a": la.decode(errors="ignore"), "b": lb.decode(errors="ignore")})
            if len(diffs) >= sample_n:
                break
    return {"equal": False, "md5_a": md5_a, "md5_b": md5_b, "samples": diffs}


