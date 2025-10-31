from __future__ import annotations

import json

from openschema.generator import generate_from_schema
from openschema.utils import profile_timer


SCHEMA = {
    "n_rows": 100_000,
    "fields": [
        {"name": "id", "type": "string", "format": "uuid", "unique": True},
        {"name": "role", "type": "category", "categories": ["engineer", "manager", "hr"]},
        {"name": "salary", "type": "int"},
        {"name": "when", "type": "datetime"},
    ],
}


def main() -> None:
    n = SCHEMA["n_rows"]
    with profile_timer(n) as t:
        df, report = generate_from_schema(SCHEMA, seed="bench", force=True)
    print(json.dumps({
        "rows": len(df),
        "elapsed_sec": round(t.elapsed, 3),
        "rows_per_sec": round(t.rows_per_sec, 1),
    }))


if __name__ == "__main__":
    main()


