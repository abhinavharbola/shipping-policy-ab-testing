"""
Step 8: Streamlit dashboard.

Design system
--------------
Brutalist, not decorative: pure white paper, near-black ink, 2px solid
black borders on every panel, no border-radius anywhere, and a flat hard
offset shadow (no blur) instead of soft elevation. Color is rationed to
exactly one job - the verdict/guardrail status - using flat, saturated
fills rather than soft tints, so a green or red block always means the
same thing and nothing else on the page competes with it for attention.

Type: Space Grotesk (bold, uppercase, tracked-out) for headings, tab
labels, and section titles - this is a report, not a form - Inter for
body copy, and JetBrains Mono reserved strictly for numeric data:
statistics, confidence intervals, seeds. Never for labels.

Layout: there is no sidebar. Everything the sidebar used to hold
(hypothesis, design parameters, verdict, seed) already lives on the main
canvas - the hero panel, the stat rows, and the Design tab - so a second
copy in a rail added nothing but clutter. The four tabs span the full
width of the content frame edge to edge, evenly divided, instead of
clustering in the middle. All prose (subtitle, reasoning, captions, memo
body) is justified; headings and one-line data strings are not, since
justification only does something useful across multiple lines.

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

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FAVICON_PATH = ASSETS / "favicon.png"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.reporting import next_step, recommendation  # noqa: E402

PAGE_ICON = str(FAVICON_PATH) if FAVICON_PATH.is_file() else "\U0001F4E6"

st.set_page_config(
    page_title="Free Shipping Experiment: Preregistered A/B Test",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

PAPER = "#FFFFFF"
PANEL = "#FFFFFF"
INK = "#0B0B0C"
INK_SOFT = "#54585F"
GRID = "#DADDE1"

SUCCESS = "#0F8A5F"
SUCCESS_FILL = "#2ED47A"
WARNING = "#8A5D00"
WARNING_FILL = "#FFC93C"
DANGER = "#B3241C"
DANGER_FILL = "#FF5A48"
NEUTRAL = "#6B7280"

DISPLAY_FONT = "'Space Grotesk', 'Arial Black', sans-serif"
TITLE_FONT = "'Archivo Black', 'Arial Black', sans-serif"
BODY_FONT = "'Inter', -apple-system, sans-serif"
DATA_FONT = "'JetBrains Mono', 'SFMono-Regular', monospace"

CHART_FONT = "JetBrains Mono"

# ---------------------------------------------------------------------------
# Global styles
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: {BODY_FONT};
        color: {INK};
    }}

    [data-testid="stAppViewContainer"] {{
        background-color: {PAPER};
    }}

    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
    }}

    .block-container {{
        padding-top: 2.4rem;
        padding-bottom: 2rem;
        max-width: 1120px;
        margin-left: auto;
        margin-right: auto;
    }}

    h1, h2, h3, h4 {{
        font-family: {DISPLAY_FONT};
        color: {INK};
    }}

    code {{ font-family: {DATA_FONT}; }}

    /* ---- masthead: centered title, justified subtitle ---- */
    .masthead {{
        text-align: center;
        margin: 0 auto 1.8rem auto;
        max-width: 760px;
        padding-bottom: 1.4rem;
        border-bottom: 3px solid {INK};
    }}
    .masthead .eyebrow {{
        font-family: {DATA_FONT};
        font-size: 0.78rem;
        line-height: 1.8;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: {INK_SOFT};
        margin: 0 0 0.8rem 0;
        overflow: visible;
    }}
    .masthead h1 {{
        font-family: {TITLE_FONT};
        font-weight: 300;
        font-size: 2.5rem;
        letter-spacing: -0.01em;
        margin: 0 0 0.8rem 0;
        line-height: 1.15;
    }}
    .masthead .subtitle {{
        color: {INK_SOFT};
        font-size: 0.98rem;
        line-height: 1.6;
        margin: 0 auto;
        text-align: justify;
        text-align-last: center;
    }}

    /* ---- hero verdict panel ---- */
    .hero {{
        background: {PANEL};
        border: 2px solid {INK};
        box-shadow: 8px 8px 0 {INK};
        padding: 1.8rem 1.9rem 0.2rem 1.9rem;
        margin: 0 0 2.4rem 0;
    }}
    .hero-top {{
        display: flex;
        justify-content: center;
        margin-bottom: 0.9rem;
    }}
    .badge {{
        display: inline-block;
        font-family: {DISPLAY_FONT};
        font-weight: 700;
        font-size: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        padding: 0.3rem 1.1rem;
        border: 2px solid {INK};
        color: {INK};
    }}
    .badge.sm {{ font-size: 0.78rem; padding: 0.2rem 0.6rem; letter-spacing: 0.06em; }}
    .badge.good {{ background: {SUCCESS_FILL}; }}
    .badge.caution {{ background: {WARNING_FILL}; }}
    .badge.bad {{ background: {DANGER_FILL}; }}
    .badge.neutral {{ background: #FFFFFF; }}

    .hero-reasoning {{
        color: {INK};
        font-size: 1rem;
        line-height: 1.6;
        max-width: 70ch;
        margin: 0 auto 0.9rem auto;
        text-align: justify;
        text-align-last: center;
    }}
    .hero-meta {{
        color: {INK_SOFT};
        font-size: 0.8rem;
        margin-bottom: 1.1rem;
        font-family: {DATA_FONT};
        text-align: center;
    }}

    /* ---- reusable stat row ---- */
    .stat-row {{
        display: flex;
        border-top: 2px solid {INK};
        border-bottom: 2px solid {INK};
    }}
    .stat-cell {{
        flex: 1;
        padding: 1rem 1.2rem 1.1rem 1.2rem;
        border-right: 2px solid {INK};
        text-align: center;
    }}
    .stat-cell:last-child {{ border-right: none; }}
    .stat-label {{
        font-size: 0.78rem;
        color: {INK_SOFT};
        margin-bottom: 0.35rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .stat-value {{
        font-family: {DATA_FONT};
        font-size: 1.5rem;
        font-weight: 600;
        color: {INK};
        line-height: 1.2;
    }}
    .stat-value.good {{ color: {SUCCESS}; }}
    .stat-value.caution {{ color: {WARNING}; }}
    .stat-value.bad {{ color: {DANGER}; }}
    .stat-note {{
        font-family: {DATA_FONT};
        font-size: 0.76rem;
        color: {INK_SOFT};
        margin-top: 0.4rem;
        line-height: 1.5;
    }}
    .stat-row.compact .stat-cell {{ padding-top: 0.75rem; padding-bottom: 0.75rem; }}
    .stat-row.compact .stat-value {{ font-size: 1.15rem; }}

    /* ---- section nav: full-width, evenly divided, inverted on select ----
       Built from real st.button widgets (not st.tabs) because Streamlit's
       internal tab markup is not stable enough to reliably restyle - the
       column layout below guarantees the four buttons split the frame
       width evenly regardless of Streamlit version. ---- */
    .st-key-section_nav div[data-testid="stHorizontalBlock"] {{
        border: 2px solid {INK};
        margin-bottom: 1.8rem;
        gap: 0 !important;
    }}
    .st-key-section_nav div[data-testid="column"] {{
        padding: 0 !important;
        border-right: 2px solid {INK};
    }}
    .st-key-section_nav div[data-testid="column"]:last-child {{
        border-right: none;
    }}
    .st-key-section_nav div[data-testid="stButton"] {{
        width: 100%;
    }}
    .st-key-section_nav button {{
        font-family: {DISPLAY_FONT} !important;
        font-weight: 700 !important;
        font-size: 0.86rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.9rem 0 !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        width: 100%;
    }}
    .st-key-section_nav button[kind="secondary"] {{
        background: {PANEL} !important;
        color: {INK} !important;
    }}
    .st-key-section_nav button[kind="primary"] {{
        background: {INK} !important;
        color: #FFFFFF !important;
    }}
    .st-key-section_nav button:hover {{
        background: {INK} !important;
        color: #FFFFFF !important;
    }}
    .st-key-section_nav button p {{
        font-family: {DISPLAY_FONT} !important;
        font-weight: 700 !important;
        color: inherit !important;
    }}

    .stMarkdown p, .stMarkdown li {{
        line-height: 1.6;
        text-align: justify;
    }}

    .section-caption {{
        text-align: justify;
        text-align-last: center;
        color: {INK_SOFT};
        font-size: 0.86rem;
        margin-bottom: 1.1rem;
    }}

    /* ---- memo sheet ---- */
    .memo-sheet {{
        background: {PANEL};
        border: 2px solid {INK};
        box-shadow: 8px 8px 0 {INK};
        padding: 2rem 2.2rem 1.8rem 2.2rem;
        margin: 0 auto 1.4rem auto;
        max-width: 780px;
    }}
    .memo-head {{
        border-bottom: 2px solid {INK};
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }}
    .memo-head-row {{
        display: flex;
        gap: 0.9rem;
        font-family: {DATA_FONT};
        font-size: 0.82rem;
        margin-bottom: 0.4rem;
    }}
    .memo-head-row:last-child {{ margin-bottom: 0; }}
    .memo-k {{
        color: {INK_SOFT};
        width: 3.4rem;
        flex-shrink: 0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }}
    .memo-v {{ color: {INK}; font-weight: 600; }}
    .memo-body {{
        text-align: justify;
        line-height: 1.65;
        color: {INK};
        font-size: 0.98rem;
        margin-bottom: 1.3rem;
    }}
    .memo-section-title {{
        font-family: {DISPLAY_FONT};
        text-transform: uppercase;
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        margin: 0 0 0.7rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid {INK};
    }}
    .memo-list {{
        text-align: justify;
        line-height: 1.65;
        padding-left: 1.2rem;
        margin-bottom: 1.4rem;
        color: {INK};
        font-size: 0.98rem;
    }}
    .memo-stat-grid {{
        display: flex;
        border: 2px solid {INK};
        margin-bottom: 1.4rem;
    }}
    .memo-stat-cell {{
        flex: 1;
        padding: 0.95rem 1.1rem;
        border-right: 2px solid {INK};
    }}
    .memo-stat-cell:last-child {{ border-right: none; }}
    .memo-stat-label {{
        font-size: 0.74rem;
        color: {INK_SOFT};
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
        font-weight: 600;
    }}
    .memo-stat-value {{
        font-family: {DATA_FONT};
        font-size: 1.3rem;
        font-weight: 600;
        color: {INK};
    }}
    .memo-stat-value.good {{ color: {SUCCESS}; }}
    .memo-stat-value.bad {{ color: {DANGER}; }}
    .memo-stat-note {{
        font-family: {DATA_FONT};
        font-size: 0.74rem;
        color: {INK_SOFT};
        margin-top: 0.35rem;
        line-height: 1.5;
    }}

    div[data-testid="stDownloadButton"] {{
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
    }}
    div[data-testid="stDownloadButton"] button {{
        font-family: {DISPLAY_FONT};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.82rem;
        border: 2px solid {INK} !important;
        border-radius: 0 !important;
        background: {INK} !important;
        color: #FFFFFF !important;
        box-shadow: 4px 4px 0 {INK};
        padding: 0.55rem 1.4rem;
    }}
    div[data-testid="stDownloadButton"] button:hover {{
        background: #FFFFFF !important;
        color: {INK} !important;
    }}

    /* ---- footer ---- */
    .app-footer {{
        margin-top: 1rem;
        padding-top: 1.1rem;
        border-top: 2px solid {INK};
        color: {INK_SOFT};
        font-size: 0.8rem;
        display: flex;
        justify-content: center;
        gap: 1.8rem;
        flex-wrap: wrap;
        text-align: center;
    }}
    .app-footer a {{ color: {INK}; text-decoration: underline; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def stat_row(stats, compact=False):
    """Render a row of statistics as hard-bordered columns, sharing one
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


