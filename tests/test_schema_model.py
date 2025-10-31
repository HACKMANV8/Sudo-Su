import json
import os

import pytest

from openschema.schema_model import load_schema_from_file, validate_schema, schema_summary, to_json_schema


def test_load_schema_from_file_normalizes_names(tmp_path):
    data = {
        "name": "Employee Records",
        "description": "x",
        "fields": [
            {"name": "EmployeeID", "type": "INT", "unique": True},
            {"name": "Join-Date", "type": "datetime"},
        ],
    }
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    norm = load_schema_from_file(str(p))
    assert norm["name"] == "employee_records"
    assert [f["name"] for f in norm["fields"]] == ["employee_id", "join_date"]


def test_validate_schema_defaults_and_invalid_types():
    # Defaults
    raw = {
        "fields": [
            {"name": "x", "type": "float"},
            {"name": "y", "type": "int"},
            {"name": "z", "type": "string"},
        ]
    }
    norm = validate_schema(raw)
    x = next(f for f in norm["fields"] if f["name"] == "x")
    assert x["nullable"] == 0.0 and x["unique"] is False
    assert x["min"] == 0 and x["max"] == 100

    # Invalid type rejected
    with pytest.raises(ValueError):
        validate_schema({"fields": [{"name": "bad", "type": "weird"}]})


def test_schema_summary_and_json_schema():
    raw = {
        "fields": [
            {"name": "id", "type": "int", "unique": True},
            {"name": "role", "type": "category", "categories": ["a", "b", "c"]},
            {"name": "when", "type": "datetime"},
        ]
    }
    norm = validate_schema(raw)
    s = schema_summary(norm)
    assert s.startswith("3 fields:")
    assert "id(int unique)" in s
    assert "role(category 3)" in s
    assert "when(datetime)" in s

    js = to_json_schema(norm)
    assert js["type"] == "object"
    assert "properties" in js and "id" in js["properties"]


