"""
Step 6: analyze.

Runs exactly the tests specified in docs/PREREGISTRATION.md: Welch's t-test
on seller-level mean AOV (primary), one-sided two-proportion z-test on
pooled order-level complaints (guardrail). Nothing else, and nothing
added after seeing the result.

`analyze()` is the only function that touches experimental data, and it
reads only data/simulated/assigned_experiment.csv, which contains no
counterfactual columns and no true-effect information (see randomize.py).
It also refuses to run on anything but the full pre-specified sample,
enforcing the fixed-horizon stopping rule from docs/PREREGISTRATION.md
section 6.

The ground-truth recovery check is deliberately kept OUTSIDE analyze():
it is the only piece of code in this file allowed to read
data/simulated/true_effects.json, and it runs after analyze() has
already produced its result, using analyze()'s output as a black box.
This ordering is what tests/test_no_raw_data_leak.py checks.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ASSIGNED_PATH = DATA / "simulated" / "assigned_experiment.csv"
POWER_PATH = ROOT / "results" / "power_analysis.json"
TRUE_EFFECTS_PATH = DATA / "simulated" / "true_effects.json"
RESULTS_PATH = ROOT / "results" / "analysis_results.json"
RECOVERY_PATH = ROOT / "results" / "recovery_check.json"

ALPHA = 0.05


class PartialDatasetError(ValueError):
    pass


def _expected_n_per_arm():
    return json.load(open(POWER_PATH))["required_n_per_arm"]


def analyze(experiment_df, expected_n_per_arm=None):
    """
    Run the preregistered primary and guardrail analyses on a fully
    realized experiment dataset. Raises PartialDatasetError if the
    dataset does not contain the full preregistered sample per arm,
    enforcing the no-peeking / fixed-horizon stopping rule.
    """
    if expected_n_per_arm is None:
        expected_n_per_arm = _expected_n_per_arm()

    seller_counts = experiment_df.groupby("arm")["seller_id"].nunique()
    for arm in ("treatment", "control"):
        if seller_counts.get(arm, 0) != expected_n_per_arm:
            raise PartialDatasetError(
                f"Expected exactly {expected_n_per_arm} sellers in arm '{arm}' "
                f"per the preregistered fixed-horizon design; got "
                f"{seller_counts.get(arm, 0)}. Analysis refuses to run on a "
                "partial or over-accrued sample. See docs/PREREGISTRATION.md section 6."
            )

    primary = _analyze_primary(experiment_df)
    guardrail = _analyze_guardrail(experiment_df)

    return {"primary": primary, "guardrail": guardrail}


def _analyze_primary(experiment_df):
    seller_means = experiment_df.groupby(["seller_id", "arm"])["aov"].mean().reset_index()
    treatment = seller_means.loc[seller_means["arm"] == "treatment", "aov"]
    control = seller_means.loc[seller_means["arm"] == "control", "aov"]

    t_stat, p_value = stats.ttest_ind(treatment, control, equal_var=False)
    point_estimate = float(treatment.mean() - control.mean())

    se = np.sqrt(treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control))
    df = (
        (treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control)) ** 2
    ) / (
        (treatment.var(ddof=1) / len(treatment)) ** 2 / (len(treatment) - 1)
        + (control.var(ddof=1) / len(control)) ** 2 / (len(control) - 1)
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
    }


def _analyze_guardrail(experiment_df):
    treatment = experiment_df[experiment_df["arm"] == "treatment"]
    control = experiment_df[experiment_df["arm"] == "control"]

    count = np.array([treatment["complaint"].sum(), control["complaint"].sum()])
    nobs = np.array([len(treatment), len(control)])

    # One-sided: is treatment's complaint rate higher than control's?
    z_stat, p_value_one_sided = proportions_ztest(count, nobs, alternative="larger")

    p_treatment = count[0] / nobs[0]
    p_control = count[1] / nobs[1]
    point_estimate = float(p_treatment - p_control)

    # Reported CI is the standard two-sided 95% interval for the point estimate
    # itself (used below by the ground-truth recovery check); the go/no-go
    # breach decision does not use this CI at all, it uses p_value_one_sided
    # against ALPHA directly, consistent with the preregistered one-sided test.
    se = np.sqrt(p_treatment * (1 - p_treatment) / nobs[0] + p_control * (1 - p_control) / nobs[1])
    z_crit = stats.norm.ppf(1 - ALPHA / 2)
    ci_low = point_estimate - z_crit * se
    ci_high = point_estimate + z_crit * se

    margin = json.load(open(POWER_PATH))["guardrail"][
        "non_inferiority_margin_absolute"
    ]
    breach = point_estimate > margin and p_value_one_sided < ALPHA

    return {
        "test": "one-sided two-proportion z-test (treatment > control), pooled order-level counts",
        "unit_for_test": "order (documented clustering simplification, see docs/PREREGISTRATION.md section 8)",
        "n_treatment_orders": int(nobs[0]),
        "n_control_orders": int(nobs[1]),
        "treatment_complaint_rate": round(float(p_treatment), 4),
        "control_complaint_rate": round(float(p_control), 4),
        "point_estimate_diff": round(point_estimate, 4),
        "ci_95_low": round(float(ci_low), 4),
        "ci_95_high": round(float(ci_high), 4),
        "z_statistic": round(float(z_stat), 4),
        "p_value_one_sided": float(p_value_one_sided),
        "non_inferiority_margin": margin,
        "guardrail_breached": bool(breach),
    }


def check_ground_truth_recovery(results):
    """
    Reads true_effects.json. This is the only function in the project
    allowed to do so, and it is called only after analyze() has already
    produced `results` from data it could not have seen this file's
    contents through.
    """
    true_effects = json.load(open(TRUE_EFFECTS_PATH))

    primary_ci = (results["primary"]["ci_95_low"], results["primary"]["ci_95_high"])
    true_aov = true_effects["true_aov_lift_absolute"]
    primary_recovered = primary_ci[0] <= true_aov <= primary_ci[1]

    guardrail_ci = (results["guardrail"]["ci_95_low"], results["guardrail"]["ci_95_high"])
    true_complaint = true_effects["true_complaint_lift_absolute"]
    guardrail_recovered = guardrail_ci[0] <= true_complaint <= guardrail_ci[1]

    return {
        "true_aov_lift": true_aov,
        "primary_ci": primary_ci,
        "primary_recovered": bool(primary_recovered),
        "true_complaint_lift": true_complaint,
        "guardrail_ci": guardrail_ci,
        "guardrail_recovered": bool(guardrail_recovered),
        "both_recovered": bool(primary_recovered and guardrail_recovered),
    }


def main():
    experiment_df = pd.read_csv(ASSIGNED_PATH)
    results = analyze(experiment_df)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {RESULTS_PATH}")
    print(json.dumps(results, indent=2))

    recovery = check_ground_truth_recovery(results)
    with open(RECOVERY_PATH, "w") as f:
        json.dump(recovery, f, indent=2)
    print(f"\nWrote {RECOVERY_PATH}")
    print(json.dumps(recovery, indent=2))


if __name__ == "__main__":
    main()



