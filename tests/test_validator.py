import pandas as pd

from openschema.validator import validate_dataframe, score_realism, generate_validation_report


def make_schema():
    return {
        "n_rows": 100,
        "fields": [
            {"name": "id", "type": "int", "unique": True, "min": 1, "max": 10_000},
            {"name": "role", "type": "category", "categories": ["engineer", "manager", "hr"]},
            {"name": "salary", "type": "int", "min": 30_000, "max": 200_000},
            {"name": "when", "type": "datetime", "metadata": {"historical": True}},
            {"name": "label", "type": "bool"},
        ],
        "class_balance": {"1": 0.3, "0": 0.7},
    }


def test_validate_dataframe_ok():
    schema = make_schema()
    df = pd.DataFrame({
        "id": list(range(1, 101)),
        "role": ["engineer"] * 50 + ["manager"] * 30 + ["hr"] * 20,
        "salary": [80_000] * 100,
        "when": pd.date_range("2020-01-01", periods=100, freq="D"),
        "label": [1] * 30 + [0] * 70,
    })
    res = validate_dataframe(df, schema, tolerance={"class_balance": 0.05})
    assert res["ok"] is True
    assert "per_field" in res and "id" in res["per_field"]


def test_validate_dataframe_failures():
    schema = make_schema()
    df = pd.DataFrame({
        "id": [1] * 100,  # not unique
        "role": ["engineer"] * 100,
        "salary": [10_000] * 100,  # below min
        "when": pd.to_datetime(["2100-01-01"] * 100),  # future for historical (within pandas bounds)
        "label": [1] * 100,
    })
    res = validate_dataframe(df, schema)
    assert res["ok"] is False
    msgs = "\n".join(res["failures"])
    assert "id: uniqueness" in msgs
    assert "salary: 100 values below min" in msgs
    assert "when: 100 timestamps are in the future" in msgs


def test_realism_and_report():
    schema = make_schema()
    df = pd.DataFrame({
        "id": list(range(1, 101)),
        "role": ["engineer"] * 50 + ["manager"] * 30 + ["hr"] * 20,
        "salary": [60_000] * 50 + [100_000] * 30 + [55_000] * 20,
        "when": pd.date_range("2020-01-01", periods=100, freq="D"),
        "label": [1] * 30 + [0] * 70,
    })
    realism = score_realism(df, schema)
    assert 0.0 <= realism["realism_score"] <= 1.0
    rep = generate_validation_report(df, schema)
    assert rep.startswith("# Validation Report")
    assert "Per-field stats" in rep


