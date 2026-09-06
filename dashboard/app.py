"""
Step 8: Streamlit dashboard.

One page, four sections: preregistered design (read directly from
PREREGISTRATION.md and results/power_analysis.json so the dashboard
cannot drift from what was actually committed to git), simulated
results, ground-truth recovery, and the stakeholder memo.
"""

import json
import subprocess
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(
    page_title="Free Shipping Experiment — Preregistered A/B Test",
    page_icon="~",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --ink: #E7E9ED;
        --ink-dim: #98A1AF;
        --ink-faint: #5D6675;
        --paper: #12151B;
        --panel: #181C24;
        --line: #2A303C;
        --accent: #5FA8A0;
        --accent-dim: #3D6E68;
        --go: #7FB08A;
        --warn: #D98B6E;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: var(--paper);
    }

    h1, h2, h3 {
        font-family: 'Source Serif 4', serif;
        font-weight: 600;
        letter-spacing: -0.01em;
        color: var(--ink);
    }

    .registry-header {
        border-bottom: 1px solid var(--line);
        padding-bottom: 1.4rem;
        margin-bottom: 1.6rem;
    }
    .registry-title {
        font-family: 'Source Serif 4', serif;
        font-size: 2.1rem;
        font-weight: 600;
        color: var(--ink);
        margin-bottom: 0.2rem;
    }
    .registry-subtitle {
        color: var(--ink-dim);
        font-size: 0.98rem;
        max-width: 62ch;
        line-height: 1.5;
    }
    .commit-proof {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
        color: var(--accent);
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 3px;
        padding: 0.55rem 0.8rem;
        margin-top: 0.9rem;
        display: inline-block;
    }
    .commit-proof .label {
        color: var(--ink-faint);
        margin-right: 0.6rem;
    }

    .stat-row {
        display: flex;
        gap: 2.2rem;
        flex-wrap: wrap;
        margin: 1.2rem 0 1.6rem 0;
    }
    .stat {
        min-width: 150px;
    }
    .stat .num {
        font-family: 'Source Serif 4', serif;
        font-size: 2.0rem;
        font-weight: 600;
        color: var(--ink);
        line-height: 1.1;
    }
    .stat .num.accent { color: var(--accent); }
    .stat .num.go { color: var(--go); }
    .stat .num.warn { color: var(--warn); }
    .stat .lbl {
        font-size: 0.78rem;
        color: var(--ink-faint);
        margin-top: 0.25rem;
        letter-spacing: 0.01em;
    }

    .section-note {
        color: var(--ink-dim);
        font-size: 0.92rem;
        line-height: 1.6;
        max-width: 78ch;
        margin-bottom: 1rem;
    }

    .verdict-banner {
        border-left: 3px solid var(--go);
        background: rgba(127, 176, 138, 0.08);
        padding: 0.9rem 1.2rem;
        margin: 1rem 0 1.6rem 0;
        border-radius: 2px;
    }
    .verdict-banner.nogo {
        border-left-color: var(--warn);
        background: rgba(217, 139, 110, 0.08);
    }
    .verdict-banner .verdict-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--ink-faint);
        letter-spacing: 0.05em;
    }
    .verdict-banner .verdict-text {
        font-size: 1.05rem;
        color: var(--ink);
        margin-top: 0.3rem;
    }

    hr.divider {
        border: none;
        border-top: 1px solid var(--line);
        margin: 1.8rem 0;
    }

    [data-testid="stTabs"] button {
        font-family: 'Inter', sans-serif;
        font-size: 0.92rem;
    }

    .stMarkdown p, .stMarkdown li { color: var(--ink-dim); }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: var(--ink); }
    .stMarkdown strong { color: var(--ink); }
    .stMarkdown table { color: var(--ink-dim); }
    .stMarkdown code {
        font-family: 'IBM Plex Mono', monospace;
        background: var(--panel);
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
    <div class="registry-header">
        <div class="registry-title">Free Shipping &amp; Order Value</div>
        <div class="registry-subtitle">
            A preregistered, simulated A/B test. Design was committed to git
            before any experimental data existed — the log below is the proof.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
            <div class="stat"><div class="num">R$ {power['primary']['mde_absolute_brl']:.0f}</div><div class="lbl">PRIMARY MDE</div></div>
            <div class="stat"><div class="num">{power['guardrail']['non_inferiority_margin_absolute']*100:.1f}pp</div><div class="lbl">GUARDRAIL MARGIN</div></div>
            <div class="stat"><div class="num accent">{power['required_n_per_arm']:,}</div><div class="lbl">SELLERS PER ARM</div></div>
            <div class="stat"><div class="num">{power['required_total_sellers']:,}</div><div class="lbl">TOTAL SELLERS</div></div>
            <div class="stat"><div class="num">{power['power_target']*100:.0f}%</div><div class="lbl">TARGET POWER</div></div>
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
                <div class="stat"><div class="num go">R$ {p['point_estimate_lift']:.2f}</div><div class="lbl">AOV LIFT (POINT ESTIMATE)</div></div>
                <div class="stat"><div class="num">[{p['ci_95_low']:.2f}, {p['ci_95_high']:.2f}]</div><div class="lbl">95% CI (R$)</div></div>
                <div class="stat"><div class="num">{p['p_value']:.2e}</div><div class="lbl">P-VALUE (WELCH'S T)</div></div>
                <div class="stat"><div class="num {'warn' if g['guardrail_breached'] else ''}">{g['point_estimate_diff']*100:+.2f}pp</div><div class="lbl">COMPLAINT RATE DIFF</div></div>
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
                marker_color=["#5D6675", "#5FA8A0"],
                text=[f"R$ {p['control_mean_aov']:.2f}", f"R$ {p['treatment_mean_aov']:.2f}"],
                textposition="outside",
            ))
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="#181C24", paper_bgcolor="#181C24",
                font=dict(family="Inter", color="#E7E9ED"),
                yaxis_title="Mean AOV (R$)",
                height=340, margin=dict(t=20, b=20, l=40, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Complaint rate by arm**")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker_color=["#5D6675", "#D98B6E" if g["guardrail_breached"] else "#5FA8A0"],
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="outside",
            ))
            fig2.add_hline(
                y=g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100,
                line_dash="dash", line_color="#D98B6E",
                annotation_text="non-inferiority ceiling", annotation_font_color="#D98B6E",
            )
            fig2.update_layout(
                template="plotly_dark",
                plot_bgcolor="#181C24", paper_bgcolor="#181C24",
                font=dict(family="Inter", color="#E7E9ED"),
                yaxis_title="Complaint rate (%)",
                height=340, margin=dict(t=20, b=20, l=40, r=20),
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("<hr class='divider'/>", unsafe_allow_html=True)
        st.json(results, expanded=False)

with tab_recovery:
    if not has_results:
        st.info("Run `shipping-analyze` (or `python3 -m pipeline.analyze`) to populate this tab.")
    else:
        r = recovery
        both_ok = r["both_recovered"]
        st.markdown(
            f"""
            <div class="verdict-banner {'nogo' if not both_ok else ''}">
                <div class="verdict-label">GROUND-TRUTH RECOVERY CHECK</div>
                <div class="verdict-text">
                    {"Both intervals contain their true injected value." if both_ok else "At least one interval missed its true injected value — investigate before trusting this pipeline."}
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
            "value roughly 5% of the time even when the method is correct. This one seeded "
            "run passing is a smoke test that the pipeline isn't obviously broken — not proof "
            "the method generalizes to every real, unknown effect size. See README limitations.</div>",
            unsafe_allow_html=True,
        )

with tab_memo:
    if not has_results:
        st.info("Run `shipping-report` (or `python3 -m pipeline.reporting`) to populate this tab.")
    else:
        st.markdown(memo_text)
