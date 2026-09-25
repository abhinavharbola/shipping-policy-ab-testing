"""
Regression tests for the guardrail-test fix (docs/PREREGISTRATION.md
section 8 amendment).

The guardrail test used to pool order-level complaint counts within each
arm, which treats orders from the same seller as independent and
understates the true standard error, and tested against a zero-difference
null rather than the preregistered margin itself. These tests pin the
fixed behavior directly: the guardrail's unit of analysis is the seller,
matching the primary metric and the randomization unit, and the breach
decision is driven by a proper margin-shifted null, not a from-zero
p-value combined with a separate point-estimate check.
"""

import numpy as np
import pandas as pd
import pytest

from experiment import analyze


def make_experiment_df(n_per_arm, orders_per_seller, seller_complaint_rates, seed=0):
    """
    Builds a synthetic experiment dataset where each seller's TRUE
    complaint rate is known and fixed (no sampling noise within a seller),
    so the seller-level point estimate is exactly predictable, and any
    order-level analysis that (incorrectly) weights by order count instead
    of by seller can be shown to diverge from it.
    """
    rows = []
    for arm in ("treatment", "control"):
        for i in range(n_per_arm):
            seller_id = f"{arm}_{i}"
            rate = seller_complaint_rates[arm][i]
            n_orders = orders_per_seller[arm][i]
            n_complaints = round(rate * n_orders)
            complaints = [1] * n_complaints + [0] * (n_orders - n_complaints)
            for c in complaints:
                rows.append({
                    "seller_id": seller_id,
                    "category": "cat",
                    "arm": arm,
                    "aov": 100.0,
                    "complaint": c,
                })
    return pd.DataFrame(rows)


def test_guardrail_unit_of_analysis_is_the_seller_not_the_order():
    """
    Construct a population where a few high-volume sellers have a LOW
    complaint rate and many low-volume sellers have a HIGH complaint rate
    in the treatment arm, control held at a uniform rate. An order-level
    (order-weighted) analysis is dominated by the high-volume sellers and
    would report a small gap; a seller-level (seller-weighted) analysis
    treats every seller equally and reports the true, larger gap.
    """
    n_per_arm = 200
    rng = np.random.default_rng(0)

    # control: everyone at 10%, uniform order counts
    control_rates = {i: 0.10 for i in range(n_per_arm)}
    control_orders = {i: 20 for i in range(n_per_arm)}

    # treatment: 10 high-volume sellers at 10% (no change), 190 low-volume
    # sellers at 40% (a real, large per-seller increase)
    treatment_rates = {}
    treatment_orders = {}
    for i in range(n_per_arm):
        if i < 10:
            treatment_rates[i] = 0.10
            treatment_orders[i] = 500  # high volume, unchanged rate
        else:
            treatment_rates[i] = 0.40
            treatment_orders[i] = 5    # low volume, sharply worse rate

    df = make_experiment_df(
        n_per_arm,
        {"treatment": treatment_orders, "control": control_orders},
        {"treatment": treatment_rates, "control": control_rates},
    )

    results = analyze._analyze_guardrail(df)

    # Order-weighted pooling would be dominated by the 10 high-volume,
    # unchanged-rate sellers (10 * 500 = 5000 orders) over the 190
    # low-volume, sharply-worse sellers (190 * 5 = 950 orders), and would
    # report a gap well under 10 points. The seller-level estimate must
    # instead reflect that 190 of 200 treatment sellers got much worse.
    assert results["point_estimate_diff"] > 0.20, (
        "guardrail point estimate looks order-weighted, not seller-weighted; "
        f"got {results['point_estimate_diff']}"
    )
    assert results["unit_for_test"].startswith("seller")
    assert "n_treatment_sellers" in results
    assert results["n_treatment_sellers"] == n_per_arm


def test_guardrail_tests_the_margin_directly_not_just_zero():
    """
    A gap that is clearly, significantly different from zero but still
    comfortably under the preregistered margin must NOT be flagged as a
    breach. The old from-zero test alone would have flagged this (a large
    sample makes almost any nonzero gap "significant" against zero); only
    a margin-shifted test correctly clears it.
    """
    n_per_arm = 3000
    control_rates = {i: 0.10 for i in range(n_per_arm)}
    control_orders = {i: 200 for i in range(n_per_arm)}
    # every seller's rate moves up by a small, uniform 0.5pp: real, precisely
    # estimable, and clearly nonzero at this sample size, but far under the
    # preregistered 2.0pp margin. 200 orders/seller keeps both rates exact
    # integer complaint counts (20 and 21) so no rounding noise creeps in.
    treatment_rates = {i: 0.105 for i in range(n_per_arm)}
    treatment_orders = {i: 200 for i in range(n_per_arm)}

    df = make_experiment_df(
        n_per_arm,
        {"treatment": treatment_orders, "control": control_orders},
        {"treatment": treatment_rates, "control": control_rates},
    )

    # _guardrail_stats takes the margin directly, no file I/O, so this test
    # exercises the actual test logic without touching results/power_analysis.json.
    results = analyze._guardrail_stats(df, margin=0.02)
    assert results["point_estimate_diff"] == pytest.approx(0.005, abs=1e-6)
    assert results["guardrail_breached"] is False
    assert results["non_inferiority_established"] is True


def test_old_from_zero_logic_would_have_wrongly_flagged_the_same_data():
    """
    Sanity check that the fixed test is doing real work, not just relabeling
    the old one: replay the same small-but-real 0.5pp shift through the
    OLD from-zero, order-pooled logic and confirm it is significant against
    zero, where the new margin-shifted test correctly finds non-inferiority.
    This pins the actual behavioral difference, not just the new function's
    output in isolation.
    """
    n_per_arm = 3000
    control_rates = {i: 0.10 for i in range(n_per_arm)}
    control_orders = {i: 200 for i in range(n_per_arm)}
    treatment_rates = {i: 0.105 for i in range(n_per_arm)}
    treatment_orders = {i: 200 for i in range(n_per_arm)}

    df = make_experiment_df(
        n_per_arm,
        {"treatment": treatment_orders, "control": control_orders},
        {"treatment": treatment_rates, "control": control_rates},
    )

    treatment = df[df["arm"] == "treatment"]
    control = df[df["arm"] == "control"]
    count = np.array([treatment["complaint"].sum(), control["complaint"].sum()])
    nobs = np.array([len(treatment), len(control)])
    p_t, p_c = count[0] / nobs[0], count[1] / nobs[1]
    se = np.sqrt(p_t * (1 - p_t) / nobs[0] + p_c * (1 - p_c) / nobs[1])
    from scipy import stats as _stats
    z = (p_t - p_c) / se
    p_value_from_zero = 1 - _stats.norm.cdf(z)

    # The old from-zero test is significant here (large order count makes
    # even a tiny, sub-margin gap "significant" against zero), which is
    # exactly the framing problem the fix addresses: significance against
    # zero says nothing about whether the margin was crossed.
    assert p_value_from_zero < 0.05
