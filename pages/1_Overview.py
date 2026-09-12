import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go

import styles
from utils import (
    load_clubs, load_transfers,
    get_pl_club_ids, get_pl_transfers,
    season_spending_trend, top_spending_clubs,
    trading_efficiency_by_club, completed_seasons, season_biggest_bargain,
    club_badge_style,
)
from styles import format_eur_m

st.set_page_config(page_title="Soccernomics — Overview", page_icon="\u26bd", layout="wide")
styles.inject()

PLOT_BG = "rgba(0,0,0,0)"
GRID_COLOR = "#223029"
TEXT_COLOR = "#D7E4DE"
GREEN = "#2FBF71"
AMBER = "#E8B75D"

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
clubs = load_clubs()
transfers = load_transfers()
pl_ids = get_pl_club_ids(clubs)
pl_transfers = get_pl_transfers(transfers, pl_ids)

trend = season_spending_trend(pl_transfers, pl_ids)
# The latest season in the data is still open (transfer windows in progress) — comparing a
# partial season to a full one would be misleading, so we exclude it from the selector by default.
all_seasons = completed_seasons(pl_transfers)
LATEST_OPEN_SEASON = all_seasons[-1] if all_seasons else None
selectable_seasons = [s for s in all_seasons if s != LATEST_OPEN_SEASON] or all_seasons

# ---------------------------------------------------------------------------
# Header + season filter — the filter drives every panel below it
# ---------------------------------------------------------------------------
head_col, filter_col = st.columns([2.4, 1])
with head_col:
    styles.header(
        "Soccernomics",
        "Premier League transfer spending, player values, and the business of the game \u2014 by season.",
    )
with filter_col:
    default_idx = len(selectable_seasons) - 1
    selected_season = st.selectbox("Season", selectable_seasons, index=default_idx)

season_idx = selectable_seasons.index(selected_season)
prior_season = selectable_seasons[season_idx - 1] if season_idx > 0 else None

cur_spend = trend.loc[selected_season, "spending"] if selected_season in trend.index else 0
cur_revenue = trend.loc[selected_season, "revenue"] if selected_season in trend.index else 0
prior_spend = trend.loc[prior_season, "spending"] if prior_season and prior_season in trend.index else None
prior_revenue = trend.loc[prior_season, "revenue"] if prior_season and prior_season in trend.index else None
net_spend = cur_spend - cur_revenue
prior_net_spend = (prior_spend - prior_revenue) if (prior_spend is not None and prior_revenue is not None) else None
net_spend_delta = (
    ((net_spend - prior_net_spend) / abs(prior_net_spend) * 100)
    if prior_net_spend not in (None, 0) else None
)

spend_delta = ((cur_spend - prior_spend) / prior_spend * 100) if prior_spend else None
revenue_delta = ((cur_revenue - prior_revenue) / prior_revenue * 100) if prior_revenue else None

season_incoming = pl_transfers[
    pl_transfers["to_club_id"].isin(pl_ids) & (pl_transfers["transfer_season"] == selected_season)
]
headline_signing = season_incoming.dropna(subset=["transfer_fee"]).nlargest(1, "transfer_fee")
top_spenders = top_spending_clubs(pl_transfers, pl_ids, season=selected_season, top_n=8)
bargain = season_biggest_bargain(pl_transfers, pl_ids, selected_season)
trading = trading_efficiency_by_club(transfers, pl_ids, min_trades=6).head(5)

st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# KPI row — framed as season headlines, not neutral stats
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
with c1:
    styles.kpi_card(
        "Window spending",
        format_eur_m(cur_spend),
        f"{spend_delta:+.0f}% vs {prior_season}" if spend_delta is not None else None,
        delta_positive=(spend_delta or 0) >= 0,
    )
with c2:
    styles.kpi_card(
        "Sales revenue",
        format_eur_m(cur_revenue),
        f"{revenue_delta:+.0f}% vs {prior_season}" if revenue_delta is not None else None,
        delta_positive=(revenue_delta or 0) >= 0,
    )
with c3:
    styles.kpi_card(
        "Net spend",
        format_eur_m(net_spend),
        f"{net_spend_delta:+.0f}% vs {prior_season}" if net_spend_delta is not None else None,
        delta_positive=(net_spend_delta or 0) >= 0,
    )
with c4:
    if len(headline_signing):
        r = headline_signing.iloc[0]
        styles.kpi_card("Headline signing", format_eur_m(r["transfer_fee"]), caption=f"{r['player_name']} \u2192 {r['to_club_name']}")
    else:
        styles.kpi_card("Headline signing", "\u2014")

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Trend (all seasons, selected one highlighted) + this season's spenders
# ---------------------------------------------------------------------------
col_a, col_b = st.columns([1.3, 1])

