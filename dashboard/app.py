"""
Step 8: Streamlit dashboard.

A persistent verdict banner sits above the tabs so the go/no-go call is
visible no matter which tab is open. Below it: preregistered design (read
directly from PREREGISTRATION.md and results/power_analysis.json so the
dashboard cannot drift from what was actually committed to git), simulated
results, ground-truth recovery, and the stakeholder memo.
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
# Style
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --bg: #EEF2F7;
        --panel: #FFFFFF;
        --panel-alt: #F5F8FB;
        --border: #DBE2EC;
        --ink: #12192B;
        --ink-dim: #57617A;
        --ink-faint: #8892A6;
        --accent: #0B6E5E;
        --accent-soft: rgba(11, 110, 94, 0.09);
        --accent-line: rgba(11, 110, 94, 0.35);
        --warn: #8C2F39;
        --warn-soft: rgba(140, 47, 57, 0.08);
        --warn-line: rgba(140, 47, 57, 0.35);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: var(--bg);
    }

    h1, h2, h3 {
        font-family: 'Source Serif 4', serif;
        font-weight: 600;
        letter-spacing: -0.01em;
        color: var(--ink);
    }

    .page-header {
        border-bottom: 1px solid var(--border);
        padding-bottom: 1.2rem;
        margin-bottom: 1.1rem;
    }
    .page-title {
        font-family: 'Source Serif 4', serif;
        font-size: 2.15rem;
        font-weight: 600;
        color: var(--ink);
        margin-bottom: 0.3rem;
    }
    .page-subtitle {
        color: var(--ink-dim);
        font-size: 0.98rem;
        max-width: 68ch;
        line-height: 1.55;
        text-align: justify;
        text-justify: inter-word;
    }

    /* persistent verdict banner, visible above every tab */
    .verdict-hero {
        background: var(--accent-soft);
        border: 1px solid var(--accent-line);
        border-radius: 10px;
        padding: 1.05rem 1.4rem;
        margin: 1.1rem 0 1.3rem 0;
        display: flex;
        align-items: center;
        gap: 1.3rem;
        flex-wrap: wrap;
    }
    .verdict-hero.nogo {
        background: var(--warn-soft);
        border-color: var(--warn-line);
    }
    .verdict-pill {
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        font-size: 0.92rem;
        letter-spacing: 0.04em;
        padding: 0.4rem 1.0rem;
        border-radius: 999px;
        color: #FFFFFF;
        background: var(--accent);
        white-space: nowrap;
    }
    .verdict-pill.nogo { background: var(--warn); }
    .verdict-hero-text {
        color: var(--ink);
        font-size: 1.0rem;
        line-height: 1.5;
        flex: 1;
        min-width: 260px;
        text-align: justify;
        text-justify: inter-word;
    }
    .verdict-hero-figures {
        display: flex;
        gap: 1.6rem;
        flex-wrap: wrap;
    }
    .verdict-figure .num {
        font-family: 'Source Serif 4', serif;
        font-size: 1.35rem;
        font-weight: 600;
        color: var(--ink);
        line-height: 1.1;
    }
    .verdict-figure .lbl {
        font-size: 0.68rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--ink-faint);
        margin-top: 0.2rem;
    }

    .commit-proof {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: var(--ink-dim);
        background: var(--panel-alt);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0.6rem 0.9rem;
        margin-top: 0.2rem;
        display: inline-block;
    }
    .commit-proof .label {
        color: var(--accent);
        font-weight: 600;
        margin-right: 0.6rem;
    }

    .stat-row {
        display: flex;
        gap: 0.9rem;
        flex-wrap: wrap;
        margin: 1.0rem 0 1.5rem 0;
    }
    .stat-card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 9px;
        padding: 0.95rem 1.15rem;
        min-width: 148px;
    }
    .stat-card .num {
        font-family: 'Source Serif 4', serif;
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--ink);
        line-height: 1.15;
    }
    .stat-card .num.accent { color: var(--accent); }
    .stat-card .num.warn { color: var(--warn); }
    .stat-card .lbl {
        font-size: 0.68rem;
        color: var(--ink-faint);
        margin-top: 0.3rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .section-note {
        color: var(--ink-dim);
        font-size: 0.93rem;
        line-height: 1.6;
        max-width: 80ch;
        margin-bottom: 1rem;
        text-align: justify;
        text-justify: inter-word;
    }

    .check-banner {
        border: 1px solid var(--accent-line);
        background: var(--accent-soft);
        padding: 0.85rem 1.15rem;
        margin: 0.4rem 0 1.5rem 0;
        border-radius: 8px;
    }
    .check-banner.nogo {
        border-color: var(--warn-line);
        background: var(--warn-soft);
    }
    .check-banner .check-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: var(--ink-faint);
        letter-spacing: 0.05em;
    }
    .check-banner .check-text {
        font-size: 1.0rem;
        color: var(--ink);
        margin-top: 0.3rem;
    }

    hr.divider {
        border: none;
        border-top: 1px solid var(--border);
        margin: 1.7rem 0;
    }

    [data-testid="stTabs"] button {
        font-family: 'Inter', sans-serif;
        font-size: 0.92rem;
        color: var(--ink-dim);
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--accent);
    }

    .stMarkdown p, .stMarkdown li {
        color: var(--ink-dim);
        text-align: justify;
        text-justify: inter-word;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: var(--ink); }
    .stMarkdown strong { color: var(--ink); }
    .stMarkdown table { color: var(--ink-dim); }
    .stMarkdown code {
        font-family: 'IBM Plex Mono', monospace;
        background: var(--panel-alt);
        color: var(--accent);
        padding: 0.1rem 0.35rem;
        border-radius: 3px;
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
    return json.load(open(ROOT / path))


@st.cache_data
def load_text(path):
    return (ROOT / path).read_text()


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

st.markdown(
    """
    <div class="page-header">
        <div class="page-title">Free Shipping &amp; Order Value</div>
        <div class="page-subtitle">
            A preregistered, simulated A/B test. The design was committed to
            git before any experimental data existed, and the log below is
            the proof.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if has_results:
    verdict, reasoning = parse_verdict(memo_text)
    p, g = results["primary"], results["guardrail"]
    nogo_class = "nogo" if verdict == "NO-GO" else ""
    guardrail_status = "Breached" if g["guardrail_breached"] else "Within margin"
    st.markdown(
        f"""
        <div class="verdict-hero {nogo_class}">
            <div class="verdict-pill {nogo_class}">{verdict or "PENDING"}</div>
            <div class="verdict-hero-text">{reasoning or "Run the analysis to see a recommendation."}</div>
            <div class="verdict-hero-figures">
                <div class="verdict-figure">
                    <div class="num">R$ {p['point_estimate_lift']:.2f}</div>
                    <div class="lbl">AOV lift</div>
                </div>
                <div class="verdict-figure">
                    <div class="num">{g['point_estimate_diff']*100:+.2f}pp</div>
                    <div class="lbl">Complaint diff</div>
                </div>
                <div class="verdict-figure">
                    <div class="num">{guardrail_status}</div>
                    <div class="lbl">Guardrail</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("Run the pipeline (see README) to populate the verdict and results.")

if commit_log:
    lines = commit_log.split("\n")
    proof_html = "<div class='commit-proof'>"
    for i, line in enumerate(lines):
        sha, _, msg = line.partition(" ")
        proof_html += f"<span class='label'>{i+1:02d}</span>{sha} {msg}<br/>" if i < len(lines) - 1 else f"<span class='label'>{i+1:02d}</span>{sha} {msg}"
    proof_html += "</div>"
    st.markdown(proof_html, unsafe_allow_html=True)

st.markdown("<hr class='divider'/>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_design, tab_results, tab_recovery, tab_memo = st.tabs(
    ["Preregistered Design", "Simulated Results", "Ground-Truth Recovery", "Stakeholder Memo"]
)

with tab_design:
    st.markdown(
        "<div class='section-note'>Pulled directly from "
        "<code>PREREGISTRATION.md</code> and <code>results/power_analysis.json</code>, "
        "the exact files committed to git before any simulation code was written. "
        "This tab cannot drift from the committed design because it reads no other source.</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-card"><div class="num">R$ {power['primary']['mde_absolute_brl']:.0f}</div><div class="lbl">Primary MDE</div></div>
            <div class="stat-card"><div class="num">{power['guardrail']['non_inferiority_margin_absolute']*100:.1f}pp</div><div class="lbl">Guardrail margin</div></div>
            <div class="stat-card"><div class="num accent">{power['required_n_per_arm']:,}</div><div class="lbl">Sellers per arm</div></div>
            <div class="stat-card"><div class="num">{power['required_total_sellers']:,}</div><div class="lbl">Total sellers</div></div>
            <div class="stat-card"><div class="num">{power['power_target']*100:.0f}%</div><div class="lbl">Target power</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"*Binding constraint: **{power['binding_constraint']}***. "
                f"Real Olist sellers in scope for comparison: {power['context_real_sellers_in_scope']:,}.")

    st.markdown("<hr class='divider'/>", unsafe_allow_html=True)
    st.markdown(prereg_text)

with tab_results:
    if not has_results:
        st.info("Run `shipping-analyze` (or `python3 -m pipeline.analyze`) to populate this tab.")
    else:
        p = results["primary"]
        g = results["guardrail"]

        st.markdown(
            f"""
            <div class="stat-row">
                <div class="stat-card"><div class="num accent">R$ {p['point_estimate_lift']:.2f}</div><div class="lbl">AOV lift (point estimate)</div></div>
                <div class="stat-card"><div class="num">[{p['ci_95_low']:.2f}, {p['ci_95_high']:.2f}]</div><div class="lbl">95% CI (R$)</div></div>
                <div class="stat-card"><div class="num">{p['p_value']:.2e}</div><div class="lbl">P value (Welch's t)</div></div>
                <div class="stat-card"><div class="num {'warn' if g['guardrail_breached'] else ''}">{g['point_estimate_diff']*100:+.2f}pp</div><div class="lbl">Complaint rate diff</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
            breach = g["guardrail_breached"]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker_color=["#8A94A8", "#8C2F39" if breach else "#0B6E5E"],
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="outside",
                textfont=dict(color="#12192B"),
            ))
            fig2.add_hline(
                y=g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100,
                line_dash="dash", line_color="#8C2F39",
                annotation_text="non-inferiority ceiling",
                annotation_font_color="#8C2F39",
                annotation_position="top left",
            )
            fig2.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                font=dict(family="Inter", color="#12192B"),
                yaxis_title="Complaint rate (%)",
                yaxis=dict(gridcolor="#E7EBF2"),
                height=340, margin=dict(t=40, b=20, l=40, r=20),
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("<hr class='divider'/>", unsafe_allow_html=True)
        with st.expander("View raw analysis output (JSON)"):
            st.json(results, expanded=True)

with tab_recovery:
    if not has_results:
        st.info("Run `shipping-analyze` (or `python3 -m pipeline.analyze`) to populate this tab.")
    else:
        r = recovery
        both_ok = r["both_recovered"]
        st.markdown(
            f"""
            <div class="check-banner {'nogo' if not both_ok else ''}">
                <div class="check-label">GROUND-TRUTH RECOVERY CHECK</div>
                <div class="check-text">
                    {"Both intervals contain their true injected value." if both_ok else "At least one interval missed its true injected value. Take a closer look before trusting this run."}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

        st.markdown(
            "<div class='section-note'>A confidence interval is expected to miss the true "
            "value roughly 5% of the time even when the method is correct. One seeded run "
            "passing is a smoke test that the pipeline is not obviously broken, not proof "
            "the method generalizes to every real, unknown effect size. See README limitations.</div>",
            unsafe_allow_html=True,
        )

with tab_memo:
    if not has_results:
        st.info("Run `shipping-report` (or `python3 -m pipeline.reporting`) to populate this tab.")
    else:
        st.markdown(memo_text)
