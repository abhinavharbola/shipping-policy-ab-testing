import json
from pathlib import Path

import numpy as np
import pandas as pd

from design.preregistered import N_PER_ARM

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CALIB_PATH = DATA / "calibration" / "calibration_params.json"
OUT_POPULATION = DATA / "simulated" / "population_potential_outcomes.csv"
OUT_TRUE_EFFECTS = DATA / "simulated" / "true_effects.json"

SIM_SEED = 20260904

TRUE_AOV_LIFT = 28.0
TRUE_COMPLAINT_LIFT_ABS = 0.012

SELLER_COMPLAINT_SHIFT_SD = 0.02
DISPERSION_BRACKET = (0.0, 3.0)
DISPERSION_ITERATIONS = 60


def bootstrap_orders_per_seller(rng, n_sellers, real_distribution):
    real_distribution = np.array(real_distribution)
    return rng.choice(real_distribution, size=n_sellers, replace=True)


def lognormal_from_moments(mean, std, z):
    sigma_ln = np.sqrt(np.log1p((std / mean) ** 2))
    mu_ln = np.log(mean) - sigma_ln ** 2 / 2
    return np.exp(mu_ln + sigma_ln * z)


def seller_means(values, seller_index, n_sellers):
    sums = np.bincount(seller_index, weights=values, minlength=n_sellers)
    counts = np.bincount(seller_index, minlength=n_sellers)
    return sums / counts


def control_seller_parameters(dispersion, base_mean, base_std, z_seller):
    factor = np.exp(dispersion * z_seller - dispersion ** 2 / 2)
    return base_mean * factor, base_std * factor


def achieved_seller_std(dispersion, base_mean, base_std, z_seller, z_order, seller_index):
    mean, std = control_seller_parameters(dispersion, base_mean, base_std, z_seller)
    aov = lognormal_from_moments(mean[seller_index], std[seller_index], z_order)
    means = seller_means(aov, seller_index, len(base_mean))
    return float(np.std(means, ddof=1))


def calibrate_dispersion(target_std, base_mean, base_std, z_seller, z_order, seller_index):
    def achieved(d):
        return achieved_seller_std(d, base_mean, base_std, z_seller, z_order, seller_index)

    low, high = DISPERSION_BRACKET
    if not achieved(low) <= target_std <= achieved(high):
        raise ValueError(
            f"Target seller-level AOV std {target_std} is not reachable within "
            f"dispersion bracket {DISPERSION_BRACKET}: achieved "
            f"{achieved(low):.2f} to {achieved(high):.2f}."
        )
    for _ in range(DISPERSION_ITERATIONS):
        mid = (low + high) / 2
        if achieved(mid) < target_std:
            low = mid
        else:
            high = mid
    dispersion = (low + high) / 2
    return dispersion, achieved(dispersion)


def simulate_population(calibration, n_sellers, seed=SIM_SEED):
    rng = np.random.default_rng(seed)

    categories = calibration["category_names"]
    weights = np.array(
        [calibration["category_weights_seller_level"][c] for c in categories],
        dtype=float,
    )
    weights = weights / weights.sum()
    seller_category = rng.choice(categories, size=n_sellers, p=weights)
    seller_ids = np.array([f"sim_seller_{i:05d}" for i in range(n_sellers)])

    per_category = calibration["per_category"]
    base_mean = np.array([per_category[c]["aov_mean"] for c in seller_category])
    base_std = np.array([per_category[c]["aov_std"] for c in seller_category])
    base_rate = np.array([per_category[c]["complaint_rate"] for c in seller_category])

    z_seller = rng.standard_normal(n_sellers)
    seller_complaint_shift = rng.normal(0, SELLER_COMPLAINT_SHIFT_SD, size=n_sellers)

    orders_per_seller = bootstrap_orders_per_seller(
        rng, n_sellers, calibration["seller_level"]["orders_per_seller_distribution"]
    ).astype(int)
    seller_index = np.repeat(np.arange(n_sellers), orders_per_seller)
    n_orders = len(seller_index)

    z_order_control = rng.standard_normal(n_orders)
    z_order_treatment = rng.standard_normal(n_orders)

    target_std = calibration["seller_level"]["seller_level_aov_std"]
    dispersion, achieved_std = calibrate_dispersion(
        target_std, base_mean, base_std, z_seller, z_order_control, seller_index
    )

    mean_control, std_control = control_seller_parameters(
        dispersion, base_mean, base_std, z_seller
    )
    aov_control = lognormal_from_moments(
        mean_control[seller_index], std_control[seller_index], z_order_control
    )
    aov_treatment = lognormal_from_moments(
        mean_control[seller_index] + TRUE_AOV_LIFT,
        std_control[seller_index],
        z_order_treatment,
    )

    p_control = np.clip(base_rate + seller_complaint_shift, 0.01, 0.6)
    p_treatment = np.clip(p_control + TRUE_COMPLAINT_LIFT_ABS, 0.01, 0.6)
    complaint_control = rng.binomial(1, p_control[seller_index])
    complaint_treatment = rng.binomial(1, p_treatment[seller_index])

    population = pd.DataFrame({
        "seller_id": seller_ids[seller_index],
        "category": seller_category[seller_index],
        "aov_control": aov_control,
        "aov_treatment": aov_treatment,
        "complaint_control": complaint_control.astype(int),
        "complaint_treatment": complaint_treatment.astype(int),
    })

    realized_aov_lift = float(
        np.mean(
            seller_means(aov_treatment, seller_index, n_sellers)
            - seller_means(aov_control, seller_index, n_sellers)
        )
    )
    realized_complaint_diff = float(
        complaint_treatment.mean() - complaint_control.mean()
    )

    true_effects = {
        "seed": seed,
        "n_sellers": int(n_sellers),
        "n_per_arm": int(n_sellers // 2),
        "true_aov_lift_absolute": TRUE_AOV_LIFT,
        "true_complaint_lift_absolute": TRUE_COMPLAINT_LIFT_ABS,
        "realized_aov_lift_seller_level": round(realized_aov_lift, 4),
        "realized_complaint_diff_order_level": round(realized_complaint_diff, 6),
        "seller_aov_std_target": target_std,
        "seller_aov_std_achieved": round(achieved_std, 2),
        "seller_dispersion_sigma": round(dispersion, 4),
        "note": "Ground truth for the recovery check in analyze.py. The true_* fields "
        "are the injected parameters. The realized_* fields are the finite-population "
        "effects actually present in this simulated population, which is what a "
        "confidence interval from one randomized run targets. Kept separate from "
        "randomize.py's output; randomize.py and analyze.py never read this file or "
        "the *_control/*_treatment potential-outcome columns together.",
    }
    return population, true_effects


def main():
    calibration = json.loads(CALIB_PATH.read_text(encoding="utf-8"))
    n_sellers = N_PER_ARM * 2

    population, true_effects = simulate_population(calibration, n_sellers)

    OUT_POPULATION.parent.mkdir(parents=True, exist_ok=True)
    population.to_csv(OUT_POPULATION, index=False)
    with open(OUT_TRUE_EFFECTS, "w", encoding="utf-8") as f:
        json.dump(true_effects, f, indent=2)

    print(f"Simulated {n_sellers} sellers, {len(population)} order-level potential outcomes")
    print(
        f"Seller-level AOV std: target {true_effects['seller_aov_std_target']}, "
        f"achieved {true_effects['seller_aov_std_achieved']}"
    )
    print(f"Wrote {OUT_POPULATION}")
    print(f"Wrote {OUT_TRUE_EFFECTS}")


if __name__ == "__main__":
    main()
