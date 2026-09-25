"""
Power calculation correctness against a known textbook example, plus
sanity checks on the calibrated MDE calculation itself.
"""

import pytest
from statsmodels.stats.power import TTestIndPower

from design import power_analysis as mde_calculator


def test_ttest_power_matches_textbook_example():
    # Cohen (1988) canonical example: d=0.5 (medium effect), alpha=0.05,
    # power=0.8, two-sided, equal n -> n per group approx 64 (63.77).
    analysis = TTestIndPower()
    n = analysis.solve_power(effect_size=0.5, alpha=0.05, power=0.8, ratio=1.0)
    assert 63 <= n <= 65


def test_primary_power_uses_calibration_only():
    calibration = {
        "seller_level": {"seller_level_aov_std": 100.0},
    }
    result = mde_calculator.primary_power(calibration)
    assert result["cohens_d"] == pytest.approx(25.0 / 100.0, rel=1e-6)
    assert result["required_n_per_arm_sellers"] > 0


def test_guardrail_power_uses_calibration_only():
    calibration = {
        "overall": {"complaint_rate": 0.10},
        "seller_level": {"orders_per_seller_mean": 10.0},
    }
    result = mde_calculator.guardrail_power(calibration)
    assert result["worst_tolerable_complaint_rate"] == pytest.approx(0.12)
    assert result["required_n_per_arm_orders"] > 0
    assert result["required_n_per_arm_sellers_equivalent"] > 0


def test_higher_baseline_variance_requires_more_sellers():
    calibration_low_std = {"seller_level": {"seller_level_aov_std": 100.0}}
    calibration_high_std = {"seller_level": {"seller_level_aov_std": 400.0}}
    low = mde_calculator.primary_power(calibration_low_std)
    high = mde_calculator.primary_power(calibration_high_std)
    # more baseline noise -> more sellers needed to detect the same MDE
    assert high["required_n_per_arm_sellers"] > low["required_n_per_arm_sellers"]
