"""
Step 8: Streamlit dashboard.

Built on top of Streamlit's native theme (.streamlit/config.toml) rather
than overriding component internals with hand-rolled CSS. The header
bar, tabs, metric deltas, and success/error banners all pick up the
theme automatically this way, and stay consistent across Streamlit
versions instead of breaking when internal class names change.

Layout: verdict banner and headline metrics are visible immediately, no
tab click required. The build-order proof is real but secondary
information, so it lives in a collapsed expander rather than competing
for attention at the top of the page. Tabs below hold the detail:
preregistered design, simulated results, ground-truth recovery, and the
stakeholder memo.
"""

import json
import re
import subprocess
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(
    page_title="Free Shipping Experiment: Preregistered A/B Test",
    page_icon="\u25c6",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Typography only. Colors, tabs, headers, and alerts come from
# .streamlit/config.toml, not from CSS overrides here.
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Source Serif 4', serif;
        font-weight: 600;
        letter-spacing: -0.01em;
    }
    .stMarkdown p, .stMarkdown li {
        text-align: justify;
        text-justify: inter-word;
    }
    .subtitle {
        color: #57617A;
        font-size: 0.98rem;
        max-width: 68ch;
        line-height: 1.55;
        margin-top: -0.6rem;
        margin-bottom: 1rem;
    }
    code {
        font-family: 'IBM Plex Mono', monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_json(path):
    return json.load(open(ROOT / path, encoding="utf-8"))


@st.cache_data
def load_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


EXPECTED_FIRST_COMMIT_SUBJECT = (
    "Preregister design: metric, MDE, power analysis, before any simulation code exists"
)


@st.cache_data
def get_commit_log():
    try:
        out = subprocess.run(
            ["git", "log", "--oneline", "--reverse"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def history_matches_expected_chain(commit_log):
    """
    A fresh `git init`, a GitHub "upload files" import, or copying the
    folder into an existing repo all silently discard the original
    history. Check the first commit's subject rather than trust
    whatever happens to be on disk.
    """
    if not commit_log:
        return False
    first_line = commit_log.split("\n")[0]
    first_subject = first_line.partition(" ")[2].strip()
    return first_subject == EXPECTED_FIRST_COMMIT_SUBJECT


def parse_verdict(memo_text):
    """
    Pulls the verdict straight out of the committed memo rather than
    recomputing go/no-go logic separately in the dashboard, so there is
    exactly one place that decision gets made.
    """
    match = re.search(
        r"## Recommendation: (GO|NO-GO)\s*\n+(.+?)(?:\n\n|\Z)",
        memo_text, re.DOTALL,
    )
    if not match:
        return None, None
    verdict = match.group(1)
    reasoning = " ".join(match.group(2).split())
    return verdict, reasoning


power = load_json("results/power_analysis.json")
prereg_text = load_text("PREREGISTRATION.md")

try:
    results = load_json("results/analysis_results.json")
    recovery = load_json("results/recovery_check.json")
    memo_text = load_text("results/memo.md")
    has_results = True
except FileNotFoundError:
    has_results = False

commit_log = get_commit_log()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Free Shipping & Order Value")
st.markdown(
    "<div class='subtitle'>A preregistered, simulated A/B test. The design was "
    "committed to git before any experimental data existed.</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Verdict: visible immediately, no tab click required
# ---------------------------------------------------------------------------

if not has_results:
    st.info("Run the pipeline (see README) to populate the verdict and results.")
else:
    p, g = results["primary"], results["guardrail"]
    verdict, reasoning = parse_verdict(memo_text)

    if verdict == "GO":
        st.success(f"**{verdict}.** {reasoning}")
    else:
        st.error(f"**{verdict or 'PENDING'}.** {reasoning or 'Run the analysis to see a recommendation.'}")

    significant = p["significant_at_alpha_0.05"]
    breached = g["guardrail_breached"]

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(
            "AOV lift",
            f"R$ {p['point_estimate_lift']:.2f}",
            delta="Significant" if significant else "Not significant",
            delta_color="normal" if significant else "inverse",
            help=(
                f"95% CI: R$ {p['ci_95_low']:.2f} to R$ {p['ci_95_high']:.2f}  \n"
                f"p = {p['p_value']:.2e} (Welch's t-test)"
            ),
        )
    with m2:
        st.metric(
            "Guardrail (complaint rate)",
            f"{g['point_estimate_diff']*100:+.2f}pp",
            delta="Within margin" if not breached else "Breached margin",
            delta_color="normal" if not breached else "inverse",
            help=(
                f"Non-inferiority margin: {g['non_inferiority_margin']*100:.1f}pp  \n"
                f"Control {g['control_complaint_rate']*100:.1f}% \u2192 "
                f"Treatment {g['treatment_complaint_rate']*100:.1f}%"
            ),
        )
    with m3:
        st.metric(
            "Sample",
            f"{power['required_n_per_arm']:,} / arm",
            delta="Preregistered N",
            delta_color="off",
            help=f"{power['required_total_sellers']:,} sellers total, {power['power_target']*100:.0f}% target power",
        )

with st.expander("Build-order proof (git commit history)"):
    if commit_log and history_matches_expected_chain(commit_log):
        lines = commit_log.split("\n")
        numbered = "\n".join(f"{i+1:02d}  {line}" for i, line in enumerate(lines))
        st.code(numbered, language=None)
        st.caption(
            "The first commit is this project's preregistration, committed before any "
            "simulation, randomization, or analysis code existed. See PREREGISTRATION.md "
            "for the design that commit locked in."
        )
    elif commit_log:
        st.warning(
            "This checkout's first commit is not this project's preregistration commit, "
            "so the build-order proof cannot be verified here. This usually happens when "
            "the repository was re-initialized, re-uploaded through a web UI, or copied "
            "into an existing repo, any of which silently discards the original history. "
            "Re-clone or re-extract the original project archive without modifying git "
            "history to see the real proof chain."
        )
        st.caption("This checkout's actual git history:")
        st.code(commit_log, language=None)
    else:
        st.caption("No git history found in this checkout.")

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_design, tab_results, tab_recovery, tab_memo = st.tabs(
    ["Preregistered Design", "Simulated Results", "Ground-Truth Recovery", "Stakeholder Memo"]
)

with tab_design:
    st.caption(
        "Pulled directly from `PREREGISTRATION.md` and `results/power_analysis.json`, "
        "the exact files committed to git before any simulation code was written. "
        "This tab cannot drift from the committed design because it reads no other source."
    )

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Primary MDE", f"R$ {power['primary']['mde_absolute_brl']:.0f}")
    d2.metric("Guardrail margin", f"{power['guardrail']['non_inferiority_margin_absolute']*100:.1f}pp")
    d3.metric("Sellers per arm", f"{power['required_n_per_arm']:,}")
    d4.metric("Total sellers", f"{power['required_total_sellers']:,}")
    d5.metric("Target power", f"{power['power_target']*100:.0f}%")

    st.caption(
        f"Binding constraint: **{power['binding_constraint']}**. Real Olist sellers in "
        f"scope for comparison: {power['context_real_sellers_in_scope']:,}."
    )

    st.divider()
    st.markdown(prereg_text)

with tab_results:
    if not has_results:
        st.info("Run `shipping-analyze` (or `python3 -m pipeline.analyze`) to populate this tab.")
    else:
        p = results["primary"]
        g = results["guardrail"]
        breach = g["guardrail_breached"]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Order value by arm**")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[p["control_mean_aov"], p["treatment_mean_aov"]],
                marker_color=["#8A94A8", "#0B6E5E"],
                text=[f"R$ {p['control_mean_aov']:.2f}", f"R$ {p['treatment_mean_aov']:.2f}"],
                textposition="outside",
                textfont=dict(color="#12192B"),
            ))
            fig.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font=dict(family="Inter", color="#12192B"),
                yaxis_title="Mean AOV (R$)",
                yaxis=dict(gridcolor="#E7EBF2"),
                height=340, margin=dict(t=20, b=20, l=40, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Complaint rate by arm**")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker_color=["#8A94A8", "#8C2F39" if breach else "#0B6E5E"],
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="#FFFFFF", size=13),
            ))
            ceiling_value = g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100
            fig2.add_hline(
                y=ceiling_value,
                line_dash="dash", line_color="#8C2F39",
                annotation_text="non-inferiority ceiling",
                annotation_font_color="#8C2F39",
                annotation_position="top left",
            )
            max_bar = max(g["control_complaint_rate"], g["treatment_complaint_rate"]) * 100
            fig2.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font=dict(family="Inter", color="#12192B"),
                yaxis_title="Complaint rate (%)",
                yaxis=dict(gridcolor="#E7EBF2", range=[0, max(ceiling_value, max_bar) * 1.18]),
                height=340, margin=dict(t=40, b=20, l=40, r=20),
            )
            st.plotly_chart(fig2, use_container_width=True)

        with st.expander("View raw analysis output (JSON)"):
            st.json(results, expanded=True)

