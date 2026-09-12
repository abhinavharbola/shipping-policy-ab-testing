"""
Step 8: Streamlit dashboard.

Design system
--------------
Palette (see COLORS below): a cool paper background and near-navy ink,
carrying the report's actual verdict colors - teal for a cleared bar,
amber for a guardrail that held but is worth watching, brick for a
breach or a non-significant result. Nothing here is a generic SaaS
palette; it is the same three-color logic the guardrail chart already
needs (clear / caution / breach), reused everywhere so color always
means the same thing.

Type: Source Serif 4 for the verdict and section headings (this is a
report, not a form), Inter for body and UI copy, and Red Hat Mono
reserved strictly for numeric data - statistics, confidence intervals,
seeds - never for labels. Labels are sentence case throughout; the
previous version put small-caps-style labels in monospace, which reads
as decoration rather than data.

Layout: a persistent sidebar holds the study snapshot and the build-order
rail (calibrate -> preregister -> simulate -> randomize -> analyze ->
report), so the reader always knows which stage of the pipeline produced
what they're looking at, independent of which tab is open. The main
canvas leads with one hero panel - verdict, reasoning, and the three
headline numbers - then four tabs for progressive depth. Metric detail
that used to live in a hover tooltip is now always-visible small print
under each number, since a hover state doesn't survive a screenshot and
this project is meant to be read as a static report as often as it is
clicked through live.

The verdict shown here is computed by calling `experiment.reporting`'s
`recommendation()` directly on the already-computed analysis output, not
by re-parsing the rendered memo.md text. That keeps "exactly one place
the decision gets made" true without depending on the memo's markdown
formatting staying byte-for-byte stable.

Formatting conventions kept consistent throughout: currency (R$) always
shows 2 decimal places; percentages and percentage-point deltas always
show 1. Currency figures inside markdown are wrapped in backtick code
spans so Streamlit's markdown renderer doesn't pair the dollar signs up
as inline LaTeX math (see tests/test_memo_rendering.py).
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FAVICON_PATH = ASSETS / "favicon.png"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.reporting import next_step, recommendation  # noqa: E402

PAGE_ICON = str(FAVICON_PATH) if FAVICON_PATH.is_file() else "\U0001F7E2"

st.set_page_config(
    page_title="Free Shipping Experiment: Preregistered A/B Test",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

PAPER = "#F5F7F6"
PANEL = "#FFFFFF"
INK = "#12192B"
INK_SOFT = "#5B6474"
HAIRLINE = "#DCE4E1"
TEAL = "#0E7C6B"
TEAL_SOFT = "#E4F1EE"
AMBER = "#96690F"
AMBER_SOFT = "#F6ECDA"
BRICK = "#8C2F39"
BRICK_SOFT = "#F5E4E5"
SLATE = "#8A94A8"

DISPLAY_FONT = "'Source Serif 4', Georgia, serif"
BODY_FONT = "'Inter', -apple-system, sans-serif"
DATA_FONT = "'Red Hat Mono', 'SFMono-Regular', monospace"

CHART_FONT = "Red Hat Mono"

# ---------------------------------------------------------------------------
# Global styles
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Red+Hat+Mono:wght@400;500;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: {BODY_FONT};
        color: {INK};
    }}

    [data-testid="stAppViewContainer"] {{
        background-color: {PAPER};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {PANEL};
        border-right: 1px solid {HAIRLINE};
    }}

    .block-container {{
        padding-top: 2.2rem;
        max-width: 1180px;
    }}

    h1, h2, h3, h4 {{
        font-family: {DISPLAY_FONT};
        color: {INK};
    }}

    code {{ font-family: {DATA_FONT}; }}

    /* ---- masthead ---- */
    .masthead {{
        margin-bottom: 1.6rem;
    }}
    .masthead h1 {{
        font-weight: 600;
        font-size: 2.1rem;
        letter-spacing: -0.01em;
        margin: 0 0 0.35rem 0;
        line-height: 1.15;
    }}
    .masthead .subtitle {{
        color: {INK_SOFT};
        font-size: 0.98rem;
        line-height: 1.55;
        max-width: 62ch;
    }}

    /* ---- hero verdict panel ---- */
    .hero {{
        background: {PANEL};
        border: 1px solid {HAIRLINE};
        border-left: 5px solid var(--hero-accent, {SLATE});
        border-radius: 3px;
        padding: 1.5rem 1.7rem 0.2rem 1.7rem;
        margin-bottom: 1.4rem;
    }}
    .hero-top {{
        display: flex;
        align-items: baseline;
        gap: 0.7rem;
        flex-wrap: wrap;
        margin-bottom: 0.4rem;
    }}
    .hero-verdict {{
        font-family: {DISPLAY_FONT};
        font-weight: 600;
        font-size: 1.9rem;
        color: var(--hero-accent, {INK});
        letter-spacing: -0.01em;
    }}
    .hero-reasoning {{
        color: {INK};
        font-size: 1rem;
        line-height: 1.6;
        max-width: 72ch;
        margin-bottom: 0.9rem;
    }}
    .hero-meta {{
        color: {INK_SOFT};
        font-size: 0.82rem;
        margin-bottom: 1.1rem;
        font-family: {DATA_FONT};
    }}

    /* ---- reusable stat row ---- */
    .stat-row {{
        display: flex;
        border-top: 1px solid {HAIRLINE};
    }}
    .stat-cell {{
        flex: 1;
        padding: 0.95rem 1.2rem 1.05rem 0;
        border-right: 1px solid {HAIRLINE};
    }}
    .stat-cell:first-child {{ padding-left: 0; }}
    .stat-cell:last-child {{ border-right: none; }}
    .stat-label {{
        font-size: 0.82rem;
        color: {INK_SOFT};
        margin-bottom: 0.3rem;
    }}
    .stat-value {{
        font-family: {DATA_FONT};
        font-size: 1.5rem;
        font-weight: 500;
        color: {INK};
        line-height: 1.2;
    }}
    .stat-value.good {{ color: {TEAL}; }}
    .stat-value.caution {{ color: {AMBER}; }}
    .stat-value.bad {{ color: {BRICK}; }}
    .stat-note {{
        font-family: {DATA_FONT};
        font-size: 0.78rem;
        color: {INK_SOFT};
        margin-top: 0.35rem;
        line-height: 1.5;
    }}
    .stat-row.compact .stat-cell {{ padding-top: 0.7rem; padding-bottom: 0.7rem; }}
    .stat-row.compact .stat-value {{ font-size: 1.15rem; }}

    /* ---- status pill ---- */
    .pill {{
        display: inline-block;
        font-size: 0.76rem;
        padding: 0.15rem 0.55rem;
        border-radius: 3px;
        font-family: {DATA_FONT};
    }}
    .pill.good {{ background: {TEAL_SOFT}; color: {TEAL}; }}
    .pill.caution {{ background: {AMBER_SOFT}; color: {AMBER}; }}
    .pill.bad {{ background: {BRICK_SOFT}; color: {BRICK}; }}
    .pill.neutral {{ background: #EEF1F0; color: {INK_SOFT}; }}

    /* ---- sidebar: study snapshot ---- */
    .snapshot-title {{
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {INK_SOFT};
        margin: 1.1rem 0 0.6rem 0;
        font-weight: 600;
    }}
    .snapshot-row {{
        font-size: 0.86rem;
        line-height: 1.7;
        color: {INK};
    }}
    .snapshot-row .k {{ color: {INK_SOFT}; }}

    /* ---- sidebar: build-order rail ---- */
    .rail {{ margin: 0.3rem 0 0.2rem 0; }}
    .rail-step {{
        display: flex;
        gap: 0.65rem;
        position: relative;
        padding-bottom: 1.05rem;
    }}
    .rail-step:last-child {{ padding-bottom: 0; }}
    .rail-line {{
        position: absolute;
        left: 5px;
        top: 16px;
        bottom: -2px;
        width: 1px;
        background: {HAIRLINE};
    }}
    .rail-step:last-child .rail-line {{ display: none; }}
    .rail-dot {{
        flex-shrink: 0;
        width: 11px;
        height: 11px;
        border-radius: 50%;
        margin-top: 3px;
        border: 1.5px solid {HAIRLINE};
        background: {PANEL};
        z-index: 1;
    }}
    .rail-dot.done {{ background: {TEAL}; border-color: {TEAL}; }}
    .rail-dot.locked {{
        background: repeating-linear-gradient(45deg, {INK_SOFT}, {INK_SOFT} 2px, {PANEL} 2px, {PANEL} 4px);
        border-color: {INK_SOFT};
    }}
    .rail-label {{ font-size: 0.86rem; color: {INK}; line-height: 1.3; }}
    .rail-label .sub {{ display: block; font-size: 0.74rem; color: {INK_SOFT}; margin-top: 0.1rem; }}

    /* ---- tabs: understated underline nav, not the default pill chrome ---- */
    [data-testid="stTabs"] [role="tablist"] {{
        gap: 1.6rem;
        border-bottom: 1px solid {HAIRLINE};
    }}
    [data-testid="stTabs"] button {{
        font-family: {BODY_FONT};
        font-size: 0.92rem;
        padding: 0 0 0.6rem 0;
    }}
    [data-testid="stTabs"] [aria-selected="true"] {{
        color: {INK};
        font-weight: 600;
    }}

    .stMarkdown p, .stMarkdown li {{ line-height: 1.6; }}

    /* ---- footer ---- */
    .app-footer {{
        margin-top: 2.4rem;
        padding-top: 1rem;
        border-top: 1px solid {HAIRLINE};
        color: {INK_SOFT};
        font-size: 0.8rem;
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.4rem;
    }}
    .app-footer a {{ color: {INK_SOFT}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def stat_row(stats, compact=False):
    """Render a row of statistics as hairline-divided columns, sharing one
    typographic treatment across every tab instead of repeating Streamlit's
    default bordered-card-per-metric pattern."""
    cells = []
    for s in stats:
        value_class = f"stat-value {s.get('tone', '')}".strip()
        note = s.get("note", "")
        cells.append(
            f"""<div class="stat-cell">
                <div class="stat-label">{s['label']}</div>
                <div class="{value_class}">{s['value']}</div>
                <div class="stat-note">{note}</div>
            </div>"""
        )
    row_class = "stat-row compact" if compact else "stat-row"
    st.markdown(f'<div class="{row_class}">{"".join(cells)}</div>', unsafe_allow_html=True)


def pill(text, tone="neutral"):
    return f'<span class="pill {tone}">{text}</span>'


# ---------------------------------------------------------------------------
# Data loading - reads each pipeline artifact independently, so the sidebar
# rail can reflect exactly which stages have actually produced output rather
# than a single all-or-nothing flag.
# ---------------------------------------------------------------------------

@st.cache_data
def load_json(path):
    return json.load(open(ROOT / path, encoding="utf-8"))


@st.cache_data
def load_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def exists(path):
    return (ROOT / path).is_file()


calib_done = exists("data/calibration/calibration_params.json")
power_done = exists("results/power_analysis.json")
simulate_done = exists("data/simulated/population_potential_outcomes.csv")
randomize_done = exists("data/simulated/assigned_experiment.csv")
analyze_done = exists("results/analysis_results.json")
report_done = exists("results/memo.md")

prereg_text = load_text("PREREGISTRATION.md") if exists("PREREGISTRATION.md") else None
power = load_json("results/power_analysis.json") if power_done else None

has_results = analyze_done and report_done
if has_results:
    results = load_json("results/analysis_results.json")
    recovery = load_json("results/recovery_check.json") if exists("results/recovery_check.json") else None
    memo_text = load_text("results/memo.md")
true_effects = load_json("data/simulated/true_effects.json") if exists("data/simulated/true_effects.json") else None

# ---------------------------------------------------------------------------
# Sidebar: study snapshot + build-order rail, visible regardless of tab
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:0.55rem; margin-bottom:0.2rem;">
            <div style="font-family:'Source Serif 4',serif; font-weight:600; font-size:1.05rem;">
                Free Shipping Experiment
            </div>
        </div>
        <div style="color:#5B6474; font-size:0.82rem; margin-bottom:0.4rem;">
            Preregistered, simulated A/B test
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="snapshot-title">Study snapshot</div>', unsafe_allow_html=True)
    if power:
        snapshot_html = f"""
        <div class="snapshot-row"><span class="k">Hypothesis</span><br>
        Free shipping raises AOV without a meaningful complaint-rate rise</div>
        <div class="snapshot-row" style="margin-top:0.5rem;">
        <span class="k">Randomized on</span> seller, not order<br>
        <span class="k">Primary MDE</span> R$ {power['primary']['mde_absolute_brl']:.0f}<br>
        <span class="k">Guardrail margin</span> {power['guardrail']['non_inferiority_margin_absolute']*100:.1f}pp<br>
        <span class="k">Required N/arm</span> {power['required_n_per_arm']:,}
        </div>
        """
        st.markdown(snapshot_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="snapshot-row">Run power analysis to populate this snapshot.</div>',
            unsafe_allow_html=True,
        )

    if has_results:
        p, g = results["primary"], results["guardrail"]
        verdict, _ = recommendation(p, g)
        tone = "good" if verdict == "GO" else "bad"
        st.markdown(
            f'<div style="margin-top:0.7rem;">{pill(verdict, tone)}</div>',
            unsafe_allow_html=True,
        )
    if true_effects:
        st.markdown(
            f'<div class="stat-note" style="margin-top:0.6rem;">'
            f'Simulated population - seed {true_effects["seed"]}, '
            f'{true_effects["n_sellers"]:,} sellers</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="snapshot-title">Build order</div>', unsafe_allow_html=True)

    def rail_step(label, done, sub=None, locked=False):
        dot_class = "locked" if locked else ("done" if done else "")
        sub_html = f'<span class="sub">{sub}</span>' if sub else ""
        return f"""<div class="rail-step">
            <div class="rail-line"></div>
            <div class="rail-dot {dot_class}"></div>
            <div class="rail-label">{label}{sub_html}</div>
        </div>"""

    rail_html = '<div class="rail">' + "".join([
        rail_step("Calibrate", calib_done, "descriptive stats from real Olist orders"),
        rail_step("Preregister", True, "metric, MDE, tests - locked to git", locked=True),
        rail_step("Simulate", simulate_done, "inject known effect, potential outcomes"),
        rail_step("Randomize", randomize_done, "reveal one arm per seller"),
        rail_step("Analyze", analyze_done, "preregistered tests, run once"),
        rail_step("Report", report_done, "memo + this dashboard"),
    ]) + "</div>"
    st.markdown(rail_html, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="app-footer" style="display:block; margin-top:1.6rem;">
        <a href="https://github.com/abhinavharbola/shipping-policy-ab-testing" target="_blank">Repository</a><br>
        <a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce" target="_blank">Olist dataset</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main canvas: masthead
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="masthead">
        <h1>Free Shipping &amp; Order Value</h1>
        <div class="subtitle">Does offering free shipping raise average order value
        without meaningfully increasing delivery complaints? The metric, sample
        size, and tests below were committed to git before any experimental
        data existed - see the build order in the sidebar.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero: verdict + headline numbers, always visible, no tab click required
# ---------------------------------------------------------------------------

if not power:
    st.info(
        "Run the pipeline (see README) to compute the required sample size and "
        "populate this dashboard. Nothing below can be shown until "
        "`results/power_analysis.json` exists."
    )
elif not has_results:
    st.markdown(
        f"""
        <div class="hero" style="--hero-accent: {SLATE};">
            <div class="hero-top"><span class="hero-verdict" style="font-size:1.3rem;">Design locked, awaiting data</span></div>
            <div class="hero-reasoning">The preregistered design requires
            {power['required_n_per_arm']:,} sellers per arm
            ({power['required_total_sellers']:,} total). Run
            <code>shipping-simulate</code>, <code>shipping-randomize</code>, and
            <code>shipping-analyze</code> (or <code>scripts/run_pipeline.py</code>)
            to populate the verdict and results below.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    p, g = results["primary"], results["guardrail"]
    verdict, reasoning = recommendation(p, g)
    significant = p["significant_at_alpha_0.05"]
    breached = g["guardrail_breached"]
    margin = g["non_inferiority_margin"]
    diff = g["point_estimate_diff"]

    accent = TEAL if verdict == "GO" else BRICK

    # Guardrail nuance beyond the binary breach/no-breach call: flag when the
    # observed gap is closing in on the margin even though it hasn't crossed
    # it, so a stakeholder gets an early warning rather than a false all-clear.
    # This is a presentation-layer read, not a change to the preregistered
    # breach decision itself, which is made in analyze.py and untouched here.
    if breached:
        guardrail_tone, guardrail_label = "bad", "Breached margin"
    elif diff > 0.75 * margin:
        guardrail_tone, guardrail_label = "caution", "Within margin, watch closely"
    else:
        guardrail_tone, guardrail_label = "good", "Within margin"

    n_total = p["n_treatment_sellers"] + p["n_control_sellers"]
    seed_note = f"seed {true_effects['seed']}" if true_effects else ""

    st.markdown(
        f"""
        <div class="hero" style="--hero-accent: {accent};">
            <div class="hero-top">
                <span class="hero-verdict">{verdict}</span>
            </div>
            <div class="hero-reasoning">{reasoning}</div>
            <div class="hero-meta">{n_total:,} sellers analyzed · Welch's t-test + one-sided
            non-inferiority z-test · alpha 0.05{" · " + seed_note if seed_note else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    stat_row([
        {
            "label": "AOV lift",
            "value": f"R$ {p['point_estimate_lift']:.2f}",
            "tone": "good" if significant and p["point_estimate_lift"] > 0 else ("bad" if significant else ""),
            "note": (
                f"95% CI R$ {p['ci_95_low']:.2f} to R$ {p['ci_95_high']:.2f} · "
                f"{'significant' if significant else 'not significant'} at p = {p['p_value']:.1e}"
            ),
        },
        {
            "label": "Complaint-rate guardrail",
            "value": f"{diff*100:+.1f}pp",
            "tone": guardrail_tone,
            "note": f"{guardrail_label} · non-inferiority margin {margin*100:.1f}pp",
        },
        {
            "label": "Sample size",
            "value": f"{power['required_n_per_arm']:,} / arm",
            "note": f"{power['required_total_sellers']:,} sellers total · preregistered, {power['power_target']*100:.0f}% power",
        },
    ])

st.write("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_design, tab_results, tab_recovery, tab_memo = st.tabs(
    ["Design", "Results", "Recovery check", "Memo"]
)

with tab_design:
    if not power:
        st.info("Run `shipping-power` (or `python3 -m design.power_analysis`) to populate this tab.")
    else:
        st.caption(
            "Pulled directly from PREREGISTRATION.md and results/power_analysis.json, "
            "the exact files committed to git before any simulation code was written."
        )
        stat_row([
            {"label": "Primary MDE", "value": f"R$ {power['primary']['mde_absolute_brl']:.0f}",
             "note": "min. lift worth acting on"},
            {"label": "Guardrail margin", "value": f"{power['guardrail']['non_inferiority_margin_absolute']*100:.1f}pp",
             "note": "max. tolerable complaint-rate rise"},
            {"label": "Sellers / arm", "value": f"{power['required_n_per_arm']:,}",
             "note": f"binding: {power['binding_constraint']}"},
            {"label": "Total sellers", "value": f"{power['required_total_sellers']:,}", "note": ""},
            {"label": "Target power", "value": f"{power['power_target']*100:.0f}%",
             "note": f"alpha {power['alpha']}"},
        ], compact=True)

        st.markdown(
            f'<p class="stat-note" style="margin-top:0.9rem;">Real Olist sellers in scope for '
            f"comparison: {power['context_real_sellers_in_scope']:,}. The simulated population is "
            f"sized to what the design requires, not to this historical count - see "
            f'PREREGISTRATION.md for the reasoning.</p>',
            unsafe_allow_html=True,
        )

        with st.expander("Read the full preregistration document"):
            st.markdown(prereg_text)

with tab_results:
    if not has_results or not power:
        st.info("Run `shipping-analyze` (or `python3 -m experiment.analyze`) to populate this tab.")
    else:
        p = results["primary"]
        g = results["guardrail"]
        breach = g["guardrail_breached"]
        significant = p["significant_at_alpha_0.05"]
        mde = power["primary"]["mde_absolute_brl"]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Order value by arm**")
            if significant and p["point_estimate_lift"] > 0:
                treatment_color = TEAL
            elif significant and p["point_estimate_lift"] < 0:
                treatment_color = BRICK
            else:
                treatment_color = SLATE
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[p["control_mean_aov"], p["treatment_mean_aov"]],
                marker_color=[SLATE, treatment_color],
                text=[f"R$ {p['control_mean_aov']:.2f}", f"R$ {p['treatment_mean_aov']:.2f}"],
                textposition="outside",
                textfont=dict(color=INK, family=CHART_FONT, size=13),
            ))
            mde_line = p["control_mean_aov"] + mde
            fig.add_hline(
                y=mde_line,
                line_dash="dash", line_color=INK_SOFT,
                annotation_text=f"preregistered MDE (+R$ {mde:.0f})",
                annotation_font=dict(color=INK_SOFT, family=CHART_FONT, size=11),
                annotation_position="top left",
            )
            top = max(p["treatment_mean_aov"], mde_line)
            fig.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Mean AOV (R$)",
                yaxis=dict(gridcolor=HAIRLINE, range=[0, top * 1.2]),
                height=340, margin=dict(t=40, b=20, l=40, r=20),
            )
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.markdown("**Complaint rate by arm**")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker_color=[SLATE, BRICK if breach else TEAL],
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="#FFFFFF", family=CHART_FONT, size=13),
            ))
            ceiling_value = g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100
            fig2.add_hline(
                y=ceiling_value,
                line_dash="dash", line_color=BRICK,
                annotation_text="non-inferiority ceiling",
                annotation_font=dict(color=BRICK, family=CHART_FONT, size=11),
                annotation_position="top left",
            )
            max_bar = max(g["control_complaint_rate"], g["treatment_complaint_rate"]) * 100
            fig2.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Complaint rate (%)",
                yaxis=dict(gridcolor=HAIRLINE, range=[0, max(ceiling_value, max_bar) * 1.18]),
                height=340, margin=dict(t=40, b=20, l=40, r=20),
            )
            st.plotly_chart(fig2, width='stretch')

        with st.expander("View raw analysis output (JSON)"):
            st.json(results, expanded=True)

with tab_recovery:
    if not has_results or not recovery:
        st.info("Run `shipping-analyze` (or `python3 -m experiment.analyze`) to populate this tab.")
    else:
        r = recovery
        both_ok = r["both_recovered"]

        st.caption(
            "Ground truth exists only because this experiment is simulated: "
            "the true injected effect is checked against the preregistered "
            "analysis's confidence interval, after analyze() has already "
            "returned a result computed without ever seeing this file."
        )

        def recovery_chart(title, point_low, point_high, true_value, unit_fmt, recovered):
            color = TEAL if recovered else BRICK
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[point_low, point_high], y=[0, 0],
                mode="lines", line=dict(color=color, width=6),
                hoverinfo="skip", showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=[true_value], y=[0], mode="markers",
                marker=dict(symbol="diamond", size=13, color=INK),
                name="True injected value", showlegend=True,
                hovertemplate=f"True value: {unit_fmt(true_value)}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=[(point_low + point_high) / 2], y=[0], mode="markers",
                marker=dict(symbol="line-ns", size=0),
                showlegend=False, hoverinfo="skip",
            ))
            fig.update_layout(
                template="plotly_white",
                title=dict(text=title, font=dict(family=CHART_FONT, size=13, color=INK), x=0),
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                height=140,
                margin=dict(t=36, b=28, l=20, r=20),
                yaxis=dict(visible=False, range=[-1, 1]),
                xaxis=dict(gridcolor=HAIRLINE, zeroline=False),
                legend=dict(orientation="h", y=-0.35, x=0, font=dict(size=11)),
            )
            return fig

        st.plotly_chart(
            recovery_chart(
                "AOV lift - 95% CI (bar) vs. true injected value (diamond)",
                r["primary_ci"][0], r["primary_ci"][1], r["true_aov_lift"],
                lambda v: f"R$ {v:.2f}", r["primary_recovered"],
            ),
            width='stretch',
        )
        st.plotly_chart(
            recovery_chart(
                "Complaint-rate diff - 95% CI (bar) vs. true injected value (diamond)",
                r["guardrail_ci"][0] * 100, r["guardrail_ci"][1] * 100, r["true_complaint_lift"] * 100,
                lambda v: f"{v:.2f}pp", r["guardrail_recovered"],
            ),
            width='stretch',
        )

        stat_row([
            {
                "label": "AOV lift recovered",
                "value": "Yes" if r["primary_recovered"] else "No",
                "tone": "good" if r["primary_recovered"] else "bad",
                "note": f"true R$ {r['true_aov_lift']:.2f} · CI [R$ {r['primary_ci'][0]:.2f}, R$ {r['primary_ci'][1]:.2f}]",
            },
            {
                "label": "Complaint-rate diff recovered",
                "value": "Yes" if r["guardrail_recovered"] else "No",
                "tone": "good" if r["guardrail_recovered"] else "bad",
                "note": f"true {r['true_complaint_lift']*100:.2f}pp · CI [{r['guardrail_ci'][0]*100:.2f}pp, {r['guardrail_ci'][1]*100:.2f}pp]",
            },
        ], compact=True)

        st.caption(
            "A 95% confidence interval is expected to miss the true value roughly "
            "one seeded run in twenty, even when the method is correct. "
            "Recovery is a smoke test that the pipeline isn't obviously broken, "
            "not proof the method generalizes to every real, unknown effect size - "
            "see README limitations. `test_recovery_check_catches_bugs.py` "
            "separately confirms this check can detect an actual bug when one is injected."
        )

with tab_memo:
    if not has_results:
        st.info("Run `shipping-report` (or `python3 -m experiment.reporting`) to populate this tab.")
    else:
        p = results["primary"]
        g = results["guardrail"]
        verdict, reasoning = recommendation(p, g)
        breach = g["guardrail_breached"]
        significant = p["significant_at_alpha_0.05"]
        n_total = p["n_treatment_sellers"] + p["n_control_sellers"]

        st.markdown(f"#### Recommendation: {verdict}")
        st.markdown(reasoning)

        st.markdown("#### What we tested")
        st.markdown(
            f"- Randomly split **{n_total:,} sellers** into two equal groups: standard "
            "shipping vs. free shipping\n"
            "- Measured whether free shipping changed **average order value**\n"
            "- Separately checked whether it made **delivery complaints** worse"
        )

        st.markdown("#### Results at a glance")
        stat_row([
            {
                "label": "Order value, treatment",
                "value": f"R$ {p['treatment_mean_aov']:.2f}",
                "tone": "good" if significant else "",
                "note": f"control R$ {p['control_mean_aov']:.2f} · lift R$ {p['point_estimate_lift']:.2f} · "
                        f"95% CI [R$ {p['ci_95_low']:.2f}, R$ {p['ci_95_high']:.2f}]",
            },
            {
                "label": "Complaint rate, treatment",
                "value": f"{g['treatment_complaint_rate']*100:.1f}%",
                "tone": "bad" if breach else "good",
                "note": f"control {g['control_complaint_rate']*100:.1f}% · diff {g['point_estimate_diff']*100:+.1f}pp · "
                        f"margin {g['non_inferiority_margin']*100:.1f}pp",
            },
        ])

        st.markdown("#### What happens next")
        st.markdown(next_step(p, g, verdict))

        with st.expander("Read as a plain-text memo"):
            st.markdown(memo_text)

st.markdown(
    """
    <div class="app-footer">
        <span>Built with Streamlit, Plotly, statsmodels · calibrated from the Olist Brazilian E-Commerce dataset</span>
        <span>See PREREGISTRATION.md for the full design rationale</span>
    </div>
    """,
    unsafe_allow_html=True,
)