with col_a:
    with styles.panel():
        styles.section_label("Spending across the years")
        trend_plot = trend.reset_index()
        trend_plot = trend_plot[trend_plot["transfer_season"].isin(all_seasons)]
        colors = [GREEN if s == selected_season else "#3A4B43" for s in trend_plot["transfer_season"]]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_plot["transfer_season"], y=trend_plot["spending"] / 1e9,
            mode="lines+markers", name="Spending",
            line=dict(color=GREEN, width=2), marker=dict(size=8, color=colors),
        ))
        fig.add_trace(go.Scatter(
            x=trend_plot["transfer_season"], y=trend_plot["revenue"] / 1e9,
            mode="lines", name="Revenue", line=dict(color=AMBER, width=2, dash="dot"),
        ))
        fig.update_layout(
            plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG, font_color=TEXT_COLOR,
            margin=dict(l=10, r=10, t=10, b=10), height=300,
            xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR, title="\u20ac Billion"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with col_b:
    with styles.panel():
        styles.section_label(f"Who spent big in {selected_season}")
        if len(top_spenders):
            for club, fee in top_spenders.items():
                initials, color = club_badge_style(club)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.4rem 0;'
                    f'border-bottom:1px solid #223029;">{styles.club_badge(initials, color, 28)}'
                    f'<span style="flex:1;color:#D7E4DE;font-size:0.9rem;">{club}</span>'
                    f'<span style="color:#EAF2ED;font-weight:600;font-size:0.9rem;">{format_eur_m(fee)}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No incoming transfers recorded for this season.")

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Season's biggest transfers + trading efficiency leaderboard
# ---------------------------------------------------------------------------
col_c, col_d = st.columns([1.3, 1])

with col_c:
    with styles.panel():
        styles.section_label(f"Biggest moves of {selected_season}")
        top5 = season_incoming.dropna(subset=["transfer_fee"]).nlargest(5, "transfer_fee")
        if len(top5):
            disp = top5[["player_name", "from_club_name", "to_club_name", "transfer_fee"]].copy()
            disp["transfer_fee"] = disp["transfer_fee"].apply(format_eur_m)
            disp = disp.rename(columns={
                "player_name": "Player", "from_club_name": "From", "to_club_name": "To", "transfer_fee": "Fee",
            })
            st.dataframe(disp, hide_index=True, width="stretch")
        else:
            st.caption("No transfers with a recorded fee this season.")

with col_d:
    with styles.panel():
        styles.section_label("Best traders (buy-low, sell-high)")
        st.caption("Return per \u20ac1 invested, all-time \u2014 tracked buy\u2192sell pairs, min. 6 trades")
        for club, row in trading.iterrows():
            roi = row["profit_per_euro_invested"]
            initials, color = club_badge_style(club)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.4rem 0;'
                f'border-bottom:1px solid #223029;">{styles.club_badge(initials, color, 28)}'
                f'<span style="flex:1;color:#D7E4DE;font-size:0.9rem;">{club}</span>'
                f'<span style="color:{GREEN};font-weight:700;font-size:0.9rem;">{roi:.2f}x</span>'
                f'<span style="color:#5C6E66;font-size:0.78rem;">n={int(row["n_trades"])}</span></div>',
                unsafe_allow_html=True,
            )

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Season spotlight (dynamic bargain) + key takeaways
# ---------------------------------------------------------------------------
col_e, col_f = st.columns([1, 1.3])

with col_e:
    with styles.panel():
        styles.section_label(f"Best value signing \u2014 {selected_season}")
        if bargain:
            st.markdown(f'<div class="sc-spotlight-name">{bargain["name"]}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="sc-spotlight-sub">{bargain["from_club"]} \u2192 {bargain["to_club"]} '
                f'\u00b7 {bargain["transfer_date"].strftime("%b %Y")}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**Fee:** {format_eur_m(bargain['transfer_fee'])}  \n"
                f"**Market value at the time:** {format_eur_m(bargain['market_value_in_eur'])}"
            )
            st.markdown(
                f'<div class="sc-spotlight-quote">Signed for {format_eur_m(bargain["value_gap"])} '
                f'under market value \u2014 the standout piece of business this window.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No transfer with both a fee and a market value on record for this season.")

with col_f:
    with styles.panel():
        styles.section_label("What the data says")
        styles.insight_card(
            "Player value peaks at 26 across every position",
            "Attackers lose value fastest after their peak; goalkeepers hold theirs the longest.",
            confidence="high", n=32544,
        )
        styles.insight_card(
            "Chelsea's overpay rate rose after their 2022 ownership change",
            "Median overpay vs. market value went from 28% to 39%, concentrated in deals for very young players.",
            confidence="moderate", n=93,
        )
        styles.insight_card(
            "Brentford, not Brighton, is the Premier League's sharpest trader",
            "By return on transfer fees, Brentford's buy-sell record beats Brighton's despite Brighton's stronger reputation.",
            confidence="low", n=12,
        )

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

with st.expander("Methodology & data limitations"):
    st.markdown(
        f"""
        - **Scope:** Premier League only (V1). Transfer activity involving any club that has played
          in the Premier League, {all_seasons[0]}\u2013{all_seasons[-1]}.
        - **{LATEST_OPEN_SEASON} is excluded from the season selector** by default because that
          transfer window is still open \u2014 comparing it to completed seasons would understate it.
        - **No club financial data** (revenue, wages, debt, profit) is used or estimated anywhere.
          Every figure here is a transfer fee, a market valuation, or an aggregate of the two.
        - **"Best value signing"** compares fee paid to Transfermarkt's market valuation at the time
          of transfer \u2014 a market estimate, not an independent judgement of the deal.
        - **Trading efficiency** is calculated from tracked buy\u2192sell pairs for the same player at
          the same club; clubs with very few tracked trades (see the n= counts) carry a wider margin
          of error than the totals suggest, hence the confidence labels above.
        """
    )