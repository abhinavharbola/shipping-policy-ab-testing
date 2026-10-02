from experiment.reporting import build_memo, memo_content


def make_results(status="inconclusive", significant=True, lift=38.07, meets=True):
    return {
        "primary": {
            "n_treatment_sellers": 2503,
            "n_control_sellers": 2503,
            "treatment_mean_aov": 172.09,
            "control_mean_aov": 134.02,
            "point_estimate_lift": lift,
            "ci_95_low": 21.32,
            "ci_95_high": 54.82,
            "significant_at_alpha_0.05": significant,
            "mde_absolute_brl": 25.0,
            "lift_meets_mde": meets,
        },
        "guardrail": {
            "treatment_complaint_rate": 0.139,
            "control_complaint_rate": 0.1218,
            "point_estimate_diff": 0.0173,
            "non_inferiority_margin": 0.02,
            "guardrail_status": status,
        },
    }


def test_every_dollar_sign_sits_inside_a_code_span():
    memo = build_memo(make_results())
    for line in memo.splitlines():
        if "$" not in line:
            continue
        inside = False
        for ch in line:
            if ch == "`":
                inside = not inside
            elif ch == "$":
                assert inside, f"bare dollar sign outside a code span: {line!r}"
        assert not inside


def test_bottom_line_is_not_a_copy_of_the_recommendation():
    results = make_results()
    content = memo_content(results)
    assert content["next_step"] != content["reasoning"]


def test_inconclusive_memo_does_not_claim_a_crossed_line():
    memo = build_memo(make_results(status="inconclusive"))
    assert "crossed" not in memo
    assert "cannot rule out" in memo


def test_breached_memo_states_the_estimate_is_at_or_above_the_line():
    memo = build_memo(make_results(status="breached"))
    assert "at or above that line" in memo


def test_memo_makes_no_causal_claim_about_delivery():
    for status in ("passed", "breached", "inconclusive"):
        memo = build_memo(make_results(status=status)).lower()
        assert "fix delivery" not in memo


def test_memo_reports_minimum_lift_outcome():
    met = build_memo(make_results(meets=True))
    missed = build_memo(make_results(lift=10.0, meets=False))
    assert "meets the minimum lift" in met
    assert "falls short of the minimum lift" in missed


def test_percentage_point_difference_shows_two_decimals():
    memo = build_memo(make_results())
    assert "1.73 percentage points" in memo
    assert "2.00 percentage points" in memo
