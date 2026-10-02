import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = ROOT / "results" / "analysis_results.json"
OUT_PATH = ROOT / "results" / "memo.md"


def recommendation(primary, guardrail):
    status = guardrail["guardrail_status"]
    lift_significant = primary["significant_at_alpha_0.05"]
    lift_positive = primary["point_estimate_lift"] > 0

    if status == "breached":
        return "NO-GO", (
            "Hold off. The complaint rate rose by at least the agreed "
            "threshold, regardless of the order value result."
        )
    if status == "inconclusive":
        return "NO-GO", (
            "Hold off. The measured complaint increase is below the agreed "
            "threshold, but the data cannot rule out an increase at or above "
            "it, and the rule we set in advance requires that to be ruled out."
        )
    if not lift_significant:
        return "NO-GO", (
            "Hold off. We cannot distinguish the observed order value change "
            "from noise at the sample size we ran."
        )
    if not lift_positive:
        return "NO-GO", (
            "Hold off. Free shipping lowered average order value by a "
            "statistically clear margin."
        )
    if not primary["lift_meets_mde"]:
        return "NO-GO", (
            "Hold off. The lift is statistically clear but smaller than the "
            "minimum lift we agreed in advance was worth acting on."
        )
    return "GO", (
        "Roll out free shipping. It raises average order value by a "
        "statistically clear margin that also clears the minimum lift we set "
        "in advance, and the data show complaints stayed below the agreed "
        "threshold."
    )


def next_step(primary, guardrail, verdict):
    status = guardrail["guardrail_status"]
    if verdict == "GO":
        return (
            "Ship the change, then keep watching the complaint rate for at "
            "least one full cycle after rollout. The guardrail held in this "
            "trial; it still needs to hold outside it."
        )
    if status == "breached":
        return (
            "Investigate what is driving the extra complaints before "
            "re-testing. A review score of 2 or below can have causes other "
            "than delivery, so this trial does not say which one applies. "
            "Rerunning unchanged is unlikely to change the outcome."
        )
    if status == "inconclusive":
        return (
            "This is a precision problem, not a measured breach. The "
            "guardrail needs a larger sample or a tighter complaint estimate "
            "before it can be ruled on, and this result stays a NO-GO under "
            "the rule set in advance."
        )
    if not primary["significant_at_alpha_0.05"]:
        return (
            "This trial was powered to detect a lift at least as large as "
            "the preregistered minimum. If a smaller lift would still be "
            "worth having, the next step is a larger sample, not a different "
            "test."
        )
    if primary["point_estimate_lift"] <= 0:
        return (
            "The observed effect runs counter to the hypothesis. Treat this "
            "as evidence against the policy change in its current form, not "
            "as an inconclusive result."
        )
    return (
        "The lift is real but below the minimum worth acting on. Only a "
        "different policy design or a cheaper way to deliver it would change "
        "the case."
    )


def guardrail_sentence(guardrail):
    status = guardrail["guardrail_status"]
    margin = guardrail["non_inferiority_margin"] * 100
    if status == "passed":
        outcome = "The data show the difference is below that line."
    elif status == "breached":
        outcome = "The measured difference is at or above that line."
    else:
        outcome = (
            "The measured difference is below that line, but the data cannot "
            "rule out a difference at or above it."
        )
    return (
        f"The rule agreed in advance is that free shipping passes only if "
        f"the data show, with 95% one-sided confidence, that the difference "
        f"is below {margin:.2f} percentage points. {outcome}"
    )


def memo_content(results):
    primary = results["primary"]
    guardrail = results["guardrail"]
    verdict, reasoning = recommendation(primary, guardrail)

    if primary["significant_at_alpha_0.05"]:
        significance_sentence = (
            "This interval does not include zero, so the lift is unlikely "
            "to be due to chance."
        )
    else:
        significance_sentence = (
            "This interval includes zero, so this result cannot be "
            "distinguished from no effect at all."
        )

    if primary["lift_meets_mde"]:
        minimum_sentence = "The estimate meets the minimum lift agreed in advance."
    else:
        minimum_sentence = "The estimate falls short of the minimum lift agreed in advance."

    return {
        "verdict": verdict,
        "reasoning": reasoning,
        "significance_sentence": significance_sentence,
        "minimum_sentence": minimum_sentence,
        "guardrail_sentence": guardrail_sentence(guardrail),
        "next_step": next_step(primary, guardrail, verdict),
    }


def build_memo(results):
    primary = results["primary"]
    guardrail = results["guardrail"]
    content = memo_content(results)

    lift = primary["point_estimate_lift"]
    ci_low, ci_high = primary["ci_95_low"], primary["ci_95_high"]
    mde = primary["mde_absolute_brl"]
    g_rate_t = guardrail["treatment_complaint_rate"] * 100
    g_rate_c = guardrail["control_complaint_rate"] * 100
    g_diff = guardrail["point_estimate_diff"] * 100
    n_total = primary["n_treatment_sellers"] + primary["n_control_sellers"]

    memo = f"""# Free Shipping Experiment: Stakeholder Memo

## Recommendation: {content['verdict']}

{content['reasoning']}

## What we tested

We randomly split {n_total:,} sellers into two groups: half kept
standard shipping, half switched to free shipping. We measured whether
free shipping changed average order value, and separately checked
whether it made complaints (reviews of 2 stars or below) worse.

## Order value result

Sellers offering free shipping had an average order value of
`R$ {primary['treatment_mean_aov']:.2f}`, versus `R$ {primary['control_mean_aov']:.2f}` for sellers on standard
shipping. That's a lift of **`R$ {lift:.2f}`** (95% confidence interval: `R$ {ci_low:.2f}` to
`R$ {ci_high:.2f}`). {content['significance_sentence']} The smallest lift we agreed was
worth acting on is `R$ {mde:.2f}`. {content['minimum_sentence']}

## Complaint rate check (guardrail)

Complaints ran at {g_rate_t:.2f}% of orders under free shipping versus {g_rate_c:.2f}%
under standard shipping, a difference of {g_diff:.2f} percentage points.
{content['guardrail_sentence']}

## Bottom line

{content['next_step']}
"""
    return memo


def main():
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    memo = build_memo(results)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(memo)
    print(f"Wrote {OUT_PATH}")
    print(memo)


if __name__ == "__main__":
    main()
