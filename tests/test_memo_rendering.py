"""
Streamlit's markdown renderer treats paired, unescaped '$' characters as
inline LaTeX math. The memo template writes 'R$' several times in the
same paragraph, so every dollar sign must be escaped ('R\\$') or the
memo renders as broken math instead of currency in the dashboard. This
regression test would have caught that bug directly instead of only
being visible in a screenshot.
"""

import re

from pipeline import reporting


def make_fake_results():
    return {
        "primary": {
            "n_treatment_sellers": 2499,
            "n_control_sellers": 2499,
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


def test_memo_has_no_unescaped_dollar_signs():
    memo = reporting.build_memo(make_fake_results())
    for match in re.finditer(r"\$", memo):
        preceding_char = memo[match.start() - 1] if match.start() > 0 else ""
        assert preceding_char == "\\", (
            "Found an unescaped '$' in the memo, which Streamlit's markdown "
            "renderer will pair up and interpret as LaTeX math instead of "
            "currency: "
            + memo[max(0, match.start() - 20):match.start() + 20]
        )


def test_memo_still_contains_the_currency_values():
    memo = reporting.build_memo(make_fake_results())
    assert "171.13" in memo
    assert "31.59" in memo
    assert "R\\$" in memo
