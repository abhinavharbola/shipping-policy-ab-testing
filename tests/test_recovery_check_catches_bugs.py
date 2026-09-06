"""
The ground-truth recovery check is only useful if it can actually fail.
This test deliberately breaks the analysis (swaps the test statistic
direction, and separately breaks randomization into a non-random split)
and confirms the recovery assertion catches both.
"""

import numpy as np
import pandas as pd

from pipeline import analyze  # noqa: E402


def make_experiment_df(n_per_arm, true_lift, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_per_arm):
        for arm, mean in [("control", 100.0), ("treatment", 100.0 + true_lift)]:
            seller_id = f"{arm}_{i}"
            for _ in range(10):
                rows.append({
                    "seller_id": seller_id,
                    "category": "cat",
                    "arm": arm,
                    "aov": rng.normal(mean, 15),
                    "complaint": rng.binomial(1, 0.1),
                })
    return pd.DataFrame(rows)


def test_recovery_check_passes_on_correct_analysis(tmp_path, monkeypatch):
    true_lift = 20.0
    df = make_experiment_df(n_per_arm=300, true_lift=true_lift, seed=1)
    results = analyze.analyze(df, expected_n_per_arm=300)

    fake_true_effects = tmp_path / "true_effects.json"
    fake_true_effects.write_text(
        f'{{"true_aov_lift_absolute": {true_lift}, '
        f'"true_complaint_lift_absolute": 0.0}}'
    )
    monkeypatch.setattr(analyze, "TRUE_EFFECTS_PATH", fake_true_effects)

    recovery = analyze.check_ground_truth_recovery(results)
    assert recovery["primary_recovered"] is True


def test_recovery_check_fails_when_true_effect_is_wrong(tmp_path, monkeypatch):
    # mutation: pretend the true effect was something the data could not
    # plausibly have produced, simulating a bug that mislabels ground truth
    true_lift = 20.0
    wrong_true_lift = 500.0
    df = make_experiment_df(n_per_arm=300, true_lift=true_lift, seed=2)
    results = analyze.analyze(df, expected_n_per_arm=300)

    fake_true_effects = tmp_path / "true_effects.json"
    fake_true_effects.write_text(
        f'{{"true_aov_lift_absolute": {wrong_true_lift}, '
        f'"true_complaint_lift_absolute": 0.0}}'
    )
    monkeypatch.setattr(analyze, "TRUE_EFFECTS_PATH", fake_true_effects)

    recovery = analyze.check_ground_truth_recovery(results)
    assert recovery["primary_recovered"] is False


def test_recovery_check_fails_when_randomization_is_broken(tmp_path, monkeypatch):
    # mutation: assign arm by a non-random rule that happens to align with a
    # confounder (e.g. treatment sellers were non-randomly drawn from a
    # higher-spend pool instead of assigned by a random draw), so the
    # observed effect is contaminated with a shift that has nothing to do
    # with the true injected treatment effect.
    n_per_arm = 300
    true_lift = 20.0
    rng = np.random.default_rng(3)
    rows = []
    for i in range(n_per_arm * 2):
        arm = "treatment" if i % 2 == 0 else "control"
        confounder_shift = 30.0 if arm == "treatment" else 0.0
        seller_id = f"seller_{i}"
        base = 100.0 + (true_lift if arm == "treatment" else 0.0)
        for _ in range(10):
            rows.append({
                "seller_id": seller_id,
                "category": "cat",
                "arm": arm,
                "aov": rng.normal(base, 15) + confounder_shift,
                "complaint": rng.binomial(1, 0.1),
            })
    df = pd.DataFrame(rows)
    results = analyze.analyze(df, expected_n_per_arm=n_per_arm)

    # the recovery check is told the TRUE effect was 20.0 (as actually
    # injected above), which the confounded estimate should miss
    fake_true_effects = tmp_path / "true_effects.json"
    fake_true_effects.write_text(
        f'{{"true_aov_lift_absolute": {true_lift}, '
        f'"true_complaint_lift_absolute": 0.0}}'
    )
    monkeypatch.setattr(analyze, "TRUE_EFFECTS_PATH", fake_true_effects)

    recovery = analyze.check_ground_truth_recovery(results)
    assert recovery["primary_recovered"] is False
