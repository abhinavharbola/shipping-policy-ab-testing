"""
Step 4: simulate the seller population.

Uses a potential-outcomes design: every simulated order gets BOTH a
control-condition AOV/complaint and a treatment-condition AOV/complaint,
calibrated from real Olist descriptive stats with a known effect added
to the treatment side. randomize.py then assigns each seller to one arm
and reveals only that arm's outcomes, discarding the counterfactual
columns entirely, the same way a real experiment can only ever observe
one potential outcome per unit. analyze.py never has access to this
file or to true_effects.json; it only ever sees randomize.py's output.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_DATA = Path(__file__).resolve().parents[1] / "data"
CALIB_PATH = SRC_DATA / "calibration" / "calibration_params.json"
POWER_PATH = ROOT / "results" / "power_analysis.json"
OUT_POPULATION = SRC_DATA / "simulated" / "population_potential_outcomes.csv"
OUT_TRUE_EFFECTS = SRC_DATA / "simulated" / "true_effects.json"

SIM_SEED = 20260904

# True injected effects, set slightly past the preregistered MDE: a real effect
# a team ships is usually a bit past the threshold that made the trial worth
# running in the first place. The guardrail effect is deliberately not clean.
TRUE_AOV_LIFT = 28.0             # BRL, absolute increase in mean order value
TRUE_COMPLAINT_LIFT_ABS = 0.012  # +1.2 percentage points: real but sub-margin degradation


def bootstrap_orders_per_seller(rng, n_sellers, real_distribution):
    """
    Sample simulated sellers' order counts by resampling (with replacement)
    from the real per-seller order-count distribution in the calibration
    data. Olist's real distribution is heavily right-skewed (median far
    below the mean, long tail of high-volume sellers) in a way a single
    negative-binomial parameter cannot reproduce while matching both the
    median and a high quantile at once; bootstrapping the empirical shape
    sidesteps that and is honestly what "calibrated from real data" should
    mean here.
    """
    real_distribution = np.array(real_distribution)
    return rng.choice(real_distribution, size=n_sellers, replace=True)


def main():
    calibration = json.load(open(CALIB_PATH))
    power = json.load(open(POWER_PATH))

    n_per_arm = power["required_n_per_arm"]
    n_sellers = n_per_arm * 2

    rng = np.random.default_rng(SIM_SEED)

    categories = calibration["category_names"]
    cat_weights = np.array([calibration["category_weights"][c] for c in categories])
    cat_weights = cat_weights / cat_weights.sum()
    seller_category = rng.choice(categories, size=n_sellers, p=cat_weights)
    seller_ids = np.array([f"sim_seller_{i:05d}" for i in range(n_sellers)])

    base_aov_mean = np.array(
        [calibration["per_category"][c]["aov_mean"] for c in seller_category]
    )
    base_aov_std = np.array(
        [calibration["per_category"][c]["aov_std"] for c in seller_category]
    )
    base_complaint_rate = np.array(
        [calibration["per_category"][c]["complaint_rate"] for c in seller_category]
    )

    seller_level_std = calibration["seller_level"]["seller_level_aov_std"]
    seller_noise_scale = seller_level_std * 0.35
    seller_aov_shift = rng.normal(0, seller_noise_scale, size=n_sellers)
    seller_complaint_shift = rng.normal(0, 0.02, size=n_sellers)

    orders_per_seller = bootstrap_orders_per_seller(
        rng, n_sellers, calibration["seller_level"]["orders_per_seller_distribution"]
    )

    records = []
    for i in range(n_sellers):
        n_orders = int(orders_per_seller[i])
        mu_control = max(base_aov_mean[i] + seller_aov_shift[i], 5.0)
        mu_treatment = mu_control + TRUE_AOV_LIFT
        sigma = max(base_aov_std[i], 5.0)

        sigma_ln_c = np.sqrt(np.log(1 + (sigma / mu_control) ** 2))
        mu_ln_c = np.log(mu_control) - sigma_ln_c ** 2 / 2
        aov_control = rng.lognormal(mu_ln_c, sigma_ln_c, size=n_orders)

        sigma_ln_t = np.sqrt(np.log(1 + (sigma / mu_treatment) ** 2))
        mu_ln_t = np.log(mu_treatment) - sigma_ln_t ** 2 / 2
        aov_treatment = rng.lognormal(mu_ln_t, sigma_ln_t, size=n_orders)

        p_control = np.clip(base_complaint_rate[i] + seller_complaint_shift[i], 0.01, 0.6)
        p_treatment = np.clip(p_control + TRUE_COMPLAINT_LIFT_ABS, 0.01, 0.6)
        complaint_control = rng.binomial(1, p_control, size=n_orders)
        complaint_treatment = rng.binomial(1, p_treatment, size=n_orders)

        for j in range(n_orders):
            records.append((
                seller_ids[i], seller_category[i],
                aov_control[j], aov_treatment[j],
                int(complaint_control[j]), int(complaint_treatment[j]),
            ))

    columns = [
        "seller_id", "category",
        "aov_control", "aov_treatment",
        "complaint_control", "complaint_treatment",
    ]
    population = pd.DataFrame(records, columns=columns)

    OUT_POPULATION.parent.mkdir(parents=True, exist_ok=True)
    population.to_csv(OUT_POPULATION, index=False)

    true_effects = {
        "seed": SIM_SEED,
        "n_sellers": int(n_sellers),
        "n_per_arm": int(n_per_arm),
        "true_aov_lift_absolute": TRUE_AOV_LIFT,
        "true_complaint_lift_absolute": TRUE_COMPLAINT_LIFT_ABS,
        "note": "Ground truth for the recovery check in analyze.py. Kept separate "
        "from randomize.py's output; randomize.py and analyze.py never read this "
        "file or the *_control/*_treatment potential-outcome columns together.",
    }
    with open(OUT_TRUE_EFFECTS, "w") as f:
        json.dump(true_effects, f, indent=2)

    print(f"Simulated {n_sellers} sellers, {len(population)} order-level potential outcomes")
    print(f"Wrote {OUT_POPULATION}")
    print(f"Wrote {OUT_TRUE_EFFECTS}")


if __name__ == "__main__":
    main()