with tab_recovery:
    if not has_results:
        st.info("Run `shipping-analyze` (or `python3 -m pipeline.analyze`) to populate this tab.")
    else:
        r = recovery
        both_ok = r["both_recovered"]

        if both_ok:
            st.success("Both intervals contain their true injected value.")
        else:
            st.error("At least one interval missed its true injected value. Take a closer look before trusting this run.")

        rec_df = pd.DataFrame([
            {
                "Metric": "AOV lift (R$)",
                "True value": r["true_aov_lift"],
                "CI low": r["primary_ci"][0],
                "CI high": r["primary_ci"][1],
                "Recovered": "Yes" if r["primary_recovered"] else "No",
            },
            {
                "Metric": "Complaint rate diff",
                "True value": r["true_complaint_lift"],
                "CI low": r["guardrail_ci"][0],
                "CI high": r["guardrail_ci"][1],
                "Recovered": "Yes" if r["guardrail_recovered"] else "No",
            },
        ])
        st.dataframe(rec_df, use_container_width=True, hide_index=True)

        st.caption(
            "A confidence interval is expected to miss the true value roughly 5% of the "
            "time even when the method is correct. One seeded run passing is a smoke test "
            "that the pipeline is not obviously broken, not proof the method generalizes "
            "to every real, unknown effect size. See README limitations."
        )

with tab_memo:
    if not has_results:
        st.info("Run `shipping-report` (or `python3 -m pipeline.reporting`) to populate this tab.")
    else:
        st.markdown(memo_text)
