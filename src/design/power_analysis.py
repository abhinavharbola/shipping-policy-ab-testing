"""
Step 2: Power analysis and minimum detectable effect.

Reads ONLY data/calibration/calibration_params.json (real-data-derived
baseline mean/variance/rate). It must never read simulated data, because
that data does not exist yet at this point in the project. Output is
written to results/power_analysis.json, and docs/PREREGISTRATION.md quotes
these numbers directly.

Unit of analysis for both tests is the seller, matching the unit of
randomization (see docs/PREREGISTRATION.md for the SUTVA argument). The
primary metric test is a Welch's t-test on each seller's mean AOV; the
guardrail is planned as a proportions test, so its required N is
computed in orders and then converted into an equivalent seller count
using the observed orders-per-seller rate, so the two constraints can be
compared on the same unit.
"""

import json
import math
from pathlib import Path

from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CALIB_PATH = DATA / "calibration" / "calibration_params.json"
OUT_PATH = ROOT / "results" / "power_analysis.json"

ALPHA = 0.05
POWER_TARGET = 0.80

# --- MDE choices, justified in prose below and quoted verbatim in docs/PREREGISTRATION.md ---

# Primary metric MDE: the mean freight value absorbed per order in the calibration
# data is ~R$23. A shipping-policy change that does not lift average order value by
# at least that much cannot be covering its own direct cost, before even accounting
# for margin. We set the MDE a little above the direct-cost break-even point rather
# than exactly at it, so the trial isn't powered to detect a lift that would be a
# wash on paper. Anything smaller than this is not worth acting on regardless of
# statistical significance; anything at or above it is.
AOV_MDE_ABSOLUTE = 25.0  # BRL, absolute lift in mean per-seller AOV

# Guardrail MDE: the maximum tolerable absolute increase in the delivery-complaint
# rate. Two percentage points on a ~13% baseline is roughly a 15% relative jump,
# picked as the threshold past which the seller-satisfaction cost plausibly outweighs
# the AOV gain, independent of what the AOV result says.
GUARDRAIL_MARGIN_ABSOLUTE = 0.02


def primary_power(calibration):
    seller_aov_std = calibration["seller_level"]["seller_level_aov_std"]
    cohens_d = AOV_MDE_ABSOLUTE / seller_aov_std

    analysis = TTestIndPower()
    n_per_arm = analysis.solve_power(
        effect_size=cohens_d, alpha=ALPHA, power=POWER_TARGET, ratio=1.0,
        alternative="two-sided",
    )
    n_per_arm = math.ceil(n_per_arm)

    return {
        "test": "Welch's t-test (two independent means, unequal variance)",
        "unit_of_analysis": "seller (mean AOV across that seller's orders)",
        "mde_absolute_brl": AOV_MDE_ABSOLUTE,
        "baseline_seller_level_aov_std": seller_aov_std,
        "cohens_d": round(cohens_d, 4),
        "alpha": ALPHA,
        "power_target": POWER_TARGET,
        "required_n_per_arm_sellers": n_per_arm,
    }


def guardrail_power(calibration):
    p1 = calibration["overall"]["complaint_rate"]
    p2 = p1 + GUARDRAIL_MARGIN_ABSOLUTE
    h = proportion_effectsize(p2, p1)

    analysis = NormalIndPower()
    n_per_arm_orders = analysis.solve_power(
        effect_size=h, alpha=ALPHA, power=POWER_TARGET, ratio=1.0,
        alternative="two-sided",
    )
    n_per_arm_orders = math.ceil(n_per_arm_orders)

    orders_per_seller = calibration["seller_level"]["orders_per_seller_mean"]
    n_per_arm_sellers_equiv = math.ceil(n_per_arm_orders / orders_per_seller)

    return {
        "test_used_for_power_sizing": "two-proportion z-test (NormalIndPower); "
        "note the planned analysis test itself is one-sided (non-inferiority), "
        "see docs/PREREGISTRATION.md, so this two-sided sizing is a conservative "
        "(not undersized) planning approximation",
        "unit_for_sizing": "order (pooled within arm)",
        "baseline_complaint_rate": p1,
        "non_inferiority_margin_absolute": GUARDRAIL_MARGIN_ABSOLUTE,
        "worst_tolerable_complaint_rate": round(p2, 4),
        "effect_size_h": round(h, 4),
        "alpha": ALPHA,
        "power_target": POWER_TARGET,
        "required_n_per_arm_orders": n_per_arm_orders,
        "orders_per_seller_used_for_conversion": orders_per_seller,
        "required_n_per_arm_sellers_equivalent": n_per_arm_sellers_equiv,
    }


def main():
    calibration = json.load(open(CALIB_PATH))

    primary = primary_power(calibration)
    guardrail = guardrail_power(calibration)

    binding_n = max(
        primary["required_n_per_arm_sellers"],
        guardrail["required_n_per_arm_sellers_equivalent"],
    )
    binding_constraint = (
        "primary (AOV)"
        if primary["required_n_per_arm_sellers"] >= guardrail["required_n_per_arm_sellers_equivalent"]
        else "guardrail (complaint rate)"
    )

    real_sellers_in_scope = calibration["seller_level"]["n_real_sellers_in_scope"]

    result = {
        "alpha": ALPHA,
        "power_target": POWER_TARGET,
        "primary": primary,
        "guardrail": guardrail,
        "binding_constraint": binding_constraint,
        "required_n_per_arm": binding_n,
        "required_total_sellers": binding_n * 2,
        "context_real_sellers_in_scope": real_sellers_in_scope,
        "context_note": (
            f"The design requires {binding_n} sellers per arm ({binding_n * 2} total). "
            f"The Olist calibration data contains {real_sellers_in_scope} sellers in "
            "scope. This is reported as context, not as a cap: the analysis population "
            "is simulated, so it is sized to what the design requires, not to what one "
            "historical snapshot of Olist happened to contain. If the required N could "
            "not be reached with real sellers, that would be a real-world feasibility "
            "problem for whoever runs this test live, worth flagging to stakeholders, "
            "but it does not change what the statistics require."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {OUT_PATH}")
    print(f"Primary required N/arm (sellers): {primary['required_n_per_arm_sellers']}")
    print(f"Guardrail required N/arm (sellers-equivalent): "
          f"{guardrail['required_n_per_arm_sellers_equivalent']}")
    print(f"Binding constraint: {binding_constraint}")
    print(f"Required N per arm: {binding_n} (total {binding_n * 2})")
    print(f"Real sellers in scope for comparison: {real_sellers_in_scope}")


if __name__ == "__main__":
    main()



