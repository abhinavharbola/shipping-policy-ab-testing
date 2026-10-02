import numpy as np
import pandas as pd
import pytest

from experiment.analyze import _guardrail_stats

MARGIN = 0.02


def build(n_sellers, orders_per_seller, rate_control, rate_treatment, seed=0, clustered=False):
    rng = np.random.default_rng(seed)
    rows = []
    for arm, rate in (("control", rate_control), ("treatment", rate_treatment)):
        for i in range(n_sellers):
            if clustered:
                seller_rate = 1.0 if rng.random() < rate else 0.0
            else:
                seller_rate = rate
            outcomes = rng.binomial(1, seller_rate, size=orders_per_seller)
            for outcome in outcomes:
                rows.append({"seller_id": f"{arm}_{i}", "arm": arm, "complaint": outcome})
    return pd.DataFrame(rows)


def test_clustered_outcomes_inflate_the_standard_error():
    independent = _guardrail_stats(build(400, 20, 0.10, 0.10, clustered=False), MARGIN)
    clustered = _guardrail_stats(build(400, 20, 0.10, 0.10, clustered=True), MARGIN)
    assert clustered["standard_error"] > 3 * independent["standard_error"]


def test_rate_is_order_weighted_not_seller_weighted():
    rows = []
    for i in range(10):
        rows.append({"seller_id": f"c_small_{i}", "arm": "control", "complaint": 1})
    for i in range(10):
        rows.extend({"seller_id": f"c_big_{i}", "arm": "control", "complaint": 0} for _ in range(99))
    for i in range(20):
        rows.extend({"seller_id": f"t_{i}", "arm": "treatment", "complaint": 0} for _ in range(10))
    result = _guardrail_stats(pd.DataFrame(rows), MARGIN)
    assert result["control_complaint_rate"] == pytest.approx(10 / 1000, abs=1e-4)


def test_sub_margin_gap_with_large_sample_is_established():
    df = build(3000, 200, 0.10, 0.105, seed=3)
    result = _guardrail_stats(df, MARGIN)
    assert result["non_inferiority_established"]
    assert result["guardrail_status"] == "passed"
    assert not result["point_estimate_exceeds_margin"]


def test_gap_above_margin_is_breached():
    df = build(300, 20, 0.10, 0.16, seed=4)
    result = _guardrail_stats(df, MARGIN)
    assert result["point_estimate_exceeds_margin"]
    assert result["guardrail_status"] == "breached"
    assert not result["non_inferiority_established"]


def test_sub_margin_but_noisy_gap_is_inconclusive_not_breached():
    df = build(200, 5, 0.10, 0.118, seed=5)
    result = _guardrail_stats(df, MARGIN)
    assert result["point_estimate_diff"] < MARGIN
    assert not result["non_inferiority_established"]
    assert result["guardrail_status"] == "inconclusive"


def test_degenerate_data_raises():
    rows = []
    for arm in ("control", "treatment"):
        for i in range(5):
            rows.extend({"seller_id": f"{arm}_{i}", "arm": arm, "complaint": 0} for _ in range(4))
    with pytest.raises(ValueError, match="degenerate"):
        _guardrail_stats(pd.DataFrame(rows), MARGIN)
