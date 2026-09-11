"""
Step 5: randomize.

Performs the simple random assignment specified in PREREGISTRATION.md
section 5 (not stratified, 1:1 by seller). Reveals exactly one potential
outcome per seller and writes ONLY that revealed value; the counterfactual
columns from simulate.py are dropped here and never written to
the output analyze.py reads. This is what makes "the analysis code must
not be able to see or influence the values already committed" true by
construction, not by convention: the file analyze.py loads physically
does not contain the other arm's outcome or the true effect size.

Seed is an implementation detail (see PREREGISTRATION.md section 5), not
a design decision: it is fixed here for reproducibility of this specific
run, not chosen to produce a favorable split.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data"
IN_POPULATION = DATA / "simulated" / "population_potential_outcomes.csv"
OUT_ASSIGNED = DATA / "simulated" / "assigned_experiment.csv"

RANDOMIZATION_SEED = 71  # implementation detail; not tuned


def main():
    population = pd.read_csv(IN_POPULATION)

    seller_ids = population["seller_id"].unique()
    rng = np.random.default_rng(RANDOMIZATION_SEED)
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

    # Sanity: confirm no counterfactual column survived into the revealed frame.
    assert set(revealed.columns) == {"seller_id", "category", "arm", "aov", "complaint"}

    OUT_ASSIGNED.parent.mkdir(parents=True, exist_ok=True)
    revealed.to_csv(OUT_ASSIGNED, index=False)

    n_treatment_sellers = revealed[revealed["arm"] == "treatment"]["seller_id"].nunique()
    n_control_sellers = revealed[revealed["arm"] == "control"]["seller_id"].nunique()

    print(f"Wrote {OUT_ASSIGNED}")
    print(f"Sellers: {n_treatment_sellers} treatment, {n_control_sellers} control")
    print(f"Orders: {len(revealed)}")


if __name__ == "__main__":
    main()
