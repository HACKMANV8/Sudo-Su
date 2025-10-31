import os

from openschema.pipeline import run_pipeline_from_schema, reproduce


def test_pipeline_smoke_and_reproduce(tmp_path):
    schema = {
        "n_rows": 1000,
        "fields": [
            {"name": "id", "type": "string", "format": "uuid", "unique": True},
            {"name": "role", "type": "category", "categories": ["engineer", "manager", "hr"]},
            {"name": "salary", "type": "int"},
            {"name": "when", "type": "datetime"},
        ],
    }
    out_csv = tmp_path / "out.csv"
    res = run_pipeline_from_schema(schema, seed="seed-123", out_csv=str(out_csv))
    assert res["ok"] is True
    assert res["validation"]["ok"] is True
    assert res["realism"]["realism_score"] >= 0.4
    assert os.path.exists(res["csv_path"]) and os.path.getsize(res["csv_path"]) > 0
    # Reproduce using same seed
    rep = reproduce(schema, seed="seed-123", csv_path=res["csv_path"])
    assert rep["ok"] is True


