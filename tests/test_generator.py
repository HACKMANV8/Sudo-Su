import hashlib
from io import StringIO

import numpy as np
import pandas as pd

from openschema.generator import generate_from_schema


def df_md5(df: pd.DataFrame) -> str:
    buf = StringIO()
    df.to_csv(buf, index=False)
    return hashlib.md5(buf.getvalue().encode("utf-8")).hexdigest()


def test_deterministic_generation_md5():
    schema = {
        "n_rows": 1000,
        "fields": [
            {"name": "id", "type": "string", "format": "uuid", "unique": True},
            {"name": "role", "type": "category", "categories": ["engineer", "manager", "hr"]},
            {"name": "salary", "type": "int", "distribution": "normal"},
            {"name": "when", "type": "datetime"},
            {"name": "label", "type": "bool", "class_balance": {"1": 0.3, "0": 0.7}},
        ],
    }
    df1, r1 = generate_from_schema(schema, seed=123)
    df2, r2 = generate_from_schema(schema, seed=123)
    assert df_md5(df1) == df_md5(df2)


def test_role_salary_mapping_means_differ():
    schema = {
        "n_rows": 5000,
        "fields": [
            {"name": "role", "type": "category", "categories": ["engineer", "manager"]},
            {"name": "salary", "type": "int"},
        ],
    }
    df, _ = generate_from_schema(schema, seed=7)
    means = df.groupby("role")["salary"].mean()
    assert abs(means["manager"] - means["engineer"]) / means["engineer"] > 0.1


def test_class_balance_exact_counts():
    schema = {
        "n_rows": 1000,
        "class_balance": {"1": 0.37, "0": 0.63},
        "fields": [
            {"name": "label", "type": "bool"},
        ],
    }
    df, _ = generate_from_schema(schema, seed=11)
    counts = df["label"].value_counts().to_dict()
    assert counts.get(1, 0) == 370
    assert counts.get(0, 0) == 630


def test_uniqueness_enforced():
    schema = {
        "n_rows": 1000,
        "fields": [
            {"name": "code", "type": "string", "unique": True},
        ],
    }
    df, rep = generate_from_schema(schema, seed=999)
    assert df["code"].nunique() == len(df)