def badge(text, tone="neutral", small=False):
    size_class = "sm" if small else ""
    return f'<span class="badge {tone} {size_class}">{text}</span>'


# ---------------------------------------------------------------------------
# Data loading - reads each pipeline artifact independently, so tabs can
# fall back to a helpful prompt rather than crashing when an earlier stage
# hasn't run yet.
# ---------------------------------------------------------------------------

@st.cache_data
def load_json(path):
    return json.load(open(ROOT / path, encoding="utf-8"))


@st.cache_data
def load_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def exists(path):
    return (ROOT / path).is_file()


power_done = exists("results/power_analysis.json")
analyze_done = exists("results/analysis_results.json")
report_done = exists("results/memo.md")

prereg_text = load_text("docs/PREREGISTRATION.md") if exists("docs/PREREGISTRATION.md") else None
power = load_json("results/power_analysis.json") if power_done else None

has_results = analyze_done and report_done
if has_results:
    results = load_json("results/analysis_results.json")
    recovery = load_json("results/recovery_check.json") if exists("results/recovery_check.json") else None
    memo_text = load_text("results/memo.md")
true_effects = load_json("data/simulated/true_effects.json") if exists("data/simulated/true_effects.json") else None

# ---------------------------------------------------------------------------
# Masthead (centered)
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="masthead">
        <div class="eyebrow">Preregistered A/B test</div>
        <h1>Free Shipping &amp; Order Value</h1>
        <div class="subtitle">Does offering free shipping raise average order value
        without meaningfully increasing delivery complaints? The metric, sample
        size, and tests below were locked in before any experimental data
        existed.</div>
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
        <div class="hero">
            <div class="hero-top">{badge("Design locked, awaiting data", "neutral")}</div>
            <div class="hero-reasoning">The preregistered design requires
            {power['required_n_per_arm']:,} sellers per arm
            ({power['required_total_sellers']:,} total). Run
            <code>scripts/run_pipeline.py</code> (or the individual
            <code>python3 -m experiment.simulate</code>,
            <code>python3 -m experiment.randomize</code>, and
            <code>python3 -m experiment.analyze</code> steps)
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

    verdict_tone = "good" if verdict == "GO" else "bad"

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
        <div class="hero">
            <div class="hero-top">{badge(verdict, verdict_tone)}</div>
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
# Section nav - four real buttons in equal-width columns rather than
# st.tabs(), so the bar reliably spans edge to edge with even spacing
# instead of clustering in the middle.
# ---------------------------------------------------------------------------

