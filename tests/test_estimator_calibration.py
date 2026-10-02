import json
from pathlib import Path

import numpy as np

from experiment import analyze, randomize, simulate

CALIBRATION = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "calibration" / "calibration_params.json")
    .read_text(encoding="utf-8")
)
N_DRAWS = 100

_cache = {}


def draws():
    if "value" not in _cache:
        population, effects = simulate.simulate_population(
            CALIBRATION, simulate.N_PER_ARM * 2
        )
        realized_aov = effects["realized_aov_lift_seller_level"]
        realized_complaint = effects["realized_complaint_diff_order_level"]
        rows = []
        for seed in range(2000, 2000 + N_DRAWS):
            revealed = randomize.randomize(population, seed=seed)
            primary = analyze._analyze_primary(revealed)
            guardrail = analyze._guardrail_stats(revealed, analyze.GUARDRAIL_MARGIN_ABSOLUTE)
            rows.append((primary, guardrail))
        _cache["value"] = (rows, realized_aov, realized_complaint)
    return _cache["value"]


def test_primary_estimator_is_unbiased_for_the_realized_lift():
    rows, realized_aov, _ = draws()
    estimates = np.array([p["point_estimate_lift"] for p, _ in rows])
    assert abs(estimates.mean() - realized_aov) < 3.0


def test_guardrail_estimator_is_unbiased_for_the_realized_difference():
    rows, _, realized_complaint = draws()
    estimates = np.array([g["point_estimate_diff"] for _, g in rows])
    assert abs(estimates.mean() - realized_complaint) < 0.001


def test_confidence_intervals_cover_the_realized_effects_at_least_nominally():
    rows, realized_aov, realized_complaint = draws()
    primary_cover = np.mean(
        [p["ci_95_low"] <= realized_aov <= p["ci_95_high"] for p, _ in rows]
    )
    guardrail_cover = np.mean(
        [g["ci_95_low"] <= realized_complaint <= g["ci_95_high"] for _, g in rows]
    )
    assert primary_cover >= 0.90
    assert guardrail_cover >= 0.90


def test_decision_outcomes_are_dominated_by_passed_guardrails_when_truth_is_inside_the_margin():
    rows, _, realized_complaint = draws()
    assert realized_complaint < analyze.GUARDRAIL_MARGIN_ABSOLUTE
    statuses = [g["guardrail_status"] for _, g in rows]
    assert np.mean([s == "passed" for s in statuses]) > 0.6
    assert np.mean([s == "breached" for s in statuses]) < 0.05
    go = np.mean([
        g["guardrail_status"] == "passed"
        and p["significant_at_alpha_0.05"]
        and p["point_estimate_lift"] > 0
        and p["lift_meets_mde"]
        for p, g in rows
    ])
    assert 0.45 < go < 0.8
