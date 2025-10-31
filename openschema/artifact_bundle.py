from __future__ import annotations

import json
import os
import zipfile
from typing import Dict


def create_demo_bundle(fingerprint: str, artifact_dir: str, out_zip: str) -> str:
    os.makedirs(os.path.dirname(out_zip) or ".", exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(artifact_dir):
            for f in files:
                p = os.path.join(root, f)
                arc = os.path.relpath(p, artifact_dir)
                zf.write(p, arcname=arc)
    return out_zip


