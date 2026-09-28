"""
Dashboard: Japandi report view.

Warm greige paper, linen panels, hairline rules, no shadows, small
radii, and generous whitespace. Shippori Mincho carries headings and the
verdict, DM Sans carries everything else with tabular numerals. Sage,
ochre and clay are reserved for status. Navigation is a quiet text tab
bar with an underline marking the active section.

The verdict is computed by calling experiment.reporting.recommendation()
on the analysis output, never by parsing memo.md. Currency always shows 2
decimal places and percentages 1. Currency in markdown is wrapped in code
spans so Streamlit does not read dollar signs as LaTeX.
"""

import json
import re
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

PAGE_ICON = str(FAVICON_PATH) if FAVICON_PATH.is_file() else "\u25A0"

st.set_page_config(
    page_title="Free Shipping Experiment: Preregistered A/B Test",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

PAPER = "#ECE8E1"
PANEL = "#F8F6F2"
INK = "#2A2926"
INK_SOFT = "#6B675F"
GRID = "#DDD7CB"
RULE = "#CFC8BB"
ACCENT = "#6F7B67"
HIGHLIGHT = "#E4DED3"

SUCCESS = "#4F6143"
SUCCESS_FILL = "#A9B89A"
WARNING = "#7D5A1E"
WARNING_FILL = "#D8B879"
DANGER = "#8C3B2E"
DANGER_FILL = "#C98F80"
NEUTRAL = "#C3BCAE"

DISPLAY_FONT = "'Shippori Mincho', 'Hiragino Mincho ProN', Georgia, serif"
TITLE_FONT = DISPLAY_FONT
BODY_FONT = "'DM Sans', -apple-system, 'Segoe UI', sans-serif"
DATA_FONT = BODY_FONT

CHART_FONT = "DM Sans"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;600;700&family=DM+Sans:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: {BODY_FONT};
        color: {INK};
        font-variant-numeric: tabular-nums;
    }}
    [data-testid="stAppViewContainer"] {{ background-color: {PAPER}; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

    .block-container {{
        padding-top: 3.2rem;
        padding-bottom: 3rem;
        max-width: 1040px;
        margin-left: auto;
        margin-right: auto;
    }}
    h1, h2, h3, h4 {{ font-family: {DISPLAY_FONT}; color: {INK}; font-weight: 500; }}
    code {{
        font-family: {DATA_FONT};
        background: {HIGHLIGHT};
        color: {INK};
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        font-size: 0.9em;
    }}

    .masthead {{
        margin: 0 0 2.8rem 0;
        padding-bottom: 2rem;
        border-bottom: 1px solid {RULE};
        text-align: center;
    }}
    .masthead .eyebrow {{
        font-size: 0.86rem;
        color: {ACCENT};
        font-weight: 500;
        letter-spacing: 0.02em;
        margin: 0 0 0.9rem 0;
    }}
    .masthead h1 {{
        font-family: {TITLE_FONT};
        font-weight: 500;
        font-size: 2.9rem;
        letter-spacing: -0.01em;
        line-height: 1.15;
        margin: 0 0 1.1rem 0;
        padding: 0;
    }}
    .masthead .subtitle {{
        color: {INK_SOFT};
        font-size: 1rem;
        line-height: 1.75;
        text-align: justify;
        text-align-last: center;
    }}

    .hero {{
        background: {PANEL};
        border: 1px solid {RULE};
        border-radius: 4px;
        padding: 2.2rem 2.4rem 0 2.4rem;
        margin: 0 0 1.4rem 0;
    }}
    .hero-top {{ display: flex; justify-content: center; margin-bottom: 1.3rem; }}
    .badge {{
        display: inline-block;
        font-family: {DISPLAY_FONT};
        font-weight: 600;
        font-size: 1.5rem;
        letter-spacing: 0.06em;
        padding: 0.25rem 1.1rem;
        border: 1px solid {INK};
        border-radius: 2px;
        color: {INK};
    }}
    .badge.sm {{ font-size: 0.8rem; padding: 0.15rem 0.6rem; }}
    .badge.good {{ background: {SUCCESS_FILL}; border-color: {SUCCESS}; color: {SUCCESS}; }}
    .badge.caution {{ background: {WARNING_FILL}; border-color: {WARNING}; color: {WARNING}; }}
    .badge.bad {{ background: {DANGER_FILL}; border-color: {DANGER}; color: {DANGER}; }}
    .badge.neutral {{ background: {HIGHLIGHT}; border-color: {RULE}; color: {INK_SOFT}; }}

    .hero-reasoning {{
        color: {INK};
        font-size: 1.05rem;
        line-height: 1.75;
        margin: 0 0 1.6rem 0;
        text-align: justify;
        text-align-last: center;
    }}
    .hero-reasoning:last-child {{ margin-bottom: 2.2rem; }}
    .hero-meta {{
        color: {INK_SOFT};
        font-size: 0.82rem;
        margin: 0 -2.4rem 0 -2.4rem;
        padding: 0.9rem 2.4rem;
        border-top: 1px solid {RULE};
        text-align: center;
    }}

    .stat-row {{
        display: flex;
        background: {PANEL};
        border: 1px solid {RULE};
        border-radius: 4px;
        margin-bottom: 0.6rem;
    }}
    .stat-cell {{
        flex: 1;
        padding: 1.4rem 1.6rem 1.5rem 1.6rem;
        border-right: 1px solid {RULE};
        text-align: center;
    }}
    .stat-cell:last-child {{ border-right: none; }}
    .stat-label {{
        font-size: 0.86rem;
        color: {INK_SOFT};
        margin-bottom: 0.6rem;
        font-weight: 500;
    }}
    .stat-value {{
        font-family: {DISPLAY_FONT};
        font-size: 1.85rem;
        font-weight: 500;
        color: {INK};
        line-height: 1.2;
    }}
    .stat-value.good {{ color: {SUCCESS}; }}
    .stat-value.caution {{ color: {WARNING}; }}
    .stat-value.bad {{ color: {DANGER}; }}
    .stat-note {{
        font-size: 0.8rem;
        color: {INK_SOFT};
        margin-top: 0.6rem;
        line-height: 1.55;
    }}
    .stat-row.compact .stat-cell {{ padding-top: 1.1rem; padding-bottom: 1.2rem; }}
    .stat-row.compact .stat-value {{ font-size: 1.4rem; }}

    .st-key-section_nav div[data-testid="stHorizontalBlock"] {{
        border-bottom: 1px solid {RULE};
        margin: 1.4rem 0 2.2rem 0;
        gap: 0 !important;
    }}
    .st-key-section_nav div[data-testid="column"] {{ padding: 0 !important; }}
    .st-key-section_nav div[data-testid="stButton"] {{ width: 100%; }}
    .st-key-section_nav button {{
        font-family: {BODY_FONT} !important;
        font-weight: 500 !important;
        font-size: 0.98rem !important;
        padding: 0.9rem 0 !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        background: transparent !important;
        width: 100%;
        transition: color 0.15s;
    }}
    .st-key-section_nav button[kind="secondary"] {{ color: {INK_SOFT} !important; }}
    .st-key-section_nav button[kind="secondary"]:hover {{ color: {INK} !important; }}
    .st-key-section_nav button[kind="primary"] {{
        color: {INK} !important;
        box-shadow: inset 0 -2px 0 {INK} !important;
    }}
    .st-key-section_nav button:focus-visible {{ outline: 2px solid {ACCENT} !important; outline-offset: -4px; }}
    .st-key-section_nav button p {{ font-family: {BODY_FONT} !important; font-weight: 500 !important; color: inherit !important; }}

    .stMarkdown p, .stMarkdown li {{ line-height: 1.75; text-align: justify; }}
    .stMarkdown p:has(> strong:only-child) {{ text-align: center; }}

    .section-caption {{
        text-align: justify;
        text-align-last: center;
        color: {INK_SOFT};
        font-size: 0.92rem;
        line-height: 1.7;
        margin: 0 0 1.6rem 0;
    }}

    .prereg-heading {{
        font-family: {DISPLAY_FONT};
        font-size: 1.9rem;
        font-weight: 500;
        line-height: 1.25;
        text-align: center;
        margin: 2.4rem 0 0 0;
    }}
    .st-key-prereg_lead {{
        background: {PANEL};
        border: 1px solid {RULE};
        border-radius: 4px;
        padding: 1.2rem 1.6rem 0.4rem 1.6rem;
        margin: 1.2rem 0 0.6rem 0;
    }}
    .prereg-card {{
        display: flex;
        gap: 1.4rem;
        align-items: flex-start;
        background: {PANEL};
        border: 1px solid {RULE};
        border-bottom: none;
        border-radius: 4px 4px 0 0;
        padding: 1.4rem 1.6rem 1.2rem 1.6rem;
        margin-top: 1.2rem;
    }}
    .prereg-num {{
        flex-shrink: 0;
        width: 2.6rem;
        height: 2.6rem;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid {INK};
        border-radius: 2px;
        font-family: {DISPLAY_FONT};
        font-size: 1.25rem;
        font-weight: 600;
    }}
    .prereg-title {{ font-family: {DISPLAY_FONT}; font-size: 1.3rem; font-weight: 600; line-height: 1.3; margin-bottom: 0.5rem; }}
    .prereg-summary {{ color: {INK_SOFT}; font-size: 0.98rem; line-height: 1.7; }}
    .prereg-tag {{
        display: inline-block;
        margin-top: 0.8rem;
        font-size: 0.78rem;
        font-weight: 500;
        color: {WARNING};
        border: 1px solid {WARNING};
        border-radius: 2px;
        padding: 0.1rem 0.6rem;
    }}
    .st-key-prereg div[data-testid="stExpander"] {{ margin-top: 0; border-radius: 0 0 4px 4px; }}
    div[data-testid="stExpander"] {{
        border: 1px solid {RULE};
        border-radius: 4px;
        background: {PANEL};
        margin-top: 1.4rem;
    }}
    div[data-testid="stExpander"] summary {{ font-family: {BODY_FONT}; font-weight: 500; }}
    div[data-testid="stExpander"] .stMarkdown p,
    div[data-testid="stExpander"] .stMarkdown li,
    div[data-testid="stExpander"] .stMarkdown p:has(> strong:only-child) {{ text-align: left; }}
    div[data-testid="stAlert"] {{
        border: 1px solid {RULE};
        border-radius: 4px;
        background: {HIGHLIGHT};
        color: {INK};
    }}

    .memo-sheet {{
        background: {PANEL};
        border: 1px solid {RULE};
        border-radius: 4px;
        padding: 3rem 3.2rem 2.6rem 3.2rem;
        margin: 0 auto 2rem auto;
        max-width: 760px;
    }}
    .memo-head {{ border-bottom: 1px solid {RULE}; padding-bottom: 1.3rem; margin-bottom: 2rem; }}
    .memo-head-row {{ display: flex; gap: 1.2rem; font-size: 0.9rem; margin-bottom: 0.5rem; }}
    .memo-head-row:last-child {{ margin-bottom: 0; }}
    .memo-k {{ color: {INK_SOFT}; width: 3.2rem; flex-shrink: 0; }}
    .memo-v {{ color: {INK}; font-weight: 500; }}
    .memo-body {{
        text-align: left;
        line-height: 1.8;
        color: {INK};
        font-size: 1rem;
        margin-bottom: 1.8rem;
    }}
    .memo-section-title {{
        font-family: {DISPLAY_FONT};
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0 0 0.9rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {RULE};
    }}
    .memo-list {{
        text-align: left;
        line-height: 1.8;
        padding-left: 1.2rem;
        margin-bottom: 1.8rem;
        color: {INK};
        font-size: 1rem;
    }}
    .memo-stat-grid {{
        display: flex;
        border: 1px solid {RULE};
        border-radius: 4px;
        margin-bottom: 1.8rem;
    }}
    .memo-stat-cell {{ flex: 1 1 auto; padding: 1.2rem 1.4rem; border-right: 1px solid {RULE}; }}
    .memo-stat-cell:last-child {{ border-right: none; }}
    .memo-stat-label {{ font-size: 0.84rem; color: {INK_SOFT}; margin-bottom: 0.5rem; font-weight: 500; }}
    .memo-stat-value {{ font-family: {DISPLAY_FONT}; font-size: 1.6rem; font-weight: 500; color: {INK}; }}
    .memo-stat-value.good {{ color: {SUCCESS}; }}
    .memo-stat-value.bad {{ color: {DANGER}; }}
    .memo-stat-note {{ font-size: 0.78rem; color: {INK_SOFT}; margin-top: 0.5rem; line-height: 1.55; }}

    div[data-testid="stDownloadButton"] {{ display: flex; justify-content: center; margin-bottom: 2.4rem; }}
    div[data-testid="stDownloadButton"] button {{
        font-family: {BODY_FONT};
        font-weight: 500;
        font-size: 0.94rem;
        border: 1px solid {INK} !important;
        border-radius: 2px !important;
        background: {INK} !important;
        color: {PANEL} !important;
        padding: 0.65rem 1.8rem;
        transition: background 0.15s, border-color 0.15s;
    }}
    div[data-testid="stDownloadButton"] button:hover {{
        background: {ACCENT} !important;
        border-color: {ACCENT} !important;
        color: {PANEL} !important;
    }}
    div[data-testid="stDownloadButton"] button:focus-visible {{ outline: 2px solid {ACCENT}; outline-offset: 3px; }}

    div[data-testid="stPlotlyChart"] {{
        background: {PANEL};
        border: 1px solid {RULE};
        border-radius: 4px;
        padding: 0.8rem;
        margin-bottom: 1.2rem;
    }}

    .app-footer {{
        margin-top: 2.4rem;
        padding-top: 1.4rem;
        border-top: 1px solid {RULE};
        color: {INK_SOFT};
        font-size: 0.82rem;
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
        text-align: center;
    }}
    .app-footer a {{ color: {INK}; text-decoration: underline; text-underline-offset: 3px; }}

    @media (max-width: 720px) {{
        .stat-row, .memo-stat-grid {{ flex-direction: column; }}
        .stat-cell, .memo-stat-cell {{ border-right: none; border-bottom: 1px solid {RULE}; }}
        .stat-cell:last-child, .memo-stat-cell:last-child {{ border-bottom: none; }}
        .masthead h1 {{ font-size: 2.1rem; }}
        .hero, .memo-sheet {{ padding-left: 1.4rem; padding-right: 1.4rem; }}
        .hero-meta {{ margin-left: -1.4rem; margin-right: -1.4rem; padding-left: 1.4rem; padding-right: 1.4rem; }}
    }}
    @media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
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


def render_preregistration(text, power):
    if not text:
        st.info("docs/PREREGISTRATION.md was not found.")
        return
    parts = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)
    sections = {
        int(parts[i]): (parts[i + 1].strip(), parts[i + 2].strip())
        for i in range(1, len(parts) - 2, 3)
    }
    if len(sections) < 9:
        with st.expander("Read the full preregistration document"):
            st.markdown(text)
        return

    mde = f"BRL {power['primary']['mde_absolute_brl']:.0f}"
    margin = f"{power['guardrail']['non_inferiority_margin_absolute'] * 100:.1f}pp"
    n = f"{power['required_n_per_arm']:,}"
    total = f"{power['required_total_sellers']:,}"
    summaries = {
        1: "Free shipping should raise a seller's average order value without meaningfully raising delivery complaints. The direction was stated before any data existed.",
        2: "The primary metric is average order value per seller. The guardrail is the share of orders reviewed 2 stars or below. Whole sellers are randomized, not individual orders, so one seller's policy cannot leak across arms.",
        3: f"The smallest lift worth acting on is {mde}, just above the roughly BRL 23 of freight a seller absorbs. Complaints may rise by at most {margin} before the gain stops being worth it.",
        4: f"{n} sellers per arm ({total} in total) gives {power['power_target'] * 100:.0f}% power at alpha {power['alpha']}. The order value test needs the most sellers, so it sets the size ({power['binding_constraint']}).",
        5: f"Sellers are assigned 1:1 by simple random draw, with no stratification. At {n} per arm, category mix balances on its own.",
        6: "The analysis runs once, on the full sample, with no interim looks. The code refuses to run on a partial dataset, so nobody can stop early on a lucky result.",
        7: "Welch's t-test on each seller's mean order value. It was chosen before seeing data because free shipping may change the spread of order values between arms.",
        8: f"A one-sided non-inferiority test on each seller's complaint rate against the {margin} margin. The guardrail passes only when the data show the gap is below the margin.",
        9: "This file was committed to git before any simulation code, so the git log proves the design came first.",
    }

    title_match = re.search(r"^# (.+)$", parts[0], flags=re.M)
    heading = title_match.group(1).strip() if title_match else "Preregistration"
    lead = re.sub(r"^# .*\n", "", parts[0]).strip()
    st.markdown(f'<div class="prereg-heading">{heading}</div>', unsafe_allow_html=True)
    with st.container(key="prereg_lead"):
        st.markdown(lead)
        st.markdown("Each section below opens with a plain-language summary. Open a section to read the exact preregistered wording.")

    with st.container(key="prereg"):
        for num in range(1, 10):
            title, body = sections[num]
            tag = '<span class="prereg-tag">Amended before analysis</span>' if num == 8 else ""
            st.markdown(
                f'<div class="prereg-card"><div class="prereg-num">{num}</div>'
                f'<div class="prereg-main"><div class="prereg-title">{title}</div>'
                f'<div class="prereg-summary">{summaries[num]}</div>{tag}</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("Read the full section"):
                st.markdown(body)


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

        render_preregistration(prereg_text, power)

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
                marker=dict(color=[NEUTRAL, treatment_color], line=dict(color=INK, width=1.5)),
                text=[f"R$ {p['control_mean_aov']:.2f}", f"R$ {p['treatment_mean_aov']:.2f}"],
                textposition="outside",
                textfont=dict(color=INK, family=CHART_FONT, size=13),
            ))
            mde_line = p["control_mean_aov"] + mde
            fig.add_hline(
                y=mde_line,
                line_dash="dash", line_width=1.5, line_color=INK,
                annotation_text=f"preregistered MDE (+R$ {mde:.0f})",
                annotation_font=dict(color=INK, family=CHART_FONT, size=11),
                annotation_position="top left",
            )
            top = max(p["treatment_mean_aov"], mde_line)
            fig.update_layout(
                template="plotly_white",
                plot_bgcolor=PANEL, paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Mean AOV (R$)",
                xaxis=dict(showline=True, linewidth=1, linecolor=RULE),
                yaxis=dict(gridcolor=GRID, showline=True, linewidth=1, linecolor=RULE, range=[0, top * 1.2]),
                height=340, margin=dict(t=40, b=20, l=40, r=20),
            )
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.markdown("**Complaint rate by arm**")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=["Control", "Treatment"],
                y=[g["control_complaint_rate"] * 100, g["treatment_complaint_rate"] * 100],
                marker=dict(color=[NEUTRAL, DANGER_FILL if breach else SUCCESS_FILL], line=dict(color=INK, width=1.5)),
                text=[f"{g['control_complaint_rate']*100:.1f}%", f"{g['treatment_complaint_rate']*100:.1f}%"],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color=INK, family=CHART_FONT, size=13),
            ))
            ceiling_value = g["control_complaint_rate"] * 100 + g["non_inferiority_margin"] * 100
            fig2.add_hline(
                y=ceiling_value,
                line_dash="dash", line_width=1.5, line_color=DANGER,
                annotation_text="non-inferiority ceiling",
                annotation_font=dict(color=DANGER, family=CHART_FONT, size=11),
                annotation_position="top left",
            )
            max_bar = max(g["control_complaint_rate"], g["treatment_complaint_rate"]) * 100
            fig2.update_layout(
                template="plotly_white",
                plot_bgcolor=PANEL, paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                yaxis_title="Complaint rate (%)",
                xaxis=dict(showline=True, linewidth=1, linecolor=RULE),
                yaxis=dict(gridcolor=GRID, showline=True, linewidth=1, linecolor=RULE, range=[0, max(ceiling_value, max_bar) * 1.18]),
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
                line=dict(color=color, width=2.5),
                marker=dict(size=[9, 13, 9], color=color, line=dict(color=INK, width=1.5)),
                name="Point estimate, 95% CI",
                hovertemplate="%{x" + x_suffix + "}<extra></extra>",
            ))
            fig.add_vline(
                x=true_value,
                line_dash="dash", line_width=1.5, line_color=INK,
                annotation_text=f"True value {unit_fmt(true_value)}",
                annotation_font=dict(color=INK, family=CHART_FONT, size=11),
                annotation_position="top",
            )
            fig.update_layout(
                template="plotly_white",
                title=dict(text=title, font=dict(family=CHART_FONT, size=13, color=INK), x=0.5, xanchor="center"),
                plot_bgcolor=PANEL, paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=CHART_FONT, color=INK, size=12),
                height=190,
                margin=dict(t=48, b=30, l=90, r=30),
                yaxis=dict(visible=True, showgrid=False, showline=False),
                xaxis=dict(gridcolor=GRID, zeroline=False, showline=True, linewidth=1, linecolor=RULE),
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
            '<li>Separately checked whether it made delivery complaints worse or better</li>',
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
