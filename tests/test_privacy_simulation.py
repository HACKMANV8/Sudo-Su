from __future__ import annotations

import numpy as np
import pandas as pd

from openschema.privacy.simulation import simulate_privacy_risk


def test_privacy_reidentification_drops_with_noise():
    rng = np.random.default_rng(0)
    n = 2000
    ref = pd.DataFrame({
        "age": rng.integers(18, 90, size=n),
        "zip": rng.choice(["10001", "10002", "10003", "10004"], size=n),
    })
    synth = ref.copy()  # worst case: identical structure
    r0 = simulate_privacy_risk(synth, ref, ["age", "zip"], attacker_sample_size=500, noise_level=0.0)
    r1 = simulate_privacy_risk(synth, ref, ["age", "zip"], attacker_sample_size=500, noise_level=0.05)
    assert r0["reidentification_rate"] >= r1["reidentification_rate_after_noise"]

