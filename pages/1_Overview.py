# ============================================================
# SOCCERNOMICS — OVERVIEW
# ============================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
import streamlit as st

import styles
from utils import (
    load_clubs,
    load_transfers,
    get_pl_club_ids,
    get_pl_transfers,
    season_spending_trend,
    top_spending_clubs,
    trading_efficiency_by_club,
    completed_seasons,
    season_biggest_bargain,
    club_badge_style,
    format_eur_m,
)

st.set_page_config(page_title="Soccernomics — Overview", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")
styles.inject()
styles.render_sidebar()

PLOT_BG = "rgba(0,0,0,0)"
GRID_COLOR = "#1E2823"
TEXT_COLOR = "#EAF2ED"
GREEN = "#2FBF71"
AMBER = "#E8B75D"
RED = "#E06B6B"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
clubs = load_clubs()
transfers = load_transfers()
pl_ids = get_pl_club_ids(clubs)
pl_transfers = get_pl_transfers(transfers, pl_ids)

trend = season_spending_trend(pl_transfers, pl_ids)
all_seasons = completed_seasons(pl_transfers)
LATEST_OPEN_SEASON = all_seasons[-1] if all_seasons else None

# Exclude open/partial seasons by default for fair seasonal comparisons
selectable_seasons = [s for s in all_seasons if s != LATEST_OPEN_SEASON] or all_seasons


# ---------------------------------------------------------------------------
# Header + Season Filter
# ---------------------------------------------------------------------------
head_col, filter_col = st.columns([2.5, 1])
with head_col:
    styles.header(
        "Soccernomics",
        "Premier League transfer spending, player values, and the business of the game — by season.",
    )
with filter_col:
    default_idx = len(selectable_seasons) - 1
    selected_season = st.selectbox("Season", selectable_seasons, index=default_idx)

season_idx = selectable_seasons.index(selected_season)
prior_season = selectable_seasons[season_idx - 1] if season_idx > 0 else None

cur_spend = trend.loc[selected_season, "spending"] if selected_season in trend.index else 0
cur_income = trend.loc[selected_season, "revenue"] if selected_season in trend.index else 0
prior_spend = trend.loc[prior_season, "spending"] if prior_season and prior_season in trend.index else None
prior_income = trend.loc[prior_season, "revenue"] if prior_season and prior_season in trend.index else None

net_spend = cur_spend - cur_income
prior_net_spend = (prior_spend - prior_income) if (prior_spend is not None and prior_income is not None) else None
net_spend_delta = (
    ((net_spend - prior_net_spend) / abs(prior_net_spend) * 100)
    if prior_net_spend not in (None, 0) else None
)

spend_delta = ((cur_spend - prior_spend) / prior_spend * 100) if prior_spend else None
income_delta = ((cur_income - prior_income) / prior_income * 100) if prior_income else None

season_incoming = pl_transfers[
    pl_transfers["to_club_id"].isin(pl_ids) & (pl_transfers["transfer_season"] == selected_season)
]
season_outgoing = pl_transfers[
    pl_transfers["from_club_id"].isin(pl_ids) & (pl_transfers["transfer_season"] == selected_season)
]

paid_incoming = season_incoming[season_incoming["transfer_fee"].notna() & (season_incoming["transfer_fee"] > 0)]
active_buyers = paid_incoming["to_club_name"].nunique()
paid_moves_count = len(paid_incoming)

headline_signing = season_incoming.dropna(subset=["transfer_fee"]).nlargest(1, "transfer_fee")
top_spenders = top_spending_clubs(pl_transfers, pl_ids, season=selected_season, top_n=8)
bargain = season_biggest_bargain(pl_transfers, pl_ids, selected_season)
trading = trading_efficiency_by_club(transfers, pl_ids, min_trades=6).head(5)

st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    styles.kpi_card(
        "Window spending",
        format_eur_m(cur_spend),
        f"{spend_delta:+.0f}% vs {prior_season}" if spend_delta is not None else None,
        delta_positive=(spend_delta or 0) >= 0,
    )
with c2:
    styles.kpi_card(
        "Transfer income",
        format_eur_m(cur_income),
        f"{income_delta:+.0f}% vs {prior_season}" if income_delta is not None else None,
        delta_positive=(income_delta or 0) >= 0,
    )
with c3:
    styles.kpi_card(
        "Net transfer spend",
        format_eur_m(net_spend),
        f"{net_spend_delta:+.0f}% vs {prior_season}" if net_spend_delta is not None else None,
        delta_positive=(net_spend_delta or 0) <= 0,
    )
with c4:
    styles.kpi_card(
        "Paid acquisitions",
        f"{paid_moves_count:,}",
        f"across {active_buyers} clubs",
    )
with c5:
    if len(headline_signing):
        r = headline_signing.iloc[0]
        styles.kpi_card("Headline signing", format_eur_m(r["transfer_fee"]), caption=f"{r['player_name']} → {r['to_club_name']}")
    else:
        styles.kpi_card("Headline signing", "—")

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Trend (All Seasons) + This Season's Spenders
# ---------------------------------------------------------------------------
col_a, col_b = st.columns([1.3, 1])

with col_a:
    with styles.panel():
        styles.section_label("Historical Spending & Transfer Income Trend")
        trend_plot = trend.reset_index()
        trend_plot = trend_plot[trend_plot["transfer_season"].isin(all_seasons)]
        colors = [GREEN if s == selected_season else "#3A4B43" for s in trend_plot["transfer_season"]]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_plot["transfer_season"], y=trend_plot["spending"] / 1e9,
            mode="lines+markers", name="Spending",
            line=dict(color=GREEN, width=2.5), marker=dict(size=8, color=colors),
        ))
        fig.add_trace(go.Scatter(
            x=trend_plot["transfer_season"], y=trend_plot["revenue"] / 1e9,
            mode="lines", name="Transfer income", line=dict(color=AMBER, width=2, dash="dot"),
        ))
        fig.update_layout(
            plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG, font_color=TEXT_COLOR,
            margin=dict(l=10, r=10, t=10, b=10), height=300,
            xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR, title="€ Billion"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with col_b:
    with styles.panel():
        styles.section_label(f"Top Spenders · {selected_season}")
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
# Biggest Moves + Trading Efficiency
# ---------------------------------------------------------------------------
col_c, col_d = st.columns([1.3, 1])

with col_c:
    with styles.panel():
        styles.section_label(f"Biggest Signings · {selected_season}")
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
        styles.section_label("Transfer Return (Tracked Buy → Sell)")
        st.caption("Cash recovery per €1 invested across tracked buy-then-sell player pairs (min. 6 trades).")
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
# Season Spotlight + Dynamic Evidence-Based Takeaways
# ---------------------------------------------------------------------------
col_e, col_f = st.columns([1, 1.3])

with col_e:
    with styles.panel():
        styles.section_label(f"Best Value Signing · {selected_season}")
        if bargain:
            st.markdown(f'<div class="sc-spotlight-name">{bargain["name"]}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="sc-spotlight-sub">{bargain["from_club"]} → {bargain["to_club"]} '
                f'· {bargain["transfer_date"].strftime("%b %Y")}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**Fee agreed:** {format_eur_m(bargain['transfer_fee'])}  \n"
                f"**Market value at time:** {format_eur_m(bargain['market_value_in_eur'])}"
            )
            st.markdown(
                f'<div class="sc-spotlight-quote">Signed for {format_eur_m(bargain["value_gap"])} '
                f'below recorded market valuation.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No transfer with both a fee and market value on record for this season.")

with col_f:
    with styles.panel():
        styles.section_label(f"Data Takeaways · {selected_season}")

        # Compute dynamic spending concentration
        top3_sum = top_spenders.head(3).sum() if len(top_spenders) >= 3 else 0
        top3_share = (top3_sum / cur_spend * 100) if cur_spend > 0 else 0
        top3_names = ", ".join(top_spenders.head(3).index.tolist())

        styles.insight_card(
            f"Top 3 spenders drove {top3_share:.0f}% of league spending",
            f"The top three spenders ({top3_names}) committed {format_eur_m(top3_sum)} of the {format_eur_m(cur_spend)} total window outlay.",
            confidence="high", n=len(paid_incoming),
        )

        net_status = "net deficit (spending exceeded sales)" if net_spend > 0 else "net surplus"
        styles.insight_card(
            f"Net transfer balance: {format_eur_m(net_spend)}",
            f"Premier League clubs recorded a {net_status} during {selected_season}, spending {format_eur_m(cur_spend)} against {format_eur_m(cur_income)} in transfer receipts.",
            confidence="high", n=paid_moves_count,
        )

        if bargain:
            styles.insight_card(
                f"Standout value: {bargain['name']}",
                f"{bargain['to_club']} secured {bargain['name']} for {format_eur_m(bargain['transfer_fee'])}, recording a €{bargain['value_gap']/1e6:.1f}M market discount.",
                confidence="moderate", n=1,
            )

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

with st.expander("Methodology & Data Limitations"):
    st.markdown(
        f"""
        - **Scope:** Premier League transfers involving current and historical Premier League clubs ({all_seasons[0]}–{all_seasons[-1]}).
        - **Terminology:** Uses **Transfer income** (not Revenue) to describe money received from player sales, avoiding confusion with total club operating turnover.
        - **Incomplete Seasons:** {LATEST_OPEN_SEASON} is excluded from the season selector by default because windows are live and in progress.
        - **Value Gap:** Compares transfer fees agreed with Transfermarkt's recorded valuation at the time of the transfer.
        - **Transfer Return:** Calculated from repeat buy-then-sell transactions for the same player at the same club. This represents cash recovery from transfer fees, not total club profitability or accounting ROI.
        """
    )