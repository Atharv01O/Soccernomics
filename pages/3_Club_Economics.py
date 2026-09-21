# ============================================================
# SOCCERNOMICS — CLUB ECONOMICS & PSR COMPLIANCE
# ============================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import styles
from utils import (
    load_clubs,
    load_transfers,
    load_club_financials,
    load_club_financial_statement,
    calculate_club_psr_status,
    get_pl_club_ids,
    get_pl_transfers,
    format_eur_m,
    club_badge_style,
)

st.set_page_config(
    page_title="Soccernomics — Club Economics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()
styles.render_sidebar()

PLOT_BG = "rgba(0,0,0,0)"
GRID = "#1E2823"
TEXT = "#EAF2ED"
MUTED = "#8FA398"
GREEN = "#2FBF71"
AMBER = "#E8B75D"
RED = "#E06B6B"
BLUE = "#5B9BD5"


def short_club_name(name):
    replacements = {
        "Manchester City": "Man City",
        "Manchester United": "Man Utd",
        "Newcastle United": "Newcastle",
        "Tottenham Hotspur": "Tottenham",
        "West Ham United": "West Ham",
        "Wolverhampton Wanderers": "Wolves",
        "Nottingham Forest": "Nott'm Forest",
        "Brighton & Hove Albion": "Brighton",
        "Leicester City": "Leicester",
        "Sheffield United": "Sheffield Utd",
        "Sheffield Wednesday": "Sheffield Wed",
        "AFC Bournemouth": "Bournemouth",
    }
    return replacements.get(str(name), str(name))


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

financials = load_club_financials()
clubs = load_clubs()
transfers = load_transfers()
pl_ids = get_pl_club_ids(clubs)
pl_transfers = get_pl_transfers(transfers, pl_ids)

if financials.empty:
    st.error("Club financial dataset is unavailable.")
    st.stop()

all_clubs = sorted(financials["club"].unique().tolist())
financial_seasons = sorted(financials["season"].dropna().unique().tolist(), reverse=True)


# ---------------------------------------------------------------------------
# Header & Club Filter
# ---------------------------------------------------------------------------

head_col, select_col1, select_col2 = st.columns([2.5, 1.2, 1])

with head_col:
    styles.header(
        "Club Economics & PSR Compliance",
        "Deloitte Annual Review of Football Finance: club financial statements, wage sustainability, and Profitability & Sustainability Rules (PSR) modeling.",
    )

with select_col1:
    selected_club = st.selectbox("Select Club", all_clubs, index=0)

with select_col2:
    selected_season = st.selectbox("Financial Season", financial_seasons, index=0)

club_stmt = load_club_financial_statement(financials, selected_club)
season_df = financials[financials["season"] == selected_season].copy()

# Selected club single-season row
club_season_row = (
    club_stmt[club_stmt["season"] == selected_season].iloc[0]
    if not club_stmt.empty and selected_season in club_stmt["season"].values
    else (club_stmt.iloc[0] if not club_stmt.empty else None)
)

psr_status = calculate_club_psr_status(club_season_row)

st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Club Financial KPIs
# ---------------------------------------------------------------------------

if club_season_row is not None:
    rev_gbp = club_season_row.get("revenue_gbp", 0)
    wages_gbp = club_season_row.get("wage_cost_gbp", 0)
    wage_ratio = club_season_row.get("wage_to_revenue_pct", 0)
    op_gbp = club_season_row.get("operating_result_gbp", 0)
    net_debt_gbp = club_season_row.get("net_debt_gbp", 0)

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        styles.kpi_card(
            "Annual Turnover",
            f"£{rev_gbp / 1e6:.1f}M",
            f"Season {club_season_row.get('season', selected_season)}",
        )
    with k2:
        styles.kpi_card(
            "Total Wage Bill",
            f"£{wages_gbp / 1e6:.1f}M",
            f"{wage_ratio:.1f}% of total turnover",
        )
    with k3:
        styles.kpi_card(
            "Wage-to-Turnover Ratio",
            f"{wage_ratio:.1f}%",
            "UEFA benchmark: ≤70%",
            delta_positive=wage_ratio <= 70,
        )
    with k4:
        styles.kpi_card(
            "Operating Result",
            f"£{op_gbp / 1e6:+.1f}M",
            "operational earnings",
            delta_positive=op_gbp >= 0,
        )
    with k5:
        badge_cls = (
            "sc-psr-compliant" if psr_status["psr_status"] == "PSR Compliant"
            else ("sc-psr-watchlist" if psr_status["psr_status"] == "PSR Watchlist" else "sc-psr-risk")
        )
        st.markdown(
            f"""
            <div class="sc-kpi-card">
                <div class="sc-kpi-label">PSR Compliance Status</div>
                <div style="margin-top:0.4rem;">
                    <span class="sc-psr-badge {badge_cls}">{psr_status['psr_status']}</span>
                </div>
                <div style="color:#8FA398;font-size:0.82rem;margin-top:0.6rem;">
                    Based on reported results & wage burdens
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Section 1: Revenue Breakdown & Financial Trajectory
# ---------------------------------------------------------------------------

col_rev, col_trend = st.columns([1.2, 1], gap="medium")

with col_rev:
    with styles.panel():
        styles.section_label(f"Revenue Stream Breakdown · {selected_club}")
        st.caption("Distribution of club turnover across Matchday, Broadcast, and Commercial activities.")

        if club_season_row is not None:
            matchday = float(club_season_row.get("matchday_revenue_gbp", 0) or 0) / 1e6
            broadcast = float(club_season_row.get("broadcast_revenue_gbp", 0) or 0) / 1e6
            commercial = float(club_season_row.get("commercial_revenue_gbp", 0) or 0) / 1e6

            # If detailed split missing, fallback to operating result vs revenue
            if matchday == 0 and broadcast == 0 and commercial == 0:
                matchday = rev_gbp * 0.15 / 1e6
                broadcast = rev_gbp * 0.55 / 1e6
                commercial = rev_gbp * 0.30 / 1e6

            donut_fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["Broadcast", "Commercial", "Matchday"],
                        values=[broadcast, commercial, matchday],
                        hole=0.55,
                        marker=dict(colors=[BLUE, GREEN, AMBER]),
                        textinfo="label+percent",
                        hovertemplate="<b>%{label}</b>: £%{value:.1f}M (%{percent})<extra></extra>",
                    )
                ]
            )

            donut_fig.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=11),
                showlegend=False,
            )
            st.plotly_chart(donut_fig, width="stretch", config={"displayModeBar": False})

with col_trend:
    with styles.panel():
        styles.section_label(f"Turnover vs Wage History · {selected_club}")
        st.caption("Multi-season comparison of reported turnover against annual wage bills.")

        if not club_stmt.empty:
            sorted_stmt = club_stmt.sort_values("season").copy()
            trend_fig = go.Figure()

            trend_fig.add_trace(
                go.Bar(
                    x=sorted_stmt["season"],
                    y=sorted_stmt["revenue_m_gbp"],
                    name="Turnover (£M)",
                    marker=dict(color=GREEN, opacity=0.9),
                    hovertemplate="Season %{x}<br>Turnover: £%{y:.1f}M<extra></extra>",
                )
            )
            trend_fig.add_trace(
                go.Bar(
                    x=sorted_stmt["season"],
                    y=sorted_stmt["wages_m_gbp"],
                    name="Wage Cost (£M)",
                    marker=dict(color=AMBER, opacity=0.85),
                    hovertemplate="Season %{x}<br>Wages: £%{y:.1f}M<extra></extra>",
                )
            )

            trend_fig.update_layout(
                height=320,
                barmode="group",
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=11),
                xaxis=dict(gridcolor=GRID),
                yaxis=dict(title="£ Millions", gridcolor=GRID),
                legend=dict(orientation="h", y=1.05, x=0),
            )
            st.plotly_chart(trend_fig, width="stretch", config={"displayModeBar": False})

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Section 2: Interactive PSR & Financial Sustainability Simulator
# ---------------------------------------------------------------------------

styles.section_label(f"Premier League Profitability & Sustainability Rules (PSR) Simulator · {selected_club}")
st.caption(
    "Premier League rules limit 3-year aggregated accounting losses to £105M (assuming £90M secure owner funding). "
    "Use this simulator to test how annual transfer amortisation and proposed outlays affect PSR compliance."
)

with styles.panel():
    sim_col1, sim_col2, sim_col3 = st.columns([1, 1, 1.2], gap="large")

    with sim_col1:
        base_op = float(club_season_row.get("operating_m_gbp", 0) if club_season_row is not None else 0)
        annual_amort_input = st.number_input(
            "Estimated Annual Player Amortisation (£M)",
            min_value=0.0,
            max_value=250.0,
            value=45.0,
            step=5.0,
            help="Total annual accounting amortisation charge for player registrations.",
        )

    with sim_col2:
        extra_deductions = st.number_input(
            "Allowable PSR Deductions (£M/yr)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=2.5,
            help="Youth academy, women's football, community, and infrastructure costs excluded from PSR loss calculations.",
        )

    with sim_col3:
        planned_outlay = st.number_input(
            "Proposed New Transfer Spend (£M)",
            min_value=0.0,
            max_value=300.0,
            value=60.0,
            step=10.0,
            help="New transfer fee committed (amortised over 5 years).",
        )

    # Calculation logic
    new_amortisation = planned_outlay / 5.0
    total_amortisation = annual_amort_input + new_amortisation
    annual_psr_result = base_op - total_amortisation + extra_deductions
    est_3yr_psr_loss = annual_psr_result * 3.0
    psr_limit = -105.0

    buffer = est_3yr_psr_loss - psr_limit  # positive means above -105M (safe)

    st.markdown("<hr style='border-color:#1E2823;margin:1rem 0;'>", unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        styles.kpi_card("Base Operating Result", f"£{base_op:+.1f}M", "before amortisation")
    with r2:
        styles.kpi_card("Total Amortisation Charge", f"£{total_amortisation:.1f}M/yr", f"includes £{new_amortisation:.1f}M new amortisation")
    with r3:
        styles.kpi_card(
            "Est. 3-Year PSR Position",
            f"£{est_3yr_psr_loss:+.1f}M",
            "3-year aggregate loss",
            delta_positive=est_3yr_psr_loss >= psr_limit,
        )
    with r4:
        if buffer >= 0:
            styles.kpi_card("PSR Safety Margin", f"£{buffer:.1f}M", "headroom before £105M loss cap", delta_positive=True)
        else:
            styles.kpi_card("Estimated Breach", f"£{abs(buffer):.1f}M", "exceeds maximum allowed £105M loss", delta_positive=False)

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Section 3: League-Wide Financial Comparison Matrix
# ---------------------------------------------------------------------------

styles.section_label(f"Premier League Financial Statement Ledger · {selected_season}")
st.caption("Comprehensive financial metrics across all reported Premier League clubs from Deloitte accounts.")

with styles.panel():
    if not season_df.empty:
        disp_df = season_df.copy()
        disp_df["Club"] = disp_df["club"].apply(short_club_name)
        disp_df["Revenue (£M)"] = disp_df["revenue_gbp"] / 1e6
        disp_df["Wages (£M)"] = disp_df["wage_cost_gbp"] / 1e6
        disp_df["Wage Ratio"] = disp_df["wage_to_revenue_pct"].apply(lambda v: f"{v:.1f}%")
        disp_df["Operating Result (£M)"] = disp_df["operating_result_gbp"] / 1e6
        disp_df["Net Debt (£M)"] = disp_df["net_debt_gbp"] / 1e6
        disp_df["Net Funds / Debt (£M)"] = disp_df["net_funds_debt_gbp"] / 1e6

        table_cols = [
            "Club", "Revenue (£M)", "Wages (£M)", "Wage Ratio",
            "Operating Result (£M)", "Net Debt (£M)", "Net Funds / Debt (£M)"
        ]

        st.dataframe(
            disp_df[table_cols].sort_values("Revenue (£M)", ascending=False).style.format({
                "Revenue (£M)": "£{:.1f}M",
                "Wages (£M)": "£{:.1f}M",
                "Operating Result (£M)": "£{:+.1f}M",
                "Net Debt (£M)": "£{:.1f}M",
                "Net Funds / Debt (£M)": "£{:+.1f}M",
            }),
            hide_index=True,
            width="stretch",
            height=380,
        )

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

with st.expander("Methodology & Financial Disclosures"):
    st.markdown(
        """
        - **Data Source:** Deloitte Annual Review of Football Finance (Premier League club statutory financial filings).
        - **PSR Framework:** Premier League Profitability & Sustainability Rules assess allowable loss over a 3-year rolling monitoring period. The maximum permitted loss is £105M, provided £90M is covered by equity funding from owners.
        - **Allowable Deductions:** Costs associated with women's football, youth academy, community initiatives, and stadium/training ground infrastructure are excluded from PSR calculations.
        - **Amortisation Accounting:** Player acquisition fees are capitalised on the balance sheet and amortised straight-line over contract duration.
        """
    )

st.markdown(
    "<div style='height:1rem'></div><div style='text-align:center;color:#5C6E66;font-size:.75rem;'>"
    "Soccernomics · Football. Data. Economics."
    "</div>",
    unsafe_allow_html=True,
)
