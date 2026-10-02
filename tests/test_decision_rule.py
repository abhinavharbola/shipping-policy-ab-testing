from experiment.reporting import recommendation


def primary(significant=True, lift=30.0, meets=True):
    return {
        "significant_at_alpha_0.05": significant,
        "point_estimate_lift": lift,
        "lift_meets_mde": meets,
    }


def guardrail(status):
    return {"guardrail_status": status}


def test_go_requires_every_condition():
    verdict, _ = recommendation(primary(), guardrail("passed"))
    assert verdict == "GO"


def test_insignificant_lift_is_no_go():
    verdict, _ = recommendation(primary(significant=False, meets=True), guardrail("passed"))
    assert verdict == "NO-GO"


def test_negative_significant_lift_is_no_go():
    verdict, reasoning = recommendation(
        primary(lift=-10.0, meets=False), guardrail("passed")
    )
    assert verdict == "NO-GO"
    assert "lowered" in reasoning


def test_significant_lift_below_mde_is_no_go():
    verdict, reasoning = recommendation(primary(lift=5.0, meets=False), guardrail("passed"))
    assert verdict == "NO-GO"
    assert "minimum lift" in reasoning


def test_breached_and_inconclusive_are_both_no_go_with_different_wording():
    breached_verdict, breached_text = recommendation(primary(), guardrail("breached"))
    inconclusive_verdict, inconclusive_text = recommendation(primary(), guardrail("inconclusive"))
    assert breached_verdict == inconclusive_verdict == "NO-GO"
    assert breached_text != inconclusive_text
    assert "rose by at least" in breached_text
    assert "rose by at least" not in inconclusive_text
    assert "cannot rule out" in inconclusive_text
