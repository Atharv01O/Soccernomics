# ============================================================
# SOCCERNOMICS — TRANSFERS
# ============================================================

import os
import sys

# Allow pages/ files to import project modules
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import styles
from utils import (
    load_clubs,
    load_transfers,
    load_players,
    get_pl_club_ids,
    get_pl_transfers,
    format_eur_m,
    calculate_value_gap_and_premium,
    club_transfer_balance_matrix,
    trading_efficiency_by_club,
    calculate_contract_amortisation,
    disposal_profit_loss,
    club_badge_style,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Soccernomics — Transfers",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject()
styles.render_sidebar()


# ============================================================
# CHART THEME
# ============================================================

PLOT_BG = "rgba(0,0,0,0)"
GRID = "#223029"
TEXT = "#EAF2ED"
MUTED = "#8FA398"

GREEN = "#2FBF71"
AMBER = "#E8B75D"
RED = "#E06B6B"
BLUE = "#5B9BD5"


# ============================================================
# DATA
# ============================================================

clubs = load_clubs()
players = load_players()
transfers = load_transfers()

pl_ids = get_pl_club_ids(clubs)
pl_transfers = get_pl_transfers(transfers, pl_ids).copy()


# ============================================================
# HELPERS
# ============================================================

def season_key(season):
    """Sort seasons chronologically (e.g. 03/04 -> 3, 24/25 -> 24)."""
    try:
        return int(str(season).split("/")[0])
    except Exception:
        return 999


def short_club_name(name):
    """Clean and standardize long club names for charts and cards."""
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


# ============================================================
# SEASONS
# ============================================================

all_seasons = sorted(
    pl_transfers["transfer_season"].dropna().unique().tolist(),
    key=season_key,
)

# Exclude incomplete 26/27 from completed historical selector
completed_seasons = [
    season for season in all_seasons
    if not str(season).startswith("26")
]

if not completed_seasons:
    completed_seasons = all_seasons

# Premier League club names
pl_buying_clubs = set(
    pl_transfers[pl_transfers["to_club_id"].isin(pl_ids)]["to_club_name"].dropna().unique()
)
pl_selling_clubs = set(
    pl_transfers[pl_transfers["from_club_id"].isin(pl_ids)]["from_club_name"].dropna().unique()
)
pl_club_names = sorted(pl_buying_clubs | pl_selling_clubs)


# ============================================================
# HEADER
# ============================================================

header_col, season_col = st.columns([2.8, 1])

with header_col:
    styles.header(
        "Transfers",
        "Follow the money — explore how fees and player market values move through the Premier League.",
    )

with season_col:
    selected_season = st.selectbox(
        "Season",
        completed_seasons,
        index=len(completed_seasons) - 1,
    )


# ============================================================
# FILTERS
# ============================================================

f1, f2, f3, f4 = st.columns([1.25, 1.25, 1.25, 1.5])

with f1:
    selected_club = st.selectbox(
        "Club",
        ["All Premier League clubs"] + pl_club_names,
    )

with f2:
    direction = st.selectbox(
        "Direction",
        ["All transfers", "Incoming", "Outgoing"],
    )

with f3:
    window_filter = st.selectbox(
        "Transfer Window",
        ["All Windows", "Summer Window", "Winter Window"],
    )

with f4:
    season_fees = pl_transfers[
        pl_transfers["transfer_season"] == selected_season
    ]["transfer_fee"].dropna()

    max_fee_m = max(10, int(season_fees.max() / 1_000_000) + 5) if not season_fees.empty else 150

    minimum_fee_m = st.slider(
        "Minimum transfer fee",
        min_value=0,
        max_value=max_fee_m,
        value=0,
        step=5,
        format="€%dM",
    )

minimum_fee = minimum_fee_m * 1_000_000


# ============================================================
# FILTER APPLICATION
# ============================================================

season_data = pl_transfers[pl_transfers["transfer_season"] == selected_season].copy()
paid_season = season_data[season_data["transfer_fee"].notna() & (season_data["transfer_fee"] > 0)].copy()

filtered = paid_season.copy()

if selected_club != "All Premier League clubs":
    if direction == "Incoming":
        filtered = filtered[filtered["to_club_name"] == selected_club]
    elif direction == "Outgoing":
        filtered = filtered[filtered["from_club_name"] == selected_club]
    else:
        filtered = filtered[
            (filtered["to_club_name"] == selected_club) | (filtered["from_club_name"] == selected_club)
        ]

if direction == "Incoming":
    filtered = filtered[filtered["to_club_id"].isin(pl_ids)]
elif direction == "Outgoing":
    filtered = filtered[filtered["from_club_id"].isin(pl_ids)]

if window_filter == "Summer Window":
    filtered = filtered[filtered["transfer_date"].dt.month.isin([6, 7, 8, 9])]
elif window_filter == "Winter Window":
    filtered = filtered[filtered["transfer_date"].dt.month.isin([1, 2])]

filtered = filtered[filtered["transfer_fee"] >= minimum_fee].copy()


# ============================================================
# KPI ROW
# ============================================================

incoming = filtered[filtered["to_club_id"].isin(pl_ids)]
outgoing = filtered[filtered["from_club_id"].isin(pl_ids)]

spending = incoming["transfer_fee"].sum()
income = outgoing["transfer_fee"].sum()
net_spend = spending - income
paid_count = len(filtered)
largest = filtered["transfer_fee"].max() if not filtered.empty else None

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    styles.kpi_card("Transfer spending", format_eur_m(spending), f"{len(incoming)} buys")
with k2:
    styles.kpi_card("Transfer income", format_eur_m(income), f"{len(outgoing)} sales")
with k3:
    styles.kpi_card(
        "Net transfer spend",
        format_eur_m(net_spend),
        "Spending − Income",
        delta_positive=net_spend <= 0,
    )
with k4:
    styles.kpi_card("Paid transfers", f"{paid_count:,}", f"Min fee €{minimum_fee_m}M")
with k5:
    styles.kpi_card(
        "Largest transfer",
        format_eur_m(largest) if largest is not None else "—",
        filtered.nlargest(1, "transfer_fee").iloc[0]["player_name"] if not filtered.empty else None,
    )

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 1: TRANSFER FEE VS RECORDED MARKET VALUE
# ============================================================

styles.section_label(f"Transfer Fee vs Recorded Market Value · {selected_season}")
st.caption(
    "How do agreed fees compare with Transfermarkt's market valuation at the time of transfer? "
    "Value Gap = Market Value − Fee (positive = below market value). "
    "Premium % = (Fee − Market Value) / Market Value × 100."
)

with_pricing = calculate_value_gap_and_premium(paid_season)
priced_season = with_pricing[with_pricing["market_value_in_eur"].notna() & (with_pricing["market_value_in_eur"] > 0)].copy()

if not priced_season.empty:
    chart_col, cards_col = st.columns([1.5, 1], gap="medium")

    with chart_col:
        with styles.panel():
            styles.section_label("Valuation vs. Fee Scatter")
            st.caption("Dots above the dashed line represent transfers paid at a premium; dots below were signed at a discount.")

            max_val = max(
                priced_season["market_value_in_eur"].max() / 1e6,
                priced_season["transfer_fee"].max() / 1e6,
            ) + 10

            fig = go.Figure()

            # Par line (Fee == Market Value)
            fig.add_trace(
                go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode="lines",
                    name="Fair Value Benchmark (1:1)",
                    line=dict(color="#3A4B43", width=1.5, dash="dash"),
                    hoverinfo="skip",
                )
            )

            # Scatter points color-coded by tier
            color_map = {
                "Premium (>15%)": RED,
                "Fair Value (±15%)": BLUE,
                "Discount (<-15%)": GREEN,
            }

            for tier, t_color in color_map.items():
                tier_df = priced_season[priced_season["pricing_tier"] == tier]
                if not tier_df.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=tier_df["market_value_in_eur"] / 1e6,
                            y=tier_df["transfer_fee"] / 1e6,
                            mode="markers",
                            name=tier,
                            marker=dict(size=8, color=t_color, opacity=0.85),
                            customdata=tier_df[["player_name", "from_club_name", "to_club_name", "transfer_fee", "market_value_in_eur", "premium_pct"]],
                            hovertemplate=(
                                "<b>%{customdata[0]}</b><br>"
                                "%{customdata[1]} → %{customdata[2]}<br>"
                                "Fee: €%{customdata[3]:,.0f}<br>"
                                "Market Value: €%{customdata[4]:,.0f}<br>"
                                "Differential: %{customdata[5]:+.1f}%<extra></extra>"
                            ),
                        )
                    )

            fig.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=11),
                xaxis=dict(title="Market Value at Transfer (€M)", gridcolor=GRID, zeroline=False),
                yaxis=dict(title="Agreed Transfer Fee (€M)", gridcolor=GRID, zeroline=False),
                legend=dict(orientation="h", y=1.04, x=0),
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with cards_col:
        with styles.panel():
            styles.section_label("Standout Market Bargain")
            discounts = priced_season[priced_season["to_club_id"].isin(pl_ids)].sort_values("value_gap", ascending=False)
            if not discounts.empty and discounts.iloc[0]["value_gap"] > 0:
                top_deal = discounts.iloc[0]
                st.markdown(
                    f"""
                    <div style="background:#111914;border:1px solid #26362e;border-radius:10px;padding:12px 14px;margin-bottom:12px;">
                        <div style="color:#2FBF71;font-size:0.75rem;font-weight:700;letter-spacing:1px;">LARGEST VALUE GAP (BELOW BENCHMARK)</div>
                        <div style="color:#EAF2ED;font-size:1.15rem;font-weight:700;margin-top:4px;">{top_deal['player_name']}</div>
                        <div style="color:#8FA398;font-size:0.82rem;">{short_club_name(top_deal['from_club_name'])} → {short_club_name(top_deal['to_club_name'])}</div>
                        <div style="margin-top:8px;font-size:0.9rem;color:#D7E4DE;">
                            Fee: <b style="color:#EAF2ED">{format_eur_m(top_deal['transfer_fee'])}</b> · 
                            Valuation: <b style="color:#EAF2ED">{format_eur_m(top_deal['market_value_in_eur'])}</b>
                        </div>
                        <div style="color:#2FBF71;font-weight:700;font-size:1rem;margin-top:4px;">
                            {format_eur_m(top_deal['value_gap'])} below valuation ({top_deal['discount_pct']:.0f}% discount)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            styles.section_label("Standout Market Premium")
            premiums = priced_season[priced_season["to_club_id"].isin(pl_ids)].sort_values("premium_pct", ascending=False)
            if not premiums.empty and premiums.iloc[0]["premium_pct"] > 0:
                top_prem = premiums.iloc[0]
                st.markdown(
                    f"""
                    <div style="background:#111914;border:1px solid #26362e;border-radius:10px;padding:12px 14px;">
                        <div style="color:#E06B6B;font-size:0.75rem;font-weight:700;letter-spacing:1px;">LARGEST VALUATION PREMIUM PAID</div>
                        <div style="color:#EAF2ED;font-size:1.15rem;font-weight:700;margin-top:4px;">{top_prem['player_name']}</div>
                        <div style="color:#8FA398;font-size:0.82rem;">{short_club_name(top_prem['from_club_name'])} → {short_club_name(top_prem['to_club_name'])}</div>
                        <div style="margin-top:8px;font-size:0.9rem;color:#D7E4DE;">
                            Fee: <b style="color:#EAF2ED">{format_eur_m(top_prem['transfer_fee'])}</b> · 
                            Valuation: <b style="color:#EAF2ED">{format_eur_m(top_prem['market_value_in_eur'])}</b>
                        </div>
                        <div style="color:#E06B6B;font-weight:700;font-size:1rem;margin-top:4px;">
                            {top_prem['premium_pct']:+.0f}% premium over recorded valuation
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 2: INTERACTIVE TRANSFER LEDGER
# ============================================================

styles.section_label(f"Transfer Ledger · {selected_season}")
st.caption("Complete transactional record of moves matching active filters, including market valuations, value gaps, and pricing classification.")

with styles.panel():
    if not filtered.empty:
        ledger = calculate_value_gap_and_premium(filtered)
        ledger["Date"] = pd.to_datetime(ledger["transfer_date"], errors="coerce").dt.strftime("%d %b %Y")
        ledger["Fee (€M)"] = pd.to_numeric(ledger["transfer_fee"], errors="coerce") / 1e6
        ledger["Market Value (€M)"] = pd.to_numeric(ledger["market_value_in_eur"], errors="coerce") / 1e6
        ledger["Value Gap (€M)"] = pd.to_numeric(ledger["value_gap"], errors="coerce") / 1e6
        ledger["Premium %"] = ledger["premium_pct"].apply(lambda p: f"{p:+.1f}%" if pd.notna(p) else "—")

        display_cols = [
            "player_name", "from_club_name", "to_club_name", "Date",
            "Fee (€M)", "Market Value (€M)", "Value Gap (€M)", "Premium %", "pricing_tier"
        ]

        table_df = ledger[display_cols].rename(columns={
            "player_name": "Player",
            "from_club_name": "From Club",
            "to_club_name": "To Club",
            "pricing_tier": "Pricing Classification",
        })

        st.dataframe(
            table_df.style.format({
                "Fee (€M)": "€{:.1f}M",
                "Market Value (€M)": lambda v: f"€{v:.1f}M" if pd.notna(v) and v > 0 else "—",
                "Value Gap (€M)": lambda v: f"€{v:+.1f}M" if pd.notna(v) else "—",
            }),
            hide_index=True,
            width="stretch",
            height=380,
        )
    else:
        st.caption("No transfers match the selected filters.")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 3: CLUB TRANSFER BALANCE MATRIX
# ============================================================

styles.section_label(f"Club Transfer Balance Matrix · {selected_season}")
st.caption("Aggregated spending, transfer income, and net transfer positions for all active Premier League clubs.")

with styles.panel():
    matrix = club_transfer_balance_matrix(pl_transfers, pl_ids, season=selected_season)
    if not matrix.empty:
        matrix["Club"] = matrix["club"].apply(short_club_name)
        matrix["Spending"] = matrix["spending"] / 1e6
        matrix["Transfer Income"] = matrix["income"] / 1e6
        matrix["Net Spend"] = matrix["net_spend"] / 1e6
        matrix["Avg Buy"] = matrix["avg_buy"] / 1e6
        matrix["Max Buy"] = matrix["max_buy"] / 1e6
        matrix["Max Sale"] = matrix["max_sale"] / 1e6

        matrix_disp = matrix[[
            "Club", "Spending", "Transfer Income", "Net Spend",
            "buys_count", "sales_count", "Avg Buy", "Max Buy", "Max Sale"
        ]].rename(columns={
            "buys_count": "Buys (n)",
            "sales_count": "Sales (n)",
        })

        st.dataframe(
            matrix_disp.style.format({
                "Spending": "€{:.1f}M",
                "Transfer Income": "€{:.1f}M",
                "Net Spend": "€{:+.1f}M",
                "Avg Buy": lambda v: f"€{v:.1f}M" if v > 0 else "—",
                "Max Buy": lambda v: f"€{v:.1f}M" if v > 0 else "—",
                "Max Sale": lambda v: f"€{v:.1f}M" if v > 0 else "—",
            }),
            hide_index=True,
            width="stretch",
            height=380,
        )
    else:
        st.caption("No club balance data available for this season.")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 4: SPENDING VS INCOME & NET BALANCE
# ============================================================

col_left, col_right = st.columns([1.25, 1], gap="medium")

with col_left:
    with styles.panel():
        styles.section_label("Club Spending vs Transfer Income")
        st.caption("Position of each club relative to the diagonal break-even line.")

        if not matrix.empty:
            scatter_fig = go.Figure()
            max_axis = max(matrix["Spending"].max(), matrix["Transfer Income"].max()) + 15

            # 45-degree line
            scatter_fig.add_trace(
                go.Scatter(
                    x=[0, max_axis],
                    y=[0, max_axis],
                    mode="lines",
                    line=dict(color="#3A4B43", width=1.5, dash="dot"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # Scatter dots
            scatter_fig.add_trace(
                go.Scatter(
                    x=matrix["Spending"],
                    y=matrix["Transfer Income"],
                    mode="markers+text",
                    text=matrix["Club"],
                    textposition="top center",
                    textfont=dict(size=9, color=TEXT),
                    marker=dict(
                        size=9,
                        color=[GREEN if net < 0 else AMBER for net in matrix["net_spend"]],
                        opacity=0.9,
                    ),
                    customdata=matrix[["club", "spending", "income", "net_spend"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Spending: €%{customdata[1]:,.0f}<br>"
                        "Transfer Income: €%{customdata[2]:,.0f}<br>"
                        "Net Spend: €%{customdata[3]:,.0f}<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

            scatter_fig.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=10),
                xaxis=dict(title="Transfer Spending (€M)", gridcolor=GRID, zeroline=False),
                yaxis=dict(title="Transfer Income (€M)", gridcolor=GRID, zeroline=False),
            )
            st.plotly_chart(scatter_fig, width="stretch", config={"displayModeBar": False})

with col_right:
    with styles.panel():
        styles.section_label("Net Transfer Spend Leaderboard")
        st.caption("Net spend = Spending − Income. Positive = Net Spender; Negative = Net Seller.")

        if not matrix.empty:
            sorted_matrix = matrix.sort_values("net_spend", ascending=True)
            bar_fig = go.Figure()

            bar_fig.add_trace(
                go.Bar(
                    x=sorted_matrix["Net Spend"],
                    y=sorted_matrix["Club"],
                    orientation="h",
                    marker=dict(
                        color=[GREEN if v < 0 else AMBER for v in sorted_matrix["Net Spend"]],
                        opacity=0.85,
                    ),
                    customdata=sorted_matrix["net_spend"],
                    hovertemplate="<b>%{y}</b><br>Net Spend: €%{customdata:,.0f}<extra></extra>",
                    showlegend=False,
                )
            )

            bar_fig.add_vline(x=0, line_color=GRID, line_dash="dot", line_width=1)

            bar_fig.update_layout(
                height=340,
                margin=dict(l=5, r=10, t=5, b=5),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=10),
                xaxis=dict(title="Net Spend (€M)", gridcolor=GRID, zeroline=False),
                yaxis=dict(gridcolor=GRID),
            )
            st.plotly_chart(bar_fig, width="stretch", config={"displayModeBar": False})

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 5: TOP INTRA-PREMIER LEAGUE FLOWS & TRANSFER RETURN
# ============================================================

flow_col, return_col = st.columns([1.2, 1], gap="medium")

with flow_col:
    with styles.panel():
        styles.section_label(f"Top Intra-League Flows · {selected_season}")
        st.caption("Largest transfer deals transacted directly between two Premier League clubs.")

        intra_pl = paid_season[
            paid_season["from_club_id"].isin(pl_ids) & paid_season["to_club_id"].isin(pl_ids)
        ].copy()

        if not intra_pl.empty:
            intra_grouped = (
                intra_pl.groupby(["from_club_name", "to_club_name"], as_index=False)["transfer_fee"]
                .sum()
                .nlargest(7, "transfer_fee")
            )
            intra_grouped["flow"] = (
                intra_grouped["from_club_name"].apply(short_club_name)
                + "  →  "
                + intra_grouped["to_club_name"].apply(short_club_name)
            )
            intra_grouped = intra_grouped.sort_values("transfer_fee", ascending=True)

            flow_fig = go.Figure()
            flow_fig.add_trace(
                go.Bar(
                    x=intra_grouped["transfer_fee"] / 1e6,
                    y=intra_grouped["flow"],
                    orientation="h",
                    marker=dict(color=GREEN, opacity=0.9),
                    customdata=intra_grouped["transfer_fee"],
                    hovertemplate="<b>%{y}</b><br>Volume: €%{customdata:,.0f}<extra></extra>",
                    showlegend=False,
                )
            )
            flow_fig.update_layout(
                height=300,
                margin=dict(l=5, r=15, t=5, b=5),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=11),
                xaxis=dict(title="Transfer Volume (€M)", gridcolor=GRID, zeroline=False),
                yaxis=dict(gridcolor=GRID),
            )
            st.plotly_chart(flow_fig, width="stretch", config={"displayModeBar": False})
        else:
            st.caption("No intra-Premier League moves recorded for this season.")

with return_col:
    with styles.panel():
        styles.section_label("Transfer Return (Tracked Buy → Sell)")
        st.caption("Historical transfer cash recovery per €1 spent on players later sold (min. 5 tracked deals).")

        trading = trading_efficiency_by_club(transfers, pl_ids, min_trades=5).head(6)
        if not trading.empty:
            for club_name, row in trading.iterrows():
                roi = row["profit_per_euro_invested"]
                initials, color = club_badge_style(club_name)
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:0.6rem;padding:0.4rem 0;border-bottom:1px solid #223029;">
                        {styles.club_badge(initials, color, 26)}
                        <span style="flex:1;color:#D7E4DE;font-size:0.88rem;">{short_club_name(club_name)}</span>
                        <span style="color:{GREEN};font-weight:700;font-size:0.9rem;">{roi:.2f}x</span>
                        <span style="color:#5C6E66;font-size:0.75rem;">n={int(row['n_trades'])}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.caption("Strictly defined as Sale Fees / Purchase Fees. Excludes wages, agent fees, and amortisation.")
        else:
            st.caption("No repeat trades meet the threshold.")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 6: CONTRACT AMORTISATION & BOOK VALUE SIMULATOR
# ============================================================

styles.section_label("Contract Amortisation & Book Value Simulator")
st.caption(
    "In club accounting, transfer fees are capitalised as intangible assets and amortised straight-line over the contract length. "
    "Use this tool to simulate annual P&L charge, unamortised book value, and Profit/Loss on disposal if sold early."
)

with styles.panel():
    sim1, sim2, sim3, sim4 = st.columns([1, 1, 1, 1], gap="medium")

    with sim1:
        sim_fee_m = st.number_input("Transfer Fee (€M)", min_value=1.0, max_value=300.0, value=75.0, step=5.0)
    with sim2:
        sim_contract_yrs = st.number_input("Contract Length (Years)", min_value=1, max_value=9, value=5, step=1)
    with sim3:
        sim_wage_k = st.number_input("Weekly Wage (£k/wk)", min_value=0.0, max_value=600.0, value=150.0, step=10.0)
    with sim4:
        sim_sale_yr = st.slider("Simulate Sale in Year", min_value=1, max_value=int(sim_contract_yrs), value=3)

    amort_res = calculate_contract_amortisation(
        fee_eur=sim_fee_m * 1e6,
        contract_years=sim_contract_yrs,
        weekly_wage_gbp=sim_wage_k * 1000,
    )

    disp_res = disposal_profit_loss(
        fee_eur=sim_fee_m * 1e6,
        contract_years=sim_contract_yrs,
        sale_year=sim_sale_yr,
        sale_fee_eur=sim_fee_m * 0.7 * 1e6, # Assume 70% value retention on sale
    )

    st.markdown("<hr style='border-color:#1E2823;margin:0.8rem 0;'>", unsafe_allow_html=True)

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        styles.kpi_card("Annual Amortisation Charge", format_eur_m(amort_res["annual_amortisation_eur"]), f"€{sim_fee_m:.1f}M over {sim_contract_yrs} yrs")
    with a2:
        styles.kpi_card("Annual Wage Expense", format_eur_m(amort_res["annual_wage_eur"]), f"£{sim_wage_k:.0f}k / week")
    with a3:
        styles.kpi_card("Total Annual P&L Hit", format_eur_m(amort_res["annual_pl_hit_eur"]), "Amortisation + Wages")
    with a4:
        styles.kpi_card(
            f"Book Value in Year {sim_sale_yr}",
            format_eur_m(disp_res["book_value_at_sale"]),
            f"unamortised asset value at Year {sim_sale_yr}",
        )

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # Schedule Table & Amortisation Chart
    c_chart, c_table = st.columns([1.2, 1], gap="medium")

    with c_chart:
        sched_df = amort_res["schedule"].copy()
        sched_df["Book Value (€M)"] = sched_df["book_value_eur"] / 1e6
        sched_df["Cum Amortisation (€M)"] = sched_df["cum_amortisation_eur"] / 1e6

        fig_amort = go.Figure()
        fig_amort.add_trace(
            go.Scatter(
                x=sched_df["year"],
                y=sched_df["Book Value (€M)"],
                mode="lines+markers",
                name="Remaining Book Value",
                line=dict(color=GREEN, width=2.5),
                marker=dict(size=6, color=GREEN),
                hovertemplate="Year %{x}<br>Book Value: €%{y:.1f}M<extra></extra>",
            )
        )
        fig_amort.add_trace(
            go.Scatter(
                x=sched_df["year"],
                y=sched_df["Cum Amortisation (€M)"],
                mode="lines+markers",
                name="Cumulative Amortisation",
                line=dict(color=AMBER, width=2, dash="dot"),
                marker=dict(size=6, color=AMBER),
                hovertemplate="Year %{x}<br>Cum Amortisation: €%{y:.1f}M<extra></extra>",
            )
        )

        fig_amort.update_layout(
            height=270,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT, size=10),
            xaxis=dict(title="Contract Year", gridcolor=GRID),
            yaxis=dict(title="€ Millions", gridcolor=GRID),
            legend=dict(orientation="h", y=1.05, x=0),
        )
        st.plotly_chart(fig_amort, width="stretch", config={"displayModeBar": False})

    with c_table:
        sched_disp = sched_df.copy()
        sched_disp["Year"] = sched_disp["year"].apply(lambda y: f"Year {y}")
        sched_disp["Book Value"] = (sched_disp["book_value_eur"] / 1e6).apply(lambda v: f"€{v:.1f}M")
        sched_disp["Cum Cost"] = (sched_disp["cum_total_cost_eur"] / 1e6).apply(lambda v: f"€{v:.1f}M")

        st.dataframe(
            sched_disp[["Year", "Book Value", "Cum Cost"]].rename(columns={"Cum Cost": "Cumulative Total Outlay"}),
            hide_index=True,
            width="stretch",
            height=250,
        )

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# SECTION 7: FINANCIAL DEAL TICKER
# ============================================================


ticker_deals = paid_season.nlargest(12, "transfer_fee")

if not ticker_deals.empty:
    ticker_cards = []
    for _, row in ticker_deals.iterrows():
        p_name = str(row["player_name"])
        f_name = short_club_name(row["from_club_name"])
        t_name = short_club_name(row["to_club_name"])
        f_val = format_eur_m(row["transfer_fee"])
        ticker_cards.append(
            f'<div class="transfer-card"><div class="player">{p_name}</div><div class="route">{f_name} <span>→</span> {t_name}</div><div class="fee">{f_val}</div></div>'
        )

    tape_html = "".join(ticker_cards) * 2

    ticker_code = f"""
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
        .ticker-wrapper {{ width: 100%; overflow: hidden; border: 1px solid #223029; border-radius: 10px; background: #0E1613; }}
        .ticker-track {{ display: flex; width: max-content; animation: soccernomics-scroll 35s linear infinite; }}
        .ticker-wrapper:hover .ticker-track {{ animation-play-state: paused; }}
        .transfer-card {{ width: 220px; min-width: 220px; padding: 10px 14px; border-right: 1px solid #223029; }}
        .player {{ color: #EAF2ED; font-family: Inter, sans-serif; font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .route {{ margin-top: 4px; color: #8FA398; font-family: Inter, sans-serif; font-size: 11px; white-space: nowrap; }}
        .route span {{ color: #2FBF71; padding: 0 4px; font-weight: 600; }}
        .fee {{ margin-top: 4px; color: #E8B75D; font-family: Inter, sans-serif; font-size: 13px; font-weight: 600; }}
        @keyframes soccernomics-scroll {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
    </style>
    <div class="ticker-wrapper"><div class="ticker-track">{tape_html}</div></div>
    """
    components.html(ticker_code, height=72, scrolling=False)


# ============================================================
# METHODOLOGY
# ============================================================

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

with st.expander("Methodology & Data Limitations"):
    st.markdown(
        """
        - **Transfer Spending:** Total fees paid by Premier League clubs for incoming player acquisitions.
        - **Transfer Income:** Total fees received by Premier League clubs from player sales. Consistently termed 'Transfer income' rather than 'Revenue' to distinguish from club operating turnover.
        - **Net Transfer Spend:** Transfer Spending − Transfer Income.
        - **Value Gap & Pricing Classification:** Value Gap = Market Value − Fee. A deal is classified as a *Premium* if fee > 15% above recorded market value, *Discount* if fee < 15% below market value, and *Fair Value* if within ±15%.
        - **Transfer Return:** Calculated strictly as `Total Sale Proceeds / Total Acquisition Fees` for tracked players with both an incoming and outgoing fee at the same club. This is a transfer cash-recovery multiple and must not be interpreted as club profit or accounting ROI, as it does not include player wages, agent fees, bonuses, amortisation, or training compensation.
        - **Data Source:** Historical Premier League transfers sourced from Transfermarkt datasets. Reported fees may omit future performance add-ons or undisclosed clauses.
        """
    )

st.markdown(
    "<div style='height:1rem'></div><div style='text-align:center;color:#5C6E66;font-size:.75rem;'>"
    "Soccernomics · Football. Data. Economics."
    "</div>",
    unsafe_allow_html=True,
)