from openschema.schema_model import validate_schema, to_json_schema, schema_summary


def test_name_normalization():
    raw = {
        "name": "Employee Payroll",
        "description": "desc",
        "n_rows": 10,
        "fields": [
            {"name": "EmployeeID", "type": "INT", "unique": True},
            {"name": "Join-Date", "type": "datetime"},
            {"name": "User Role", "type": "category", "categories": ["admin", "user", "guest"]},
        ],
    }
    norm = validate_schema(raw)
    assert norm["name"] == "employee_payroll"
    names = [f["name"] for f in norm["fields"]]
    assert names == ["employee_id", "join_date", "user_role"]


def test_defaults_filling():
    raw = {
        "name": "S",
        "description": "d",
        "n_rows": 100,
        "fields": [
            {"name": "x", "type": "float"},
            {"name": "y", "type": "int"},
            {"name": "z", "type": "string"},
        ],
    }
    norm = validate_schema(raw)
    fx = next(f for f in norm["fields"] if f["name"] == "x")
    assert fx["nullable"] == 0.0
    assert fx["unique"] is False
    assert fx["distribution"] == "uniform"
    assert fx["min"] == 0 and fx["max"] == 100

    fz = next(f for f in norm["fields"] if f["name"] == "z")
    assert fz.get("categories") is None
    assert fz.get("examples") == []
    assert fz.get("class_balance") is None


def test_schema_summary_format():
    raw = {
        "name": "Employee",
        "description": "d",
        "n_rows": 3,
        "fields": [
            {"name": "id", "type": "int", "unique": True},
            {"name": "role", "type": "category", "categories": ["a", "b", "c"]},
            {"name": "churn", "type": "bool", "class_balance": {True: 0.05, False: 0.95}},
        ],
    }
    norm = validate_schema(raw)
    s = schema_summary(norm)
    # basic shape
    assert s.startswith("3 fields:")
    assert "id(int unique)" in s
    assert "role(category 3)" in s
    assert "churn(bool 5%)" in s


def test_json_schema_export():
    raw = {
        "name": "T",
        "description": "d",
        "n_rows": 1,
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "when", "type": "datetime"},
            {"name": "flag", "type": "bool"},
            {"name": "role", "type": "category", "categories": ["a", "b"]},
        ],
    }
    norm = validate_schema(raw)
    js = to_json_schema(norm)
    assert js["type"] == "object"
    assert "properties" in js
    props = js["properties"]
    assert "id" in props and props["id"]["type"] == "integer"
    assert "when" in props and props["when"]["format"] == "date-time"
    assert "flag" in props and props["flag"]["type"] == "boolean"
    assert "role" in props and "enum" in props["role"]


