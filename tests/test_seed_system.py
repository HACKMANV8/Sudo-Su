import hashlib
from io import StringIO

import numpy as np

from openschema.utils import normalize_seed, derive_subseed
from openschema.generator import generate_from_schema


def df_md5(df) -> str:
    buf = StringIO()
    df.to_csv(buf, index=False)
    return hashlib.md5(buf.getvalue().encode("utf-8")).hexdigest()


def test_string_seed_normalization_and_reproducibility():
    s = "user-seed-xyz"
    n1 = normalize_seed(s)
    n2 = normalize_seed(s)
    assert isinstance(n1, int) and n1 == n2

    schema = {
        "n_rows": 500,
        "fields": [
            {"name": "id", "type": "string", "format": "uuid", "unique": True},
            {"name": "role", "type": "category", "categories": ["engineer", "manager", "hr"]},
            {"name": "salary", "type": "int"},
        ],
    }
    df1, r1 = generate_from_schema(schema, seed=s)
    df2, r2 = generate_from_schema(schema, seed=s)
    assert df_md5(df1) == df_md5(df2)
    assert r1["normalized_seed"] == r2["normalized_seed"] == n1
    assert r1["fingerprint"] == r2["fingerprint"]


def test_different_seeds_produce_different_outputs():
    schema = {
        "n_rows": 300,
        "fields": [
            {"name": "id", "type": "string", "format": "uuid", "unique": True},
            {"name": "x", "type": "float"},
        ],
    }
    df1, _ = generate_from_schema(schema, seed="A")
    df2, _ = generate_from_schema(schema, seed="B")
    assert df_md5(df1) != df_md5(df2)


def test_subseed_stability():
    m = 12345
    a = derive_subseed(m, "alpha")
    b = derive_subseed(m, "beta")
    c = derive_subseed(m, "alpha")
    assert a != b and a == c


