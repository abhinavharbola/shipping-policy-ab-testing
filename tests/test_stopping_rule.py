import inspect

import numpy as np
import pandas as pd
import pytest

from experiment import analyze


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


def test_frozen_sample_size_is_the_default_expectation():
    from design.preregistered import N_PER_ARM

    assert analyze.EXPECTED_N_PER_ARM == N_PER_ARM


def test_analyze_has_no_sample_size_override_parameter():
    assert list(inspect.signature(analyze.analyze).parameters) == ["experiment_df"]


def test_analyze_rejects_a_small_dataset_against_the_frozen_size():
    df = make_experiment_df(n_treatment=50, n_control=50)
    with pytest.raises(analyze.PartialDatasetError):
        analyze.analyze(df)


def test_analyze_rejects_imbalanced_partial_accrual(monkeypatch):
    monkeypatch.setattr(analyze, "EXPECTED_N_PER_ARM", 300)
    df = make_experiment_df(n_treatment=300, n_control=120)
    with pytest.raises(analyze.PartialDatasetError):
        analyze.analyze(df)


def test_analyze_accepts_fully_realized_dataset(monkeypatch):
    monkeypatch.setattr(analyze, "EXPECTED_N_PER_ARM", 100)
    df = make_experiment_df(n_treatment=100, n_control=100)
    results = analyze.analyze(df)
    assert "primary" in results
    assert "guardrail" in results
    assert "lift_meets_mde" in results["primary"]
    assert results["guardrail"]["guardrail_status"] in {"passed", "breached", "inconclusive"}


def test_analyze_rejects_a_seller_present_in_both_arms(monkeypatch):
    monkeypatch.setattr(analyze, "EXPECTED_N_PER_ARM", 100)
    df = make_experiment_df(n_treatment=100, n_control=100)
    df.loc[df["seller_id"] == "control_0", "seller_id"] = "treatment_0"
    df.loc[df["seller_id"] == "control_1", "seller_id"] = "control_0"
    mixed = df.copy()
    mixed.loc[mixed.index[0], "arm"] = "control"
    with pytest.raises(Exception):
        analyze.analyze(mixed)


def test_rerunning_on_identical_data_is_allowed_but_different_data_is_refused(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(analyze, "EXPECTED_N_PER_ARM", 100)
    assigned = tmp_path / "assigned.csv"
    results_path = tmp_path / "analysis_results.json"
    truth = tmp_path / "true_effects.json"
    truth.write_text(
        '{"true_aov_lift_absolute": 0.0, "realized_aov_lift_seller_level": 0.0, '
        '"true_complaint_lift_absolute": 0.0, "realized_complaint_diff_order_level": 0.0}',
        encoding="utf-8",
    )
    monkeypatch.setattr(analyze, "ASSIGNED_PATH", assigned)
    monkeypatch.setattr(analyze, "RESULTS_PATH", results_path)
    monkeypatch.setattr(analyze, "RECOVERY_PATH", tmp_path / "recovery.json")
    monkeypatch.setattr(analyze, "TRUE_EFFECTS_PATH", truth)

    make_experiment_df(100, 100, seed=1).to_csv(assigned, index=False)
    analyze.main()
    analyze.main()
    assert results_path.exists()

    make_experiment_df(100, 100, seed=2).to_csv(assigned, index=False)
    with pytest.raises(analyze.ReanalysisError):
        analyze.main()
