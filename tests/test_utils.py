from datetime import datetime, timedelta

import numpy as np
from faker import Faker

from openschema.utils import (
    init_seed,
    derive_subseed,
    safe_div,
    percent,
    sample_datetimes_uniform,
    human_readable_bytes,
)


def test_init_seed_determinism_int_and_str():
    # int seed
    rng1 = init_seed(123)
    arr1 = rng1.integers(0, 100, size=5)
    name1 = Faker().name()

    rng2 = init_seed(123)
    arr2 = rng2.integers(0, 100, size=5)
    name2 = Faker().name()

    assert np.array_equal(arr1, arr2)
    assert name1 == name2

    # string seed is stable mapping
    rng3 = init_seed("seed-xyz")
    arr3 = rng3.integers(0, 100, size=5)
    name3 = Faker().name()

    rng4 = init_seed("seed-xyz")
    arr4 = rng4.integers(0, 100, size=5)
    name4 = Faker().name()

    assert np.array_equal(arr3, arr4)
    assert name3 == name4


def test_derive_subseed_and_helpers():
    master = 999
    a = derive_subseed(master, "alpha")
    b = derive_subseed(master, "beta")
    c = derive_subseed(master, "alpha")
    assert isinstance(a, int) and isinstance(b, int)
    assert a != b and a == c

    assert safe_div(1, 0) == 0.0
    assert safe_div(5, 2) == 2.5
    assert percent(1, 0) == 0.0
    assert percent(25, 100) == 25.0


def test_sample_datetimes_and_human_bytes():
    rng = init_seed(7)
    start = datetime(2020, 1, 1)
    end = start + timedelta(days=1)
    values = sample_datetimes_uniform(start, end, 3, rng)
    assert len(values) == 3
    # ISO formatted strings
    assert all(isinstance(v, str) and "T" in v for v in values)

    assert human_readable_bytes(0) == "0 B"
    assert human_readable_bytes(1024) == "1.00 KB"
    assert human_readable_bytes(1024 * 1024) == "1.00 MB"


