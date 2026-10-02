import numpy as np
import pandas as pd
import pytest

from experiment.randomize import randomize


def make_fake_population(n_sellers=1000, orders_per_seller=5, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_sellers):
        seller_id = f"seller_{i}"
        for _ in range(orders_per_seller):
            rows.append({
                "seller_id": seller_id,
                "category": "test_cat",
                "aov_control": rng.normal(100, 10),
                "aov_treatment": rng.normal(120, 10),
                "complaint_control": rng.binomial(1, 0.1),
                "complaint_treatment": rng.binomial(1, 0.12),
            })
    return pd.DataFrame(rows)


def treated_sellers(revealed):
    return set(revealed.loc[revealed["arm"] == "treatment", "seller_id"])


def test_split_is_exactly_half_for_every_seed():
    population = make_fake_population(n_sellers=400)
    for seed in range(10):
        revealed = randomize(population, seed)
        assert len(treated_sellers(revealed)) == 200


def test_assignment_depends_on_the_seed_and_not_on_seller_order():
    population = make_fake_population(n_sellers=400)
    first = treated_sellers(randomize(population, 1))
    second = treated_sellers(randomize(population, 2))
    assert first != second
    lowest_half = {f"seller_{i}" for i in range(200)}
    assert first != lowest_half


def test_each_seller_is_treated_about_half_the_time_across_seeds():
    population = make_fake_population(n_sellers=200, orders_per_seller=1)
    n_seeds = 300
    counts = {s: 0 for s in population["seller_id"]}
    for seed in range(n_seeds):
        for s in treated_sellers(randomize(population, seed)):
            counts[s] += 1
    frequencies = np.array(list(counts.values())) / n_seeds
    assert abs(frequencies.mean() - 0.5) < 0.01
    assert np.abs(frequencies - 0.5).max() < 0.15


def test_revealed_dataset_has_no_counterfactual_columns():
    population = make_fake_population(n_sellers=200)
    revealed = randomize(population, seed=5)
    forbidden = {"aov_control", "aov_treatment", "complaint_control", "complaint_treatment"}
    assert forbidden.isdisjoint(set(revealed.columns))


def test_revealed_outcome_matches_the_assigned_arm():
    population = make_fake_population(n_sellers=100, orders_per_seller=2)
    revealed = randomize(population, seed=9)
    merged = revealed.reset_index(drop=True).join(
        population[["aov_control", "aov_treatment"]].reset_index(drop=True)
    )
    treated = merged["arm"] == "treatment"
    assert (merged.loc[treated, "aov"] == merged.loc[treated, "aov_treatment"]).all()
    assert (merged.loc[~treated, "aov"] == merged.loc[~treated, "aov_control"]).all()


def test_category_mix_is_roughly_similar_between_arms():
    rng = np.random.default_rng(3)
    n_sellers = 2000
    categories = rng.choice(["a", "b", "c"], size=n_sellers, p=[0.5, 0.3, 0.2])
    population = pd.DataFrame({
        "seller_id": [f"s_{i}" for i in range(n_sellers)],
        "category": categories,
        "aov_control": 100.0,
        "aov_treatment": 110.0,
        "complaint_control": 0,
        "complaint_treatment": 0,
    })
    revealed = randomize(population, seed=42)
    treat_mix = revealed[revealed["arm"] == "treatment"]["category"].value_counts(normalize=True)
    ctrl_mix = revealed[revealed["arm"] == "control"]["category"].value_counts(normalize=True)
    for cat in ["a", "b", "c"]:
        assert abs(treat_mix[cat] - ctrl_mix[cat]) < 0.05


def test_odd_population_raises_instead_of_silently_unbalancing():
    population = make_fake_population(n_sellers=201)
    with pytest.raises(ValueError, match="odd"):
        randomize(population, seed=1)
