"""
Step 8: Streamlit dashboard.

Built on Streamlit's native theme (.streamlit/config.toml) so built-in
components (header, tabs, metric deltas, alert banners, expanders)
follow the theme automatically. Custom CSS here is limited to
typography: a display font for the masthead, monospace for small data
tags (chart annotations, metric labels/deltas), and justified body
text.

Verdict and headline metrics are visible immediately on load, no tab
click required. The "Preregistered Design" tab keeps only a compact
summary visible by default and tucks the full document into an
expander, so it isn't dramatically heavier than the other three tabs.
"""

import json
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent.parent / "assets"

st.set_page_config(
    page_title="Free Shipping Experiment: Preregistered A/B Test",
    page_icon=str(ASSETS / "favicon.png"),
    layout="wide",
)

# ---------------------------------------------------------------------------
# Typography. Colors, tabs, headers, and alerts come from
# .streamlit/config.toml, not from CSS overrides here.
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=Red+Hat+Mono:wght@400;500;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .masthead {
        text-align: center;
        padding-top: 0.6rem;
        margin-bottom: 1.6rem;
    }
    .masthead h1 {
        font-family: 'Source Serif 4', serif;
        font-weight: 700;
        font-size: 2.6rem;
        letter-spacing: -0.01em;
        color: #12192B;
        margin-bottom: 0.4rem;
    }
    .masthead .subtitle {
        color: #57617A;
        font-size: 1.02rem;
        width: 100%;
        line-height: 1.55;
        text-align: center;
    }

    .stMarkdown p, .stMarkdown li {
        text-align: justify;
        text-justify: inter-word;
    }

    /* tabs: stretch evenly across the full width instead of clumping left */
    [data-testid="stTabs"] [role="tablist"] {
        display: flex;
        width: 100%;
    }
    [data-testid="stTab"] {
        flex: 1;
        display: flex;
        justify-content: center;
    }

    /* small data tags: metric labels/deltas, mono throughout (title excluded) */
    [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {
        font-family: 'Red Hat Mono', monospace !important;
    }
    [data-testid="stMetricLabel"] p {
        font-family: 'Red Hat Mono', monospace !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.02em;
    }

    code {
        font-family: 'Red Hat Mono', monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

CHART_FONT = "Red Hat Mono"
INK = "#12192B"
GOOD = "#0E7C6B"
BAD = "#8C2F39"
NEUTRAL = "#8A94A8"
GRID = "#E1EAE7"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_json(path):
    return json.load(open(ROOT / path, encoding="utf-8"))


@st.cache_data
def load_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


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

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="masthead">
        <h1>Free Shipping &amp; Order Value</h1>
        <div class="subtitle">A preregistered, simulated A/B test. The design was
        committed to git before any experimental data existed.</div>
    </div>
    """,
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

    m1, m2, m3 = st.columns(3, gap="small")
    with m1, st.container(border=True):
        st.metric(
            "AOV LIFT",
            f"R$ {p['point_estimate_lift']:.2f}",
            delta="Significant" if significant else "Not significant",
            delta_color="normal" if significant else "inverse",
            help=(
                f"95% CI: `R$ {p['ci_95_low']:.2f}` to `R$ {p['ci_95_high']:.2f}`  \n"
                f"p = {p['p_value']:.2e} (Welch's t-test)"
            ),
        )
    with m2, st.container(border=True):
        st.metric(
            "GUARDRAIL (COMPLAINT RATE)",
            f"{g['point_estimate_diff']*100:+.2f}pp",
            delta="Within margin" if not breached else "Breached margin",
            delta_color="normal" if not breached else "inverse",
            help=(
                f"Non-inferiority margin: {g['non_inferiority_margin']*100:.1f}pp  \n"
                f"Control {g['control_complaint_rate']*100:.1f}% \u2192 "
                f"Treatment {g['treatment_complaint_rate']*100:.1f}%"
            ),
        )
    with m3, st.container(border=True):
        st.metric(
            "SAMPLE",
            f"{power['required_n_per_arm']:,} / arm",
            delta="Preregistered N",
            delta_color="off",
            help=f"{power['required_total_sellers']:,} sellers total, {power['power_target']*100:.0f}% target power",
        )

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
        "the exact files committed to git before any simulation code was written."
    )

    d1, d2, d3, d4, d5 = st.columns(5, gap="small")
    with d1, st.container(border=True):
        st.metric("PRIMARY MDE", f"R$ {power['primary']['mde_absolute_brl']:.0f}")
    with d2, st.container(border=True):
        st.metric("GUARDRAIL MARGIN", f"{power['guardrail']['non_inferiority_margin_absolute']*100:.1f}pp")
    with d3, st.container(border=True):
        st.metric("SELLERS/ARM", f"{power['required_n_per_arm']:,}")
    with d4, st.container(border=True):
        st.metric("TOTAL SELLERS", f"{power['required_total_sellers']:,}")
    with d5, st.container(border=True):
        st.metric("TARGET POWER", f"{power['power_target']*100:.0f}%")

    st.caption(
        f"Binding constraint: **{power['binding_constraint']}**. Real Olist sellers in "
        f"scope for comparison: {power['context_real_sellers_in_scope']:,}."
    )

    with st.expander("Read the full preregistration document"):
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
                marker_color=[NEUTRAL, GOOD],
                text=[f"R$ {p['control_mean_aov']:.2f}", f"R$ {p['treatment_mean_aov']:.2f}"],
                textposition="outside",
                textfont=dict(color=INK, family=CHART_FONT, size=13),
            ))
            fig.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Mean AOV (R$)",
                yaxis=dict(gridcolor=GRID),
                height=340, margin=dict(t=20, b=20, l=40, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Complaint rate by arm**")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker_color=[NEUTRAL, BAD if breach else GOOD],
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="#FFFFFF", family=CHART_FONT, size=13),
            ))
            ceiling_value = g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100
            fig2.add_hline(
                y=ceiling_value,
                line_dash="dash", line_color=BAD,
                annotation_text="non-inferiority ceiling",
                annotation_font=dict(color=BAD, family=CHART_FONT, size=11),
                annotation_position="top left",
            )
            max_bar = max(g["control_complaint_rate"], g["treatment_complaint_rate"]) * 100
            fig2.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Complaint rate (%)",
                yaxis=dict(gridcolor=GRID, range=[0, max(ceiling_value, max_bar) * 1.18]),
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
        p = results["primary"]
        g = results["guardrail"]
        verdict, reasoning = parse_verdict(memo_text)
        breach = g["guardrail_breached"]
        significant = p["significant_at_alpha_0.05"]
        n_total = p["n_treatment_sellers"] + p["n_control_sellers"]

        st.markdown(f"##### Recommendation: {verdict}")
        if verdict == "GO":
            st.success(reasoning)
        else:
            st.error(reasoning)

        st.markdown("##### What we tested")
        st.markdown(
            f"- Randomly split **{n_total:,} sellers** into two equal groups: standard "
            "shipping vs. free shipping\n"
            "- Measured whether free shipping changed **average order value**\n"
            "- Separately checked whether it made **delivery complaints** worse"
        )

        st.markdown("##### Results at a glance")
        c1, c2 = st.columns(2, gap="small")
        with c1, st.container(border=True):
            st.metric(
                "ORDER VALUE (TREATMENT)",
                f"R$ {p['treatment_mean_aov']:.2f}",
                delta=f"R$ {p['point_estimate_lift']:.2f} vs control",
                delta_color="normal" if significant else "off",
            )
            st.caption(
                f"Control: `R$ {p['control_mean_aov']:.2f}` \u00b7 "
                f"95% CI [`R$ {p['ci_95_low']:.2f}`, `R$ {p['ci_95_high']:.2f}`]"
            )
        with c2, st.container(border=True):
            st.metric(
                "COMPLAINT RATE (TREATMENT)",
                f"{g['treatment_complaint_rate']*100:.1f}%",
                delta=f"{g['point_estimate_diff']*100:+.2f}pp vs control",
                delta_color="inverse" if breach else "normal",
            )
            st.caption(
                f"Control: {g['control_complaint_rate']*100:.1f}% \u00b7 "
                f"Margin: {g['non_inferiority_margin']*100:.1f}pp"
            )

        st.markdown("##### Bottom line")
        if verdict == "GO":
            st.success(reasoning)
        else:
            st.error(reasoning)

        with st.expander("Read as a plain-text memo"):
            st.markdown(memo_text)