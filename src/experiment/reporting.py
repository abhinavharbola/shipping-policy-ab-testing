"""
Step 7: reporting.

Turns results/analysis_results.json into a short memo a stakeholder with
no statistics background can read and act on. Reads only the analysis
output, never raw or simulated data directly (see tests/).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = ROOT / "results" / "analysis_results.json"
OUT_PATH = ROOT / "results" / "memo.md"


def recommendation(primary, guardrail):
    lift_significant = primary["significant_at_alpha_0.05"]
    lift_positive = primary["point_estimate_lift"] > 0
    breached = guardrail["guardrail_breached"]

    if lift_significant and lift_positive and not breached:
        return "GO", (
            "Roll out free shipping. It raises average order value by a "
            "statistically clear margin, and the complaint rate did not "
            "cross the line we set in advance."
        )
    if breached:
        return "NO-GO", (
            "Hold off. The complaint rate rose more than the agreed "
            "threshold, regardless of the AOV result. Fix delivery "
            "experience before revisiting free shipping."
        )
    if not lift_significant:
        return "NO-GO", (
            "Hold off. We cannot distinguish the observed AOV change from "
            "noise at the sample size we ran. Either the effect is smaller "
            "than what's worth acting on, or this run needs more data."
        )
    return "NO-GO", "Hold off. The result does not clear the bar we set before running this test."


def next_step(primary, guardrail, verdict):
    """
    A forward-looking action, distinct from the verdict reasoning above it.
    The memo previously repeated the exact same sentence under both
    'Recommendation' and 'Bottom line' - this gives the reader something
    new the second time instead of an echo.
    """
    if verdict == "GO":
        return (
            "Ship the change, then keep watching the complaint rate for at "
            "least one full cycle after rollout. The guardrail held in this "
            "trial; it still needs to hold outside it."
        )
    if guardrail["guardrail_breached"]:
        return (
            "Fix delivery capacity or expectations before re-testing. "
            "Rerunning the same experiment without addressing what's "
            "driving complaints will likely breach the guardrail again."
        )
    if not primary["significant_at_alpha_0.05"]:
        return (
            "This trial was powered to detect a lift at least as large as "
            "the preregistered MDE. If a smaller lift would still be worth "
            "having, the next step is a larger sample, not a different test."
        )
    return (
        "The observed effect runs counter to the hypothesis. Treat this as "
        "evidence against the policy change in its current form, not as an "
        "inconclusive result."
    )


def build_memo(results):
    primary = results["primary"]
    guardrail = results["guardrail"]
    verdict, verdict_text = recommendation(primary, guardrail)

    lift = primary["point_estimate_lift"]
    ci_low, ci_high = primary["ci_95_low"], primary["ci_95_high"]
    lift_significant = primary["significant_at_alpha_0.05"]
    significance_sentence = (
        "This interval does not include zero, so the lift is unlikely "
        "to be due to chance."
        if lift_significant
        else "This interval includes zero, so this result cannot be "
        "distinguished from no effect at all."
    )
    g_rate_t = guardrail["treatment_complaint_rate"] * 100
    g_rate_c = guardrail["control_complaint_rate"] * 100
    g_diff = guardrail["point_estimate_diff"] * 100
    margin = guardrail["non_inferiority_margin"] * 100

    memo = f"""# Free Shipping Experiment: Stakeholder Memo

## Recommendation: {verdict}

{verdict_text}

## What we tested

We randomly split {primary['n_treatment_sellers'] + primary['n_control_sellers']} sellers into two groups: half kept
standard shipping, half switched to free shipping. We measured whether
free shipping changed average order value, and separately checked
whether it made delivery complaints worse.

## Order value result

Sellers offering free shipping had an average order value of
`R$ {primary['treatment_mean_aov']}`, versus `R$ {primary['control_mean_aov']}` for sellers on standard
shipping. That's a lift of **`R$ {lift}`** (95% confidence interval: `R$ {ci_low}` to
`R$ {ci_high}`). {significance_sentence}

## Complaint rate check (guardrail)

Delivery complaints ran at {g_rate_t:.1f}% under free shipping versus {g_rate_c:.1f}%
under standard shipping, a difference of {g_diff:.1f} percentage points. We had
pre-agreed that anything under {margin:.1f} points was acceptable. {"This crossed that line." if guardrail['guardrail_breached'] else "This stayed within that line."}

## Bottom line

{next_step(primary, guardrail, verdict)}
"""
    return memo


def main():
    results = json.load(open(RESULTS_PATH))
    memo = build_memo(results)
    with open(OUT_PATH, "w") as f:
        f.write(memo)
    print(f"Wrote {OUT_PATH}")
    print(memo)


if __name__ == "__main__":
    main()



