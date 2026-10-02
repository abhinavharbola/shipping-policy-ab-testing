import json
import math
from pathlib import Path

from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize

from design.preregistered import (
    ALPHA,
    AOV_MDE_ABSOLUTE,
    GUARDRAIL_MARGIN_ABSOLUTE,
    N_PER_ARM,
    POWER_TARGET,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CALIB_PATH = DATA / "calibration" / "calibration_params.json"
OUT_PATH = ROOT / "results" / "power_analysis.json"


class DesignDriftError(RuntimeError):
    pass


def primary_power(calibration):
    seller_aov_std = calibration["seller_level"]["seller_level_aov_std"]
    cohens_d = AOV_MDE_ABSOLUTE / seller_aov_std

    analysis = TTestIndPower()
    n_per_arm = analysis.solve_power(
        effect_size=cohens_d,
        alpha=ALPHA,
        power=POWER_TARGET,
        ratio=1.0,
        alternative="two-sided",
    )
    n_per_arm = math.ceil(n_per_arm)

    return {
        "test": "Two-sample t-test power (TTestIndPower, equal n, equal variance "
        "planning assumption; with equal n this closely approximates Welch's "
        "t-test, which is the test that runs)",
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
        effect_size=h,
        alpha=ALPHA,
        power=POWER_TARGET,
        ratio=1.0,
        alternative="two-sided",
    )
    n_per_arm_orders = math.ceil(n_per_arm_orders)

    orders_per_seller = calibration["seller_level"]["orders_per_seller_mean"]
    n_per_arm_sellers_equiv = math.ceil(n_per_arm_orders / orders_per_seller)

    return {
        "test_used_for_power_sizing": "two-proportion z-test (NormalIndPower), pooled "
        "order-level counts, sized to detect a margin-sized difference against zero. "
        "The planned analysis test is a one-sided, margin-shifted non-inferiority "
        "test on the order-weighted complaint rate with seller-clustered standard "
        "errors (see docs/PREREGISTRATION.md section 8), so this is an order-level "
        "planning approximation, not a power calculation for the test that runs: it "
        "ignores within-seller correlation and can understate the sellers that test "
        "needs (see the section 4 amendment). The conversion to sellers uses the mean "
        "orders per seller, which the heavily skewed real distribution makes "
        "unrepresentative. A seller-clustered power calculation would need "
        "per-seller complaint-rate variance, which calibration.py does not "
        "currently compute.",
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
    calibration = json.loads(CALIB_PATH.read_text(encoding="utf-8"))

    primary = primary_power(calibration)
    guardrail = guardrail_power(calibration)

    binding_n = max(
        primary["required_n_per_arm_sellers"],
        guardrail["required_n_per_arm_sellers_equivalent"],
    )
    binding_constraint = (
        "primary (AOV)"
        if primary["required_n_per_arm_sellers"]
        >= guardrail["required_n_per_arm_sellers_equivalent"]
        else "guardrail (complaint rate)"
    )

    if binding_n != N_PER_ARM:
        raise DesignDriftError(
            f"Computed required N per arm is {binding_n}, but the preregistered "
            f"N per arm is {N_PER_ARM} (src/design/preregistered.py and "
            "docs/PREREGISTRATION.md). The calibration inputs have changed since "
            "the design was locked. Nothing was written. Amend the preregistration "
            "explicitly before changing the frozen constants."
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
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {OUT_PATH}")
    print(f"Primary required N/arm (sellers): {primary['required_n_per_arm_sellers']}")
    print(
        f"Guardrail required N/arm (sellers-equivalent): "
        f"{guardrail['required_n_per_arm_sellers_equivalent']}"
    )
    print(f"Binding constraint: {binding_constraint}")
    print(f"Required N per arm: {binding_n} (total {binding_n * 2})")
    print(f"Real sellers in scope for comparison: {real_sellers_in_scope}")


if __name__ == "__main__":
    main()
