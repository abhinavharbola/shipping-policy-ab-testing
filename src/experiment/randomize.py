from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data"
IN_POPULATION = DATA / "simulated" / "population_potential_outcomes.csv"
OUT_ASSIGNED = DATA / "simulated" / "assigned_experiment.csv"

RANDOMIZATION_SEED = 71

REVEALED_COLUMNS = {"seller_id", "category", "arm", "aov", "complaint"}


def randomize(population, seed=RANDOMIZATION_SEED):
    seller_ids = population["seller_id"].unique()

    if len(seller_ids) % 2 != 0:
        raise ValueError(
            f"Population has {len(seller_ids)} sellers, which is odd; a 1:1 "
            "split requires an even seller count. Check simulate.py's sizing."
        )

    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(seller_ids)

    half = len(shuffled) // 2
    treatment_sellers = set(shuffled[:half])

    population = population.copy()
    population["arm"] = np.where(
        population["seller_id"].isin(treatment_sellers), "treatment", "control"
    )

    revealed_aov = np.where(
        population["arm"] == "treatment",
        population["aov_treatment"],
        population["aov_control"],
    )
    revealed_complaint = np.where(
        population["arm"] == "treatment",
        population["complaint_treatment"],
        population["complaint_control"],
    )

    revealed = pd.DataFrame({
        "seller_id": population["seller_id"],
        "category": population["category"],
        "arm": population["arm"],
        "aov": revealed_aov,
        "complaint": revealed_complaint,
    })

    if set(revealed.columns) != REVEALED_COLUMNS:
        raise RuntimeError(
            f"Revealed frame has unexpected columns {sorted(revealed.columns)}; "
            "a counterfactual column may have leaked."
        )

    return revealed


def main():
    population = pd.read_csv(IN_POPULATION)
    revealed = randomize(population, seed=RANDOMIZATION_SEED)

    OUT_ASSIGNED.parent.mkdir(parents=True, exist_ok=True)
    revealed.to_csv(OUT_ASSIGNED, index=False)

    n_treatment_sellers = revealed[revealed["arm"] == "treatment"]["seller_id"].nunique()
    n_control_sellers = revealed[revealed["arm"] == "control"]["seller_id"].nunique()

    print(f"Wrote {OUT_ASSIGNED}")
    print(f"Sellers: {n_treatment_sellers} treatment, {n_control_sellers} control")
    print(f"Orders: {len(revealed)}")


if __name__ == "__main__":
    main()
