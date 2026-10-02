import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from design.preregistered import (
    ALPHA,
    AOV_MDE_ABSOLUTE,
    GUARDRAIL_MARGIN_ABSOLUTE,
    N_PER_ARM,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ASSIGNED_PATH = DATA / "simulated" / "assigned_experiment.csv"
TRUE_EFFECTS_PATH = DATA / "simulated" / "true_effects.json"
RESULTS_PATH = ROOT / "results" / "analysis_results.json"
RECOVERY_PATH = ROOT / "results" / "recovery_check.json"

EXPECTED_N_PER_ARM = N_PER_ARM


class PartialDatasetError(ValueError):
    pass


class ReanalysisError(RuntimeError):
    pass


def analyze(experiment_df):
    seller_counts = experiment_df.groupby("arm")["seller_id"].nunique()
    for arm in ("treatment", "control"):
        if seller_counts.get(arm, 0) != EXPECTED_N_PER_ARM:
            raise PartialDatasetError(
                f"Expected exactly {EXPECTED_N_PER_ARM} sellers in arm '{arm}' "
                f"per the preregistered fixed-horizon design; got "
                f"{seller_counts.get(arm, 0)}. Analysis refuses to run on a "
                "partial or over-accrued sample. See docs/PREREGISTRATION.md section 6."
            )

    if experiment_df.groupby("seller_id")["arm"].nunique().max() > 1:
        raise ValueError("At least one seller appears in more than one arm.")

    primary = _analyze_primary(experiment_df)
    guardrail = _analyze_guardrail(experiment_df)

    return {"primary": primary, "guardrail": guardrail}


def _analyze_primary(experiment_df):
    seller_means = experiment_df.groupby(["seller_id", "arm"])["aov"].mean().reset_index()
    treatment = seller_means.loc[seller_means["arm"] == "treatment", "aov"]
    control = seller_means.loc[seller_means["arm"] == "control", "aov"]

    t_stat, p_value = stats.ttest_ind(treatment, control, equal_var=False)
    point_estimate = float(treatment.mean() - control.mean())

    var_t = treatment.var(ddof=1) / len(treatment)
    var_c = control.var(ddof=1) / len(control)
    se = np.sqrt(var_t + var_c)
    df = (var_t + var_c) ** 2 / (
        var_t ** 2 / (len(treatment) - 1) + var_c ** 2 / (len(control) - 1)
    )
    t_crit = stats.t.ppf(1 - ALPHA / 2, df)
    ci_low = point_estimate - t_crit * se
    ci_high = point_estimate + t_crit * se

    return {
        "test": "Welch's t-test, two-sided",
        "unit_of_analysis": "seller (mean AOV)",
        "n_treatment_sellers": int(len(treatment)),
        "n_control_sellers": int(len(control)),
        "treatment_mean_aov": round(float(treatment.mean()), 2),
        "control_mean_aov": round(float(control.mean()), 2),
        "point_estimate_lift": round(point_estimate, 2),
        "ci_95_low": round(float(ci_low), 2),
        "ci_95_high": round(float(ci_high), 2),
        "t_statistic": round(float(t_stat), 4),
        "p_value": float(p_value),
        "significant_at_alpha_0.05": bool(p_value < ALPHA),
        "mde_absolute_brl": AOV_MDE_ABSOLUTE,
        "lift_meets_mde": bool(point_estimate >= AOV_MDE_ABSOLUTE),
    }


def _analyze_guardrail(experiment_df):
    return _guardrail_stats(experiment_df, GUARDRAIL_MARGIN_ABSOLUTE)


def _arm_rate_and_variance(seller_totals):
    n = seller_totals["n"].to_numpy(dtype=float)
    c = seller_totals["c"].to_numpy(dtype=float)
    m = len(n)
    total_n = n.sum()
    rate = c.sum() / total_n
    residual = c - rate * n
    variance = m / (m - 1) * np.sum(residual ** 2) / total_n ** 2
    return float(rate), float(variance), int(total_n)


def _guardrail_stats(experiment_df, margin):
    reviewed = experiment_df.dropna(subset=["complaint"])
    totals = (
        reviewed.groupby(["arm", "seller_id"])["complaint"]
        .agg(n="size", c="sum")
        .reset_index()
    )
    treatment = totals[totals["arm"] == "treatment"]
    control = totals[totals["arm"] == "control"]

    p_treatment, var_treatment, n_treatment_orders = _arm_rate_and_variance(treatment)
    p_control, var_control, n_control_orders = _arm_rate_and_variance(control)
    point_estimate = p_treatment - p_control

    se = float(np.sqrt(var_treatment + var_control))
    if not se > 0:
        raise ValueError("Guardrail standard error is zero; the data are degenerate.")

    z_stat = (point_estimate - margin) / se
    p_value_non_inferiority = float(stats.norm.cdf(z_stat))
    non_inferiority_established = bool(p_value_non_inferiority < ALPHA)
    exceeds_margin = bool(point_estimate >= margin)

    if non_inferiority_established:
        status = "passed"
    elif exceeds_margin:
        status = "breached"
    else:
        status = "inconclusive"

    z_crit = stats.norm.ppf(1 - ALPHA / 2)
    ci_low = point_estimate - z_crit * se
    ci_high = point_estimate + z_crit * se

    return {
        "test": "order-weighted complaint rate per arm with seller-clustered "
        "standard errors, margin-shifted one-sided z-test "
        "(non-inferiority: H0 is diff >= margin)",
        "unit_for_test": "seller is the cluster for the variance; the rate is the "
        "share of orders reviewed at or below the complaint threshold",
        "n_treatment_sellers": int(len(treatment)),
        "n_control_sellers": int(len(control)),
        "n_treatment_orders": n_treatment_orders,
        "n_control_orders": n_control_orders,
        "treatment_complaint_rate": round(p_treatment, 4),
        "control_complaint_rate": round(p_control, 4),
        "point_estimate_diff": round(point_estimate, 4),
        "standard_error": round(se, 5),
        "ci_95_low": round(float(ci_low), 4),
        "ci_95_high": round(float(ci_high), 4),
        "z_statistic_vs_margin": round(float(z_stat), 4),
        "p_value_non_inferiority": p_value_non_inferiority,
        "non_inferiority_margin": margin,
        "non_inferiority_established": non_inferiority_established,
        "point_estimate_exceeds_margin": exceeds_margin,
        "guardrail_status": status,
    }


def check_ground_truth_recovery(results):
    true_effects = json.loads(TRUE_EFFECTS_PATH.read_text(encoding="utf-8"))

    injected_aov = true_effects["true_aov_lift_absolute"]
    realized_aov = true_effects["realized_aov_lift_seller_level"]
    primary_ci = (results["primary"]["ci_95_low"], results["primary"]["ci_95_high"])
    primary_recovered = primary_ci[0] <= realized_aov <= primary_ci[1]
    primary_covers_injected = primary_ci[0] <= injected_aov <= primary_ci[1]

    injected_complaint = true_effects["true_complaint_lift_absolute"]
    realized_complaint = true_effects["realized_complaint_diff_order_level"]
    guardrail_ci = (results["guardrail"]["ci_95_low"], results["guardrail"]["ci_95_high"])
    guardrail_recovered = guardrail_ci[0] <= realized_complaint <= guardrail_ci[1]
    guardrail_covers_injected = guardrail_ci[0] <= injected_complaint <= guardrail_ci[1]
    margin = results["guardrail"]["non_inferiority_margin"]

    return {
        "injected_aov_lift": injected_aov,
        "realized_aov_lift": realized_aov,
        "primary_ci": primary_ci,
        "primary_recovered": bool(primary_recovered),
        "primary_ci_covers_injected": bool(primary_covers_injected),
        "injected_complaint_lift": injected_complaint,
        "realized_complaint_diff": realized_complaint,
        "guardrail_ci": guardrail_ci,
        "guardrail_recovered": bool(guardrail_recovered),
        "guardrail_ci_covers_injected": bool(guardrail_covers_injected),
        "realized_complaint_diff_below_margin": bool(realized_complaint < margin),
        "both_recovered": bool(primary_recovered and guardrail_recovered),
    }


def data_fingerprint(experiment_df):
    payload = experiment_df.round(4).to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def refuse_reanalysis_of_different_data(fingerprint):
    if not RESULTS_PATH.is_file():
        return
    prior = json.loads(RESULTS_PATH.read_text(encoding="utf-8")).get("data_fingerprint")
    if prior is not None and prior != fingerprint:
        raise ReanalysisError(
            f"{RESULTS_PATH} already holds a result computed on different data. "
            "The preregistered analysis runs once. Delete the existing results "
            "deliberately if this is a new run."
        )


def main():
    experiment_df = pd.read_csv(ASSIGNED_PATH)
    fingerprint = data_fingerprint(experiment_df)
    refuse_reanalysis_of_different_data(fingerprint)

    results = analyze(experiment_df)
    results["data_fingerprint"] = fingerprint

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {RESULTS_PATH}")
    print(json.dumps(results, indent=2))

    recovery = check_ground_truth_recovery(results)
    with open(RECOVERY_PATH, "w", encoding="utf-8") as f:
        json.dump(recovery, f, indent=2)
    print(f"\nWrote {RECOVERY_PATH}")
    print(json.dumps(recovery, indent=2))


if __name__ == "__main__":
    main()
