"""
Streamlit's markdown renderer treats paired, unescaped '$' characters as
inline LaTeX math. The memo template writes 'R$' several times in the
same paragraph, so every dollar sign must be protected from that pairing
or the memo renders as broken math instead of currency in the dashboard.

The template protects them by wrapping each 'R$ value' in backtick code
spans ('`R$ 31.59`'), which markdown parsers treat as literal text before
any math-pairing rule runs - that's the actual invariant that matters,
not any one specific escaping mechanism. This test checks the invariant
directly: every '$' character in the rendered memo must sit inside a
backtick-delimited span.
"""

import re

from experiment import reporting


def make_fake_results():
    return {
        "primary": {
            "n_treatment_sellers": 2503,
            "n_control_sellers": 2503,
            "treatment_mean_aov": 171.13,
            "control_mean_aov": 139.54,
            "point_estimate_lift": 31.59,
            "ci_95_low": 24.10,
            "ci_95_high": 39.09,
            "significant_at_alpha_0.05": True,
        },
        "guardrail": {
            "treatment_complaint_rate": 0.144,
            "control_complaint_rate": 0.133,
            "point_estimate_diff": 0.0106,
            "non_inferiority_margin": 0.02,
            "guardrail_breached": False,
        },
    }


def _spans_protected_by_backticks(text):
    """True if every '$' in text falls inside a matched pair of backticks."""
    in_code_span = False
    for ch in text:
        if ch == "`":
            in_code_span = not in_code_span
        elif ch == "$" and not in_code_span:
            return False
    return not in_code_span  # also false if backticks were left unpaired


def test_memo_never_has_a_dollar_sign_outside_a_code_span():
    memo = reporting.build_memo(make_fake_results())
    assert _spans_protected_by_backticks(memo), (
        "Found a '$' outside a backtick code span, which Streamlit's "
        "markdown renderer will pair up and interpret as LaTeX math "
        "instead of currency."
    )


def test_memo_still_contains_the_currency_values():
    memo = reporting.build_memo(make_fake_results())
    assert "171.13" in memo
    assert "31.59" in memo
    assert "`R$" in memo


def make_fake_results_unclean_decimals():
    """
    Values whose second decimal digit is zero, so plain f-string
    interpolation of a Python float would silently drop it (24.1 instead
    of 24.10). Regression test for a real bug: build_memo previously
    interpolated currency figures without a :.2f format spec, so the memo
    only showed two decimal places by coincidence when the underlying
    numbers happened to round cleanly.
    """
    results = make_fake_results()
    results["primary"] = {
        **results["primary"],
        "treatment_mean_aov": 171.10,
        "control_mean_aov": 139.50,
        "point_estimate_lift": 31.60,
        "ci_95_low": 24.10,
        "ci_95_high": 39.00,
    }
    return results


def test_memo_always_shows_two_decimal_places_for_currency():
    memo = reporting.build_memo(make_fake_results_unclean_decimals())
    assert "R$ 171.10" in memo
    assert "R$ 139.50" in memo
    assert "R$ 31.60" in memo
    assert "R$ 24.10" in memo
    assert "R$ 39.00" in memo
    # Guard against the regression this pins: a bare float interpolation
    # would produce these truncated, trailing-zero-dropped forms instead.
    assert "R$ 171.1`" not in memo
    assert "R$ 139.5`" not in memo
    assert "R$ 31.6`" not in memo
    assert "R$ 24.1`" not in memo
    assert "R$ 39.0`" not in memo


def make_fake_results_not_significant():
    results = make_fake_results()
    results["primary"] = {
        **results["primary"],
        "point_estimate_lift": 4.20,
        "ci_95_low": -3.10,
        "ci_95_high": 11.50,
        "significant_at_alpha_0.05": False,
    }
    return results


def test_memo_does_not_claim_significance_when_ci_includes_zero():
    """
    Regression test: the memo previously stated "This interval does not
    include zero" unconditionally, regardless of whether the primary
    result was actually significant. When the CI includes zero, the memo
    must say so, not assert the opposite.
    """
    memo = reporting.build_memo(make_fake_results_not_significant())
    assert "does not include zero" not in memo
    assert "includes zero" in memo


def test_memo_claims_significance_only_when_true():
    memo = reporting.build_memo(make_fake_results())
    assert "does not include zero" in memo


def test_bottom_line_is_not_a_verbatim_repeat_of_the_recommendation():
    """
    Regression test: 'Bottom line' previously repeated the exact same
    sentence already shown under 'Recommendation', which added no
    information the second time. It should now give a distinct,
    forward-looking next step.
    """
    memo = reporting.build_memo(make_fake_results())
    _, verdict_text = reporting.recommendation(
        make_fake_results()["primary"], make_fake_results()["guardrail"]
    )
    bottom_line = memo.split("## Bottom line")[1].strip()
    assert bottom_line != verdict_text
