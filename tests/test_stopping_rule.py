"""
Stopping-rule enforcement: analyze() must refuse to run on a partial
dataset (fewer sellers per arm than the preregistered sample size), and
must also refuse an over-accrued dataset that doesn't match either, since
both violate the fixed-horizon design in docs/PREREGISTRATION.md section 6.
"""

import numpy as np
import pandas as pd
import pytest

from experiment import analyze  # noqa: E402


def make_experiment_df(n_treatment, n_control, orders_per_seller=5, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for arm, n in [("treatment", n_treatment), ("control", n_control)]:
        for i in range(n):
            seller_id = f"{arm}_{i}"
            for _ in range(orders_per_seller):
                rows.append({
                    "seller_id": seller_id,
                    "category": "cat",
                    "arm": arm,
                    "aov": rng.normal(100, 10),
                    "complaint": rng.binomial(1, 0.1),
                })
    return pd.DataFrame(rows)


def test_analyze_rejects_partial_dataset():
    df = make_experiment_df(n_treatment=50, n_control=50)
    with pytest.raises(analyze.PartialDatasetError):
        analyze.analyze(df, expected_n_per_arm=300)


def test_analyze_rejects_imbalanced_partial_accrual():
    # treatment fully accrued mid-peek, control lagging: still a partial look
    df = make_experiment_df(n_treatment=300, n_control=120)
    with pytest.raises(analyze.PartialDatasetError):
        analyze.analyze(df, expected_n_per_arm=300)


def test_analyze_accepts_fully_realized_dataset():
    df = make_experiment_df(n_treatment=100, n_control=100)
    results = analyze.analyze(df, expected_n_per_arm=100)
    assert "primary" in results
    assert "guardrail" in results



