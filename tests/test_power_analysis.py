import json
import re
from pathlib import Path

import pytest
from statsmodels.stats.power import TTestIndPower

from design import power_analysis as mde_calculator
from design import preregistered

ROOT = Path(__file__).resolve().parent.parent
CALIBRATION = ROOT / "data" / "calibration" / "calibration_params.json"
COMMITTED_POWER = ROOT / "results" / "power_analysis.json"
PREREG = ROOT / "docs" / "PREREGISTRATION.md"


def test_ttest_power_matches_textbook_example():
    analysis = TTestIndPower()
    n = analysis.solve_power(effect_size=0.5, alpha=0.05, power=0.8, ratio=1.0)
    assert 63 <= n <= 65


def test_primary_power_uses_calibration_only():
    calibration = {"seller_level": {"seller_level_aov_std": 100.0}}
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
    low = mde_calculator.primary_power({"seller_level": {"seller_level_aov_std": 100.0}})
    high = mde_calculator.primary_power({"seller_level": {"seller_level_aov_std": 400.0}})
    assert high["required_n_per_arm_sellers"] > low["required_n_per_arm_sellers"]


def test_committed_calibration_reproduces_the_frozen_sample_size():
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    primary = mde_calculator.primary_power(calibration)
    guardrail = mde_calculator.guardrail_power(calibration)
    binding = max(
        primary["required_n_per_arm_sellers"],
        guardrail["required_n_per_arm_sellers_equivalent"],
    )
    assert binding == preregistered.N_PER_ARM


def test_committed_power_results_match_the_frozen_sample_size():
    committed = json.loads(COMMITTED_POWER.read_text(encoding="utf-8"))
    assert committed["required_n_per_arm"] == preregistered.N_PER_ARM
    assert committed["required_total_sellers"] == 2 * preregistered.N_PER_ARM


def test_preregistration_document_states_the_frozen_constants():
    text = PREREG.read_text(encoding="utf-8")
    assert f"{preregistered.N_PER_ARM:,}" in text
    assert f"BRL {preregistered.AOV_MDE_ABSOLUTE:.2f}" in text
    assert f"{preregistered.GUARDRAIL_MARGIN_ABSOLUTE * 100:.1f} percentage points" in text
    assert re.search(r"alpha\s*=\s*0\.05", text)


def test_changed_calibration_raises_design_drift(tmp_path, monkeypatch):
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    calibration["seller_level"]["seller_level_aov_std"] = 200.0
    altered = tmp_path / "calibration_params.json"
    altered.write_text(json.dumps(calibration), encoding="utf-8")
    out = tmp_path / "power_analysis.json"

    monkeypatch.setattr(mde_calculator, "CALIB_PATH", altered)
    monkeypatch.setattr(mde_calculator, "OUT_PATH", out)
    with pytest.raises(mde_calculator.DesignDriftError):
        mde_calculator.main()
    assert not out.exists()
