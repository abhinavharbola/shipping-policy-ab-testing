import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from experiment import analyze
from experiment import randomize as randomize_module

N_SELLERS = 300
ORDERS_PER_SELLER = 10
LIFT = 20.0


def make_population(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(N_SELLERS):
        shift = 40.0 * i / N_SELLERS
        for _ in range(ORDERS_PER_SELLER):
            aov_control = 100.0 + shift + rng.normal(0, 10)
            complaint = int(rng.binomial(1, 0.1))
            rows.append({
                "seller_id": f"seller_{i:04d}",
                "category": "cat",
                "aov_control": aov_control,
                "aov_treatment": aov_control + LIFT,
                "complaint_control": complaint,
                "complaint_treatment": complaint,
            })
    return pd.DataFrame(rows)


def write_truth(path, population):
    seller_control = population.groupby("seller_id")["aov_control"].mean()
    seller_treatment = population.groupby("seller_id")["aov_treatment"].mean()
    truth = {
        "true_aov_lift_absolute": LIFT,
        "realized_aov_lift_seller_level": float((seller_treatment - seller_control).mean()),
        "true_complaint_lift_absolute": 0.0,
        "realized_complaint_diff_order_level": float(
            population["complaint_treatment"].mean() - population["complaint_control"].mean()
        ),
    }
    path.write_text(json.dumps(truth), encoding="utf-8")


class SortedRng:
    def permutation(self, values):
        return np.array(values)


def run(population, tmp_path, monkeypatch):
    truth_path = tmp_path / "true_effects.json"
    write_truth(truth_path, population)
    monkeypatch.setattr(analyze, "TRUE_EFFECTS_PATH", truth_path)
    monkeypatch.setattr(analyze, "EXPECTED_N_PER_ARM", N_SELLERS // 2)


def test_correct_randomization_recovers_the_truth_for_most_seeds(tmp_path, monkeypatch):
    population = make_population()
    run(population, tmp_path, monkeypatch)
    recovered = 0
    n_seeds = 20
    for seed in range(n_seeds):
        revealed = randomize_module.randomize(population, seed=seed)
        results = analyze.analyze(revealed)
        if analyze.check_ground_truth_recovery(results)["primary_recovered"]:
            recovered += 1
    assert recovered >= 16


def test_non_random_assignment_through_the_real_randomize_is_caught(tmp_path, monkeypatch):
    population = make_population()
    run(population, tmp_path, monkeypatch)
    fake_np = SimpleNamespace(
        random=SimpleNamespace(default_rng=lambda seed: SortedRng()),
        where=np.where,
    )
    monkeypatch.setattr(randomize_module, "np", fake_np)
    revealed = randomize_module.randomize(population, seed=1)
    results = analyze.analyze(revealed)
    recovery = analyze.check_ground_truth_recovery(results)
    assert not recovery["primary_recovered"]
    assert not recovery["both_recovered"]


def test_recovery_is_judged_against_the_realized_effect_not_only_the_parameter(
    tmp_path, monkeypatch
):
    population = make_population()
    run(population, tmp_path, monkeypatch)
    truth_path = tmp_path / "true_effects.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["realized_aov_lift_seller_level"] = 500.0
    truth_path.write_text(json.dumps(truth), encoding="utf-8")

    revealed = randomize_module.randomize(population, seed=3)
    recovery = analyze.check_ground_truth_recovery(analyze.analyze(revealed))
    assert not recovery["primary_recovered"]
    assert recovery["injected_aov_lift"] == LIFT
