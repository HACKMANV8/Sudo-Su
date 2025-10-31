import pandas as pd
import numpy as np

from openschema.generator import generate_from_schema
from openschema.pipeline import run_pipeline_from_schema


SCHEMA = {
    "n_rows": 0,
    "fields": [
        {"name": "id", "type": "string", "format": "uuid", "unique": True},
        {"name": "role", "type": "category", "categories": ["engineer", "manager"]},
        {"name": "salary", "type": "int"},
    ],
}


def test_append_mode(tmp_path):
    df = pd.DataFrame({
        "id": [f"x{i}" for i in range(5)],
        "role": ["engineer", "manager", "engineer", "engineer", "manager"],
        "salary": [70000, 90000, 71000, 69000, 88000],
    })
    src = tmp_path / "in.csv"
    df.to_csv(src, index=False)

    out_df, rep = generate_from_schema(SCHEMA, seed="s", source_csv=str(src), mode="append", target_rows=10)
    assert len(out_df) == 10
    assert out_df["id"].nunique() == 10


def test_augment_mode_means_preserved(tmp_path):
    df = pd.DataFrame({
        "id": [f"y{i}" for i in range(20)],
        "role": ["engineer"] * 10 + ["manager"] * 10,
        "salary": [70000] * 10 + [90000] * 10,
    })
    src = tmp_path / "in.csv"
    df.to_csv(src, index=False)
    out_df, rep = generate_from_schema(SCHEMA, seed=7, source_csv=str(src), mode="augment", additional_rows=20)
    means = out_df.groupby("role")["salary"].mean()
    assert means["manager"] - means["engineer"] > 10000 * 0.5


def test_reproducibility_with_csv(tmp_path):
    df = pd.DataFrame({
        "id": [f"z{i}" for i in range(3)],
        "role": ["engineer", "manager", "engineer"],
        "salary": [70000, 90000, 71000],
    })
    src = tmp_path / "in.csv"
    df.to_csv(src, index=False)
    df1, r1 = generate_from_schema(SCHEMA, seed=123, source_csv=str(src), mode="augment", additional_rows=5)
    df2, r2 = generate_from_schema(SCHEMA, seed=123, source_csv=str(src), mode="augment", additional_rows=5)
    assert df1.equals(df2)
    assert r1["source_csv_hash"] == r2["source_csv_hash"]


