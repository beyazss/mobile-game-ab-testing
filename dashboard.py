"""Interactive dashboard for the Cookie Cats mobile-game experiment."""

import altair as alt
import pandas as pd
import streamlit as st

from main import (
    CONTROL_GROUP,
    TEST_GROUP,
    calculate_round_distribution,
    calculate_summary,
    check_group_allocation,
    compare_retention,
    load_and_check_data,
)

st.set_page_config(
    page_title="Mobile Game Experiment Review",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#111827"
TEAL = "#18B6A4"
PURPLE = "#7868E6"
AMBER = "#F5B942"
RED = "#E45B69"
GROUP_COLORS = [TEAL, PURPLE]

st.markdown(
    f"""
    <style>
    :root {{ --navy: {NAVY}; --muted: #64748B; --purple: {PURPLE}; }}
    .stApp {{
        background: radial-gradient(circle at 85% 0%, rgba(120,104,230,.10), transparent 28rem), #FFFFFF;
        color: var(--navy);
    }}
    .block-container {{ max-width: 1440px; padding-top: 1.4rem; padding-bottom: 3rem; }}
    [data-testid="stToolbar"] {{ display: none; }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    section[data-testid="stSidebar"] {{ background: #0F172A; border-right: 1px solid #1E293B; }}
    section[data-testid="stSidebar"] * {{ color: #E2E8F0; }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background: #172033; border-color: #334155;
    }}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color: #94A3B8; }}
    .hero {{
        position: relative; overflow: hidden; padding: 2rem 2.2rem; border-radius: 24px;
        color: white; background: linear-gradient(120deg, #101827 0%, #172554 58%, #4C3FCF 140%);
        box-shadow: 0 18px 45px rgba(15,23,42,.16); margin-bottom: 1.3rem;
    }}
    .hero::after {{
        content: ""; position: absolute; width: 260px; height: 260px; right: -70px;
        top: -110px; border-radius: 50%; background: rgba(24,182,164,.23);
    }}
    .eyebrow {{
        display: inline-block; color: #A7F3D0; font-size: .76rem; font-weight: 800;
        letter-spacing: .12em; margin-bottom: .7rem;
    }}
    .hero h1 {{ color: white; font-size: 2.2rem; line-height: 1.1; margin: 0 0 .65rem; }}
    .hero p {{ color: #CBD5E1; font-size: 1rem; max-width: 780px; margin: 0; }}
    .kpi-card {{
        min-height: 118px; padding: 1.15rem 1.25rem; border: 1px solid #E7EAF1;
        border-radius: 18px; background: rgba(255,255,255,.94);
        box-shadow: 0 8px 24px rgba(15,23,42,.06);
    }}
    .kpi-label {{
        color: #64748B; font-size: .78rem; font-weight: 800;
        letter-spacing: .05em; text-transform: uppercase;
    }}
    .kpi-value {{ color: var(--navy); font-size: 1.75rem; font-weight: 800; margin: .35rem 0 .18rem; }}
    .kpi-detail {{ color: #64748B; font-size: .82rem; }}
    .kpi-detail.negative {{ color: #C24150; font-weight: 700; }}
    .decision {{
        min-height: 308px; padding: 1.5rem; border-radius: 18px; color: white;
        background: linear-gradient(145deg, #111827, #202A44);
        box-shadow: 0 12px 28px rgba(15,23,42,.14);
    }}
    .decision-label {{ color: #5EEAD4; font-size: .76rem; font-weight: 800; letter-spacing: .11em; }}
    .decision h3 {{ color: white; font-size: 1.45rem; margin: .65rem 0 1rem; }}
    .decision p {{ color: #CBD5E1; line-height: 1.55; }}
    .decision strong {{ color: white; }}
    .status-row {{ display: flex; gap: .55rem; flex-wrap: wrap; margin-top: 1.1rem; }}
    .status {{
        padding: .38rem .65rem; border: 1px solid #334155; border-radius: 999px;
        color: #DCE7F4; font-size: .75rem;
    }}
    .section-kicker {{
        color: var(--purple); font-size: .75rem; font-weight: 800;
        letter-spacing: .1em; text-transform: uppercase; margin-bottom: .25rem;
    }}
    .section-title {{ color: var(--navy); font-size: 1.45rem; font-weight: 800; margin-bottom: .15rem; }}
    .section-copy {{ color: #64748B; margin-bottom: .8rem; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-color: #E7EAF1; border-radius: 18px;
        box-shadow: 0 8px 24px rgba(15,23,42,.045); background: rgba(255,255,255,.94);
    }}
    button[data-baseweb="tab"] {{ font-weight: 700; padding-left: 1rem; padding-right: 1rem; }}
    .data-note {{
        padding: .9rem 1rem; border-radius: 12px; background: #F1F5F9;
        color: #475569; font-size: .86rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_data() -> pd.DataFrame:
    """Load and validate the public experiment data once."""
    return load_and_check_data()


def kpi_card(label: str, value: str, detail: str, negative: bool = False) -> None:
    """Display a compact metric card with a clear label."""
    detail_class = "kpi-detail negative" if negative else "kpi-detail"
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="{detail_class}">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def retention_chart(summary: pd.DataFrame) -> alt.Chart:
    """Create an interactive D1 and D7 retention comparison."""
    chart_data = summary.melt(
        id_vars="version",
        value_vars=["d1_retention_pct", "d7_retention_pct"],
        var_name="metric",
        value_name="retention",
    )
    chart_data["metric"] = chart_data["metric"].map(
        {"d1_retention_pct": "D1 retention", "d7_retention_pct": "D7 retention"}
    )
    chart_data["label"] = chart_data["retention"].map(lambda value: f"{value:.2f}%")

    base = alt.Chart(chart_data).encode(
        x=alt.X("metric:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset="version:N",
        color=alt.Color(
            "version:N",
            title="Experiment group",
            scale=alt.Scale(domain=[CONTROL_GROUP, TEST_GROUP], range=GROUP_COLORS),
        ),
        tooltip=[
            alt.Tooltip("version:N", title="Group"),
            alt.Tooltip("metric:N", title="Metric"),
            alt.Tooltip("retention:Q", title="Retention", format=".2f"),
        ],
    )
    bars = base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        y=alt.Y(
            "retention:Q",
            title="Retention (%)",
            scale=alt.Scale(domain=[0, 50]),
            axis=alt.Axis(gridColor="#E9EDF4"),
        )
    )
    labels = base.mark_text(dy=-10, color=NAVY, fontWeight=700).encode(
        y="retention:Q", text="label:N"
    )
    return (bars + labels).properties(height=340).configure_view(strokeWidth=0)


def round_distribution(data: pd.DataFrame, groups: list[str], limit: int) -> alt.Chart:
    """Create a normalized round distribution for the selected groups."""
    distribution = calculate_round_distribution(data, groups, limit)

    return (
        alt.Chart(distribution)
        .mark_line(strokeWidth=3, interpolate="monotone", point=False)
        .encode(
            x=alt.X(
                "round_bin:Q",
                title="Rounds played in the first 14 days",
                scale=alt.Scale(domain=[0, limit]),
            ),
            y=alt.Y(
                "share:Q",
                title="Share within each group",
                stack=None,
                axis=alt.Axis(format=".0%", gridColor="#E9EDF4"),
            ),
            color=alt.Color(
                "version:N",
                title="Experiment group",
                scale=alt.Scale(domain=[CONTROL_GROUP, TEST_GROUP], range=GROUP_COLORS),
                legend=alt.Legend(values=groups),
            ),

            tooltip=[
                alt.Tooltip("version:N", title="Group"),
                alt.Tooltip("round_bin:Q", title="Round bin"),
                alt.Tooltip("players:Q", title="Players", format=","),
                alt.Tooltip("share:Q", title="Share", format=".2%"),
            ],
        )
        .properties(height=360)
        .configure_view(strokeWidth=0)
    )


def confidence_interval_chart(results: pd.DataFrame) -> alt.Chart:
    """Show the estimated retention difference and its confidence interval."""
    zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
        color="#94A3B8", strokeDash=[5, 5]
    ).encode(x="zero:Q")
    intervals = alt.Chart(results).mark_rule(strokeWidth=5).encode(
        y=alt.Y("Metric:N", title=None, sort=["D1 retention", "D7 retention"]),
        x=alt.X(
            "CI low (pp):Q",
            title="Gate 40 minus Gate 30 (percentage points)",
            scale=alt.Scale(domain=[-1.6, 0.4]),
            axis=alt.Axis(gridColor="#E9EDF4"),
        ),
        x2="CI high (pp):Q",
        color=alt.Color(
            "Metric:N",
            legend=None,
            scale=alt.Scale(domain=["D1 retention", "D7 retention"], range=[AMBER, RED]),
        ),
    )
    points = alt.Chart(results).mark_point(filled=True, size=130).encode(
        y=alt.Y("Metric:N", sort=["D1 retention", "D7 retention"]),
        x="Difference (pp):Q",
        color=alt.Color(
            "Metric:N",
            legend=None,
            scale=alt.Scale(domain=["D1 retention", "D7 retention"], range=[AMBER, RED]),
        ),
        tooltip=[
            "Metric:N",
            alt.Tooltip("Difference (pp):Q", format=".2f"),
            alt.Tooltip("CI low (pp):Q", format=".2f"),
            alt.Tooltip("CI high (pp):Q", format=".2f"),
        ],
    )
    return (zero + intervals + points).properties(height=220).configure_view(strokeWidth=0)


data = get_data()
summary = calculate_summary(data)
d1 = compare_retention(data, "retention_1")
d7 = compare_retention(data, "retention_7")
allocation = check_group_allocation(data)

with st.sidebar:
    st.markdown("## 🎮 Exploration filters")
    st.caption(
        "These controls affect only the Player behavior and Dataset tabs. "
        "Overview and statistical results always use all 90,189 players."
    )
    selected_groups = st.multiselect(
        "Experiment groups",
        options=[CONTROL_GROUP, TEST_GROUP],
        default=[CONTROL_GROUP, TEST_GROUP],
    )
    max_rounds = int(data["sum_gamerounds"].quantile(0.99))
    round_limit = st.slider(
        "Behavior chart · maximum rounds",
        min_value=50,
        max_value=max_rounds,
        value=250,
        step=10,
        help="Changes the x-axis of the chart in Player behavior. It does not remove players from the experiment analysis.",
    )
    st.markdown("---")
    st.markdown("**Dataset status**")
    st.caption("✓ 90,189 unique players")
    st.caption("✓ No missing values")
    st.caption("✓ No duplicate player IDs")
    st.caption("ℹ If 50/50 was planned, verify the observed split")

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">MOBILE GAME A/B TEST</div>
        <h1>Progression Gate Experiment</h1>
        <p>Did moving the progression gate from Level 30 to Level 40 improve player retention?</p>
    </div>
    """,
    unsafe_allow_html=True,
)

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
with kpi_1:
    kpi_card("Players analyzed", f"{len(data):,}", "No missing or duplicate IDs")
with kpi_2:
    kpi_card("Gate 30 · D7", f"{d7['gate_30_rate']:.2%}", "Current experience")
with kpi_3:
    kpi_card("Gate 40 · D7", f"{d7['gate_40_rate']:.2%}", "Test experience")
with kpi_4:
    kpi_card(
        "D7 difference",
        f"{d7['difference_percentage_points']:.2f} pp",
        f"{d7['relative_difference_pct']:.2f}% relative change",
        negative=True,
    )

st.write("")
overview_tab, behavior_tab, statistics_tab, data_tab = st.tabs(
    ["Experiment overview", "Player behavior", "Statistical evidence", "Dataset"]
)

with overview_tab:
    st.write("")
    chart_column, decision_column = st.columns([1.65, 1], gap="large")
    with chart_column:
        with st.container(border=True):
            st.markdown('<div class="section-kicker">Primary comparison</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Retention by experiment group</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-copy">Gate 40 trails Gate 30 on both retention checkpoints.</div>',
                unsafe_allow_html=True,
            )
            st.altair_chart(retention_chart(summary), width="stretch")
    with decision_column:
        st.markdown(
            f"""
            <div class="decision">
                <div class="decision-label">RESULT SUMMARY</div>
                <h3>Do not roll out Gate 40 yet</h3>
                <p><strong>D1:</strong> The 0.59 pp decline is not statistically significant.</p>
                <p><strong>D7:</strong> Gate 40 is 0.82 pp lower, equal to a 4.31% relative decline. The result is statistically significant.</p>
                <div class="status-row">
                    <span class="status">D1 · Inconclusive</span>
                    <span class="status">D7 · Significant</span>
                    <span class="status">D7 p = {d7['p_value']:.4f}</span>
                </div>
                <p><strong>Next step:</strong> Confirm the planned allocation and validate assignment/tracking. If the experiment setup is valid, retain Gate 30 and investigate the D7 decline.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    quality_1, quality_2, quality_3 = st.columns(3)
    gate_30_players = int(summary.loc[summary.version == CONTROL_GROUP, "players"].iloc[0])
    gate_40_players = int(summary.loc[summary.version == TEST_GROUP, "players"].iloc[0])
    with quality_1:
        kpi_card("Gate 30 players", f"{gate_30_players:,}", f"{allocation['gate_30_share']:.2%} of the sample")
    with quality_2:
        kpi_card("Gate 40 players", f"{gate_40_players:,}", f"{allocation['gate_40_share']:.2%} of the sample")
    with quality_3:
        kpi_card(
            "Equal-split diagnostic",
            "Follow up",
            f"If planned 50/50: p = {allocation['p_value']:.4f}",
            negative=True,
        )

with behavior_tab:
    st.write("")
    if not selected_groups:
        st.warning("Select at least one experiment group from the sidebar.")
    else:
        st.info(
            f"Active view: {', '.join(selected_groups)} · chart range: 0–{round_limit} rounds"
        )
        with st.container(border=True):
            st.markdown('<div class="section-kicker">Exploratory view</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Rounds played by group</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-copy">Each line shows the percentage distribution within its own group. The range filter changes this exploratory chart only.</div>',
                unsafe_allow_html=True,
            )
            st.altair_chart(round_distribution(data, selected_groups, round_limit), width="stretch")

        selected_summary = (
            summary[summary["version"].isin(selected_groups)]
            .loc[:, ["version", "players", "average_rounds", "median_rounds", "p90_rounds"]]
            .rename(
                columns={
                    "version": "Experiment group",
                    "players": "Players",
                    "average_rounds": "Average rounds",
                    "median_rounds": "Median rounds",
                    "p90_rounds": "90th percentile",
                }
            )
        )
        st.dataframe(
            selected_summary.style.format(
                {
                    "Players": "{:,.0f}",
                    "Average rounds": "{:.2f}",
                    "Median rounds": "{:.0f}",
                    "90th percentile": "{:.0f}",
                }
            ),
            hide_index=True,
            width="stretch",
        )

with statistics_tab:
    st.write("")
    results = pd.DataFrame([d1, d7]).rename(
        columns={
            "metric": "Metric",
            "gate_30_rate": "Gate 30",
            "gate_40_rate": "Gate 40",
            "difference_percentage_points": "Difference (pp)",
            "relative_difference_pct": "Relative difference (%)",
            "confidence_interval_low_pp": "CI low (pp)",
            "confidence_interval_high_pp": "CI high (pp)",
            "p_value": "p-value",
        }
    )
    results["Metric"] = results["Metric"].map(
        {"retention_1": "D1 retention", "retention_7": "D7 retention"}
    )
    evidence_chart, evidence_text = st.columns([1.55, 1], gap="large")
    with evidence_chart:
        with st.container(border=True):
            st.markdown('<div class="section-kicker">Effect estimate</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Difference and 95% confidence interval</div>', unsafe_allow_html=True)
            st.altair_chart(confidence_interval_chart(results), width="stretch")
    with evidence_text:
        with st.container(border=True):
            st.markdown('<div class="section-kicker">Interpretation</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">D7 is the strongest observed signal</div>', unsafe_allow_html=True)
            st.write(
                "The D1 interval crosses zero, so the evidence is not strong enough "
                "to call that difference reliable."
            )
            st.write(
                "The D7 interval remains below zero. Together with a p-value of "
                f"{d7['p_value']:.4f}, it argues against rolling out Gate 40. "
                "The public data does not state the planned allocation. If it was "
                "50/50, the observed split (p = 0.0086) warrants an assignment and "
                "tracking check before the estimate is treated as causal."
            )

    st.dataframe(
        results[
            [
                "Metric", "Gate 30", "Gate 40", "Difference (pp)",
                "Relative difference (%)", "CI low (pp)", "CI high (pp)", "p-value",
            ]
        ].style.format(
            {
                "Gate 30": "{:.2%}", "Gate 40": "{:.2%}",
                "Difference (pp)": "{:.2f}", "Relative difference (%)": "{:.2f}",
                "CI low (pp)": "{:.2f}", "CI high (pp)": "{:.2f}", "p-value": "{:.4f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )

with data_tab:
    st.write("")
    filtered_data = (
        data[data["version"].isin(selected_groups)]
        if selected_groups
        else data.iloc[0:0]
    )
    if selected_groups:
        st.info(
            f"Showing rows for: {', '.join(selected_groups)} · "
            f"{len(filtered_data):,} players selected"
        )
    else:
        st.warning("Select at least one experiment group from the sidebar.")
    with st.container(border=True):
        st.markdown('<div class="section-kicker">Player-level data</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Dataset preview</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">The preview follows the experiment-group selection in the sidebar.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(filtered_data.head(100), hide_index=True, width="stretch")
        st.download_button(
            "Download selected rows",
            data=filtered_data.to_csv(index=False).encode("utf-8"),
            file_name="filtered_cookie_cats.csv",
            mime="text/csv",
        )

    with st.expander("Data source and statistical method"):
        st.markdown(
            """
            The analysis uses the publicly shared
            [Cookie Cats player-level dataset](https://github.com/ryanschaub/Mobile-Games-A-B-Testing-with-Cookie-Cats)
            included in this repository. D1 and D7 are compared with a two-sided,
            pooled two-proportion z-test at the 5% significance level. The displayed
            95% confidence interval uses the unpooled standard error for the
            difference in proportions.

            Both retention checkpoints are reported. No multiple-testing adjustment
            is applied because this is an exploratory analysis and the public source
            does not identify a pre-registered primary outcome.

            The equal-split diagnostic compares the observed group counts with a
            hypothetical 50/50 allocation. The source does not document the planned
            allocation, so the result is a validation question—not proof of a broken
            experiment.
            """
        )

st.write("")
st.markdown(
    """
    <div class="data-note">
        <strong>Scope:</strong> The dataset contains retention and gameplay-round information.
        It does not contain revenue, purchases, ads, session duration or verified gate-exposure events.
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Analysis and dashboard: Beyaz Karayılan · Portfolio project")
