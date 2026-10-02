import json
from pathlib import Path

import numpy as np

from experiment import simulate

CALIBRATION = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "calibration" / "calibration_params.json")
    .read_text(encoding="utf-8")
)
N_SELLERS = 5006

_cache = {}


def simulated():
    if "value" not in _cache:
        _cache["value"] = simulate.simulate_population(CALIBRATION, N_SELLERS)
    return _cache["value"]


def test_seller_level_aov_std_matches_the_calibration_that_sized_the_study():
    population, _ = simulated()
    seller_means = population.groupby("seller_id")["aov_control"].mean()
    target = CALIBRATION["seller_level"]["seller_level_aov_std"]
    assert abs(seller_means.std(ddof=1) / target - 1) < 0.005


def test_simulated_mean_aov_is_close_to_the_calibrated_category_mix():
    population, _ = simulated()
    seller_means = population.groupby("seller_id")["aov_control"].mean()
    per_category = CALIBRATION["per_category"]
    weights = CALIBRATION["category_weights_seller_level"]
    expected = sum(weights[c] * per_category[c]["aov_mean"] for c in weights)
    assert abs(seller_means.mean() / expected - 1) < 0.08


def test_no_seller_mean_is_clipped_or_nonpositive():
    population, _ = simulated()
    assert (population["aov_control"] > 0).all()
    assert (population["aov_treatment"] > 0).all()


def test_true_effects_record_injected_and_realized_values():
    population, effects = simulated()
    assert effects["true_aov_lift_absolute"] == simulate.TRUE_AOV_LIFT
    direct = population["complaint_treatment"].mean() - population["complaint_control"].mean()
    assert np.isclose(effects["realized_complaint_diff_order_level"], direct, atol=1e-6)
    seller_control = population.groupby("seller_id")["aov_control"].mean()
    seller_treatment = population.groupby("seller_id")["aov_treatment"].mean()
    assert np.isclose(
        effects["realized_aov_lift_seller_level"],
        (seller_treatment - seller_control).mean(),
        atol=1e-3,
    )
    assert abs(effects["realized_aov_lift_seller_level"] - simulate.TRUE_AOV_LIFT) < 20


def test_order_counts_come_from_the_calibrated_distribution():
    population, _ = simulated()
    counts = population.groupby("seller_id").size()
    real = CALIBRATION["seller_level"]["orders_per_seller_distribution"]
    assert counts.min() >= min(real)
    assert counts.max() <= max(real)
    assert abs(counts.median() - np.median(real)) <= 2


def test_control_complaint_rate_is_near_the_calibrated_baseline():
    population, _ = simulated()
    baseline = CALIBRATION["overall"]["complaint_rate"]
    assert abs(population["complaint_control"].mean() - baseline) < 0.02


def test_simulation_is_deterministic_for_a_fixed_seed():
    first, _ = simulate.simulate_population(CALIBRATION, N_SELLERS, seed=11)
    second, _ = simulate.simulate_population(CALIBRATION, N_SELLERS, seed=11)
    assert first.equals(second)