SECTIONS = ["Design", "Results", "Recovery check", "Memo"]
if "active_section" not in st.session_state:
    st.session_state.active_section = SECTIONS[0]

with st.container(key="section_nav"):
    nav_cols = st.columns(len(SECTIONS), gap="small")
    for nav_col, name in zip(nav_cols, SECTIONS):
        with nav_col:
            is_active = st.session_state.active_section == name
            if st.button(
                name,
                key=f"nav_{name}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                # The button's own color for this run was already fixed by
                # the `type` argument above, computed from the state as it
                # stood *before* this click - so without an immediate rerun
                # the newly active tab wouldn't invert until some later,
                # unrelated interaction forced a redraw. Rerunning now makes
                # every button re-evaluate is_active against the fresh
                # state in the same click.
                if st.session_state.active_section != name:
                    st.session_state.active_section = name
                    st.rerun()

active_section = st.session_state.active_section

if active_section == "Design":
    if not power:
        st.info("Run `python3 -m design.power_analysis` (or `scripts/run_pipeline.py`) to populate this tab.")
    else:
        st.markdown(
            '<div class="section-caption">Pulled directly from '
            'docs/PREREGISTRATION.md and results/power_analysis.json - the '
            'design was locked in before any simulation code existed. '
            'Sellers, not orders, are the unit of randomization.</div>',
            unsafe_allow_html=True,
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
            f'<p class="section-caption" style="margin-top:0.9rem;">Real Olist sellers in scope for '
            f"comparison: {power['context_real_sellers_in_scope']:,}. The simulated population is "
            f"sized to what the design requires, not to this historical count - see "
            f'docs/PREREGISTRATION.md for the reasoning.</p>',
            unsafe_allow_html=True,
        )

        with st.expander("Read the full preregistration document"):
            st.markdown(prereg_text)

elif active_section == "Results":
    if not has_results or not power:
        st.info("Run `python3 -m experiment.analyze` (or `scripts/run_pipeline.py`) to populate this tab.")
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
                treatment_color = SUCCESS_FILL
            elif significant and p["point_estimate_lift"] < 0:
                treatment_color = DANGER_FILL
            else:
                treatment_color = NEUTRAL
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[p["control_mean_aov"], p["treatment_mean_aov"]],
                marker=dict(color=[NEUTRAL, treatment_color], line=dict(color=INK, width=2)),
                text=[f"R$ {p['control_mean_aov']:.2f}", f"R$ {p['treatment_mean_aov']:.2f}"],
                textposition="outside",
                textfont=dict(color=INK, family=CHART_FONT, size=13),
            ))
            mde_line = p["control_mean_aov"] + mde
            fig.add_hline(
                y=mde_line,
                line_dash="dash", line_color=INK,
                annotation_text=f"preregistered MDE (+R$ {mde:.0f})",
                annotation_font=dict(color=INK, family=CHART_FONT, size=11),
                annotation_position="top left",
            )
            top = max(p["treatment_mean_aov"], mde_line)
            fig.update_layout(
                template="plotly_white",
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Mean AOV (R$)",
                yaxis=dict(gridcolor=GRID, range=[0, top * 1.2]),
                height=340, margin=dict(t=40, b=20, l=40, r=20),
            )
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.markdown("**Complaint rate by arm**")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker=dict(color=[NEUTRAL, DANGER_FILL if breach else SUCCESS_FILL], line=dict(color=INK, width=2)),
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color=INK, family=CHART_FONT, size=13),
            ))
            ceiling_value = g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100
            fig2.add_hline(
                y=ceiling_value,
                line_dash="dash", line_color=DANGER,
                annotation_text="non-inferiority ceiling",
                annotation_font=dict(color=DANGER, family=CHART_FONT, size=11),
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
            st.plotly_chart(fig2, width='stretch')

        with st.expander("View raw analysis output (JSON)"):
            st.json(results, expanded=True)

elif active_section == "Recovery check":
    if not has_results or not recovery:
        st.info("Run `python3 -m experiment.analyze` (or `scripts/run_pipeline.py`) to populate this tab.")
    else:
        r = recovery
        p = results["primary"]
        g = results["guardrail"]

        st.markdown(
            '<div class="section-caption">Ground truth exists only because this '
            "experiment is simulated: the true injected effect is checked "
            "against the preregistered analysis's confidence interval, after "
            "analyze() has already returned a result computed without ever "
            "seeing this file.</div>",
            unsafe_allow_html=True,
        )

        def recovery_chart(title, ci_low, ci_high, point_estimate, true_value, unit_fmt, recovered, x_suffix=""):
            color = SUCCESS if recovered else DANGER
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[ci_low, point_estimate, ci_high],
                y=["Estimate"] * 3,
                mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(size=[7, 11, 7], color=color, line=dict(color=INK, width=1)),
                name="Point estimate, 95% CI",
                hovertemplate="%{x" + x_suffix + "}<extra></extra>",
            ))
            fig.add_vline(
                x=true_value,
                line_dash="dash", line_width=2, line_color=INK,
                annotation_text=f"True value {unit_fmt(true_value)}",
                annotation_font=dict(color=INK, family=CHART_FONT, size=11),
                annotation_position="top",
            )
            fig.update_layout(
                template="plotly_white",
                title=dict(text=title, font=dict(family=CHART_FONT, size=13, color=INK), x=0),
                plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                height=190,
                margin=dict(t=48, b=30, l=90, r=30),
                yaxis=dict(visible=True, showgrid=False, showline=False),
                xaxis=dict(gridcolor=GRID, zeroline=False),
                showlegend=False,
            )
            return fig

        st.plotly_chart(
            recovery_chart(
                "AOV lift, R$ - point estimate with 95% CI vs. true injected value",
                r["primary_ci"][0], r["primary_ci"][1], p["point_estimate_lift"], r["true_aov_lift"],
                lambda v: f"R$ {v:.2f}", r["primary_recovered"],
            ),
            width='stretch',
        )
        st.plotly_chart(
            recovery_chart(
                "Complaint-rate diff, pp - point estimate with 95% CI vs. true injected value",
                r["guardrail_ci"][0] * 100, r["guardrail_ci"][1] * 100,
                g["point_estimate_diff"] * 100, r["true_complaint_lift"] * 100,
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

        st.markdown(
            '<div class="section-caption">A 95% confidence interval is expected '
            "to miss the true value roughly one seeded run in twenty, even when "
            "the method is correct. Recovery is a smoke test that the pipeline "
            "isn't obviously broken, not proof the method generalizes to every "
            "real, unknown effect size - see README limitations. "
            "<code>test_recovery_check_catches_bugs.py</code> separately "
            "confirms this check can detect an actual bug when one is "
            "injected.</div>",
            unsafe_allow_html=True,
        )

elif active_section == "Memo":
    if not has_results:
        st.info("Run `python3 -m experiment.reporting` (or `scripts/run_pipeline.py`) to populate this tab.")
    else:
        p = results["primary"]
        g = results["guardrail"]
        verdict, reasoning = recommendation(p, g)
        breach = g["guardrail_breached"]
        significant = p["significant_at_alpha_0.05"]
        n_total = p["n_treatment_sellers"] + p["n_control_sellers"]
        verdict_tone = "good" if verdict == "GO" else "bad"

        # Built as a flat, single-line HTML string (no blank lines, no
        # leading indentation) rather than a pretty-printed multi-line
        # f-string: Streamlit's markdown renderer treats a blank line
        # inside a raw-HTML block as the block's end, after which any
        # following line indented 4+ spaces is read as a literal code
        # block instead of HTML - which is what broke this card before.
        memo_html = "".join([
            '<div class="memo-sheet">',
            '<div class="memo-head">',
            '<div class="memo-head-row"><span class="memo-k">To</span>'
            '<span class="memo-v">Decision stakeholders</span></div>',
            '<div class="memo-head-row"><span class="memo-k">From</span>'
            '<span class="memo-v">Preregistered experiment pipeline</span></div>',
            '<div class="memo-head-row"><span class="memo-k">Re</span>'
            '<span class="memo-v">Free shipping rollout decision</span></div>',
            '</div>',
            f'<div class="hero-top" style="margin-bottom:1.2rem;">{badge(verdict, verdict_tone)}</div>',
            f'<p class="memo-body">{reasoning}</p>',
            '<div class="memo-section-title">What we tested</div>',
            '<ul class="memo-list">',
            f'<li>Randomly split {n_total:,} sellers into two equal groups: '
            'standard shipping vs. free shipping</li>',
            '<li>Measured whether free shipping changed average order value</li>',
            '<li>Separately checked whether it made delivery complaints worse</li>',
            '</ul>',
            '<div class="memo-section-title">Results at a glance</div>',
            '<div class="memo-stat-grid">',
            '<div class="memo-stat-cell">',
            '<div class="memo-stat-label">Order value, treatment</div>',
            f'<div class="memo-stat-value {"good" if significant else ""}">'
            f'R$ {p["treatment_mean_aov"]:.2f}</div>',
            f'<div class="memo-stat-note">control R$ {p["control_mean_aov"]:.2f} · '
            f'lift R$ {p["point_estimate_lift"]:.2f} · '
            f'95% CI [R$ {p["ci_95_low"]:.2f}, R$ {p["ci_95_high"]:.2f}]</div>',
            '</div>',
            '<div class="memo-stat-cell">',
            '<div class="memo-stat-label">Complaint rate, treatment</div>',
            f'<div class="memo-stat-value {"bad" if breach else "good"}">'
            f'{g["treatment_complaint_rate"]*100:.1f}%</div>',
            f'<div class="memo-stat-note">control {g["control_complaint_rate"]*100:.1f}% · '
            f'diff {g["point_estimate_diff"]*100:+.1f}pp · '
            f'margin {g["non_inferiority_margin"]*100:.1f}pp</div>',
            '</div>',
            '</div>',
            '<div class="memo-section-title">What happens next</div>',
            f'<p class="memo-body" style="margin-bottom:0;">{next_step(p, g, verdict)}</p>',
            '</div>',
        ])
        st.markdown(memo_html, unsafe_allow_html=True)

        st.download_button(
            label="Download memo (.md)",
            data=memo_text,
            file_name="free_shipping_experiment_memo.md",
            mime="text/markdown",
        )

st.markdown(
    """
    <div class="app-footer">
        <span>Built with Streamlit, Plotly, statsmodels · calibrated from the Olist Brazilian E-Commerce dataset</span>
        <a href="https://github.com/abhinavharbola/shipping-policy-ab-testing" target="_blank">Repository</a>
        <a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce" target="_blank">Olist dataset</a>
    </div>
    """,
    unsafe_allow_html=True,
)