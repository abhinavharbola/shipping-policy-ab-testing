"""
Randomization produces balanced arms within expected variance, and never
leaks a counterfactual outcome column into the revealed dataset.
"""

import numpy as np
import pandas as pd


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


def randomize_inline(population, seed):
    seller_ids = population["seller_id"].unique()
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(seller_ids)
    half = len(shuffled) // 2
    treatment_sellers = set(shuffled[:half])
    population = population.copy()
    population["arm"] = np.where(
        population["seller_id"].isin(treatment_sellers), "treatment", "control"
    )
    revealed_aov = np.where(
        population["arm"] == "treatment", population["aov_treatment"], population["aov_control"]
    )
    revealed_complaint = np.where(
        population["arm"] == "treatment",
        population["complaint_treatment"],
        population["complaint_control"],
    )
    return pd.DataFrame({
        "seller_id": population["seller_id"],
        "category": population["category"],
        "arm": population["arm"],
        "aov": revealed_aov,
        "complaint": revealed_complaint,
    })


def test_arms_are_balanced_across_repeated_seeds():
    population = make_fake_population()
    n_sellers = population["seller_id"].nunique()
    imbalances = []
    for seed in range(20):
        revealed = randomize_inline(population, seed)
        n_treatment = revealed.loc[revealed["arm"] == "treatment", "seller_id"].nunique()
        imbalances.append(abs(n_treatment - n_sellers / 2))
    # exact 50/50 split by construction (even n_sellers, integer //2)
    assert max(imbalances) == 0


def test_revealed_dataset_has_no_counterfactual_columns():
    population = make_fake_population(n_sellers=200)
    revealed = randomize_inline(population, seed=5)
    forbidden = {"aov_control", "aov_treatment", "complaint_control", "complaint_treatment"}
    assert forbidden.isdisjoint(set(revealed.columns))


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
    revealed = randomize_inline(population, seed=42)
    treat_mix = revealed[revealed["arm"] == "treatment"]["category"].value_counts(normalize=True)
    ctrl_mix = revealed[revealed["arm"] == "control"]["category"].value_counts(normalize=True)
    for cat in ["a", "b", "c"]:
        assert abs(treat_mix[cat] - ctrl_mix[cat]) < 0.05
