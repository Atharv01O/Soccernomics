import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import styles
from utils import (
    RAW_DIR,
    load_clubs,
    load_players,
    load_transfers,
    load_player_valuations,
    load_player_wages,
    get_player_valuation_history,
    get_player_transfer_history,
    player_career_financial_summary,
    get_player_wage_history,
    player_wage_summary,
    format_eur_m,
)

# ============================================================
# SOCCERNOMICS — PLAYER MARKET PAGE
# Design reference: supplied dark football-analytics mockup.
# ============================================================

st.set_page_config(
    page_title="Soccernomics — Player",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)
styles.inject()

# ------------------------------------------------------------
# Design tokens
# ------------------------------------------------------------
BG = "#0B0F14"
BG_2 = "#0D1318"
CARD = "#101A15"
CARD_2 = "#121E18"
BORDER = "#263A31"
BORDER_SOFT = "#1B2A23"
TEXT = "#F4F8FC"
MUTED = "#8EA2B5"
MUTED_2 = "#647B90"
GREEN = "#28D17C"
GREEN_2 = "#20B86D"
CYAN = "#6EAFA2"
BLUE = "#69A6D8"
PURPLE = "#8B72E6"
PINK = "#C97AAE"
YELLOW = "#E3B84C"
RED = "#D86C76"
WHITE = "#EAF1F7"
GRID = "#26382F"

st.markdown(
    """
    <style>
    /* ---------- Global ---------- */
    .stApp {
        background:
            radial-gradient(circle at 80% 0%, rgba(35,199,245,.055), transparent 27%),
            radial-gradient(circle at 8% 20%, rgba(33,230,162,.035), transparent 25%),
            #07101A;
        color: #F4F8FC;
    }

    .block-container {
        max-width: 1280px !important;
        padding: 20px 28px 30px !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 14px !important;
        align-items: stretch !important;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 8px;
    }

    div[data-testid="column"] > div[data-testid="stVerticalBlock"] {
        height: 100%;
    }

    div[data-testid="stPlotlyChart"] {
        margin: 0 !important;
        padding: 0 !important;
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: #71879A !important;
    }

    /* ---------- Top navigation ---------- */
    .sx-nav {
        display: none;
        height: 54px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #15283A;
        margin-bottom: 12px;
    }

    .sx-brand {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .sx-logo {
        width: 31px;
        height: 31px;
        border-radius: 50%;
        background: radial-gradient(circle at 50% 50%, #07101A 0 27%, #21E6A2 29% 42%, #0C6E53 44% 100%);
        border: 1px solid #1E6D5A;
        box-shadow: 0 0 18px rgba(33,230,162,.18);
    }

    .sx-brand-name {
        font-weight: 850;
        font-size: 1rem;
        line-height: 1;
    }

    .sx-brand-sub {
        color: #71879A;
        font-size: .63rem;
        margin-top: 3px;
    }

    .sx-navlinks {
        display: flex;
        gap: 26px;
        color: #A8B8C7;
        font-size: .73rem;
        align-items: center;
    }

    .sx-nav-active {
        color: #22E5A0;
        padding: 7px 12px;
        border: 1px solid #167E66;
        background: rgba(33,230,162,.055);
        border-radius: 8px;
    }

    /* ---------- Hero ---------- */
    .sx-crumb {
        color: #71879A;
        font-size: .67rem;
        margin: 4px 0 9px;
    }

    .sx-hero {
        min-height: 190px;
        border: 1px solid #1D3A50;
        border-radius: 12px;
        overflow: hidden;
        position: relative;
        background:
            radial-gradient(circle at 18% 55%, rgba(32,199,245,.08), transparent 30%),
            linear-gradient(110deg, #091726 0%, #0A1725 54%, #081522 100%);
    }

    .sx-hero-glow {
        position: absolute;
        right: 35%;
        top: 0;
        width: 260px;
        height: 100%;
        background: radial-gradient(circle, rgba(30,116,165,.10), transparent 67%);
        pointer-events: none;
    }

    .sx-player-image {
        width: 225px;
        height: 190px;
        object-fit: cover;
        object-position: center top;
        position: absolute;
        left: 8px;
        bottom: 0;
        filter: saturate(.95);
    }

    .sx-hero-content {
        margin-left: 235px;
        padding: 23px 18px 18px 0;
        position: relative;
        z-index: 2;
    }

    .sx-player-name {
        font-size: 2.15rem;
        line-height: .92;
        font-weight: 900;
        letter-spacing: -.055em;
        max-width: 420px;
    }

    .sx-player-name span {
        display: block;
    }

    .sx-player-line {
        display: flex;
        gap: 10px;
        align-items: center;
        margin-top: 12px;
        color: #B5C5D3;
        font-size: .8rem;
    }

    .sx-pill {
        padding: 3px 7px;
        border-radius: 5px;
        background: #172A3D;
        color: #C7D5E0;
        border: 1px solid #263F55;
        font-size: .65rem;
    }

    .sx-hero-stats {
        display: flex;
        gap: 0;
        margin-top: 24px;
    }

    .sx-hero-stat {
        min-width: 84px;
        padding-right: 20px;
        margin-right: 20px;
        border-right: 1px solid #23394C;
    }

    .sx-hero-stat:last-child {
        border-right: 0;
    }

    .sx-hero-value {
        color: #F4F8FC;
        font-weight: 800;
        font-size: .92rem;
    }

    .sx-hero-label {
        color: #6F8498;
        font-size: .61rem;
        margin-top: 4px;
    }

    .sx-quote {
        margin-top: 13px;
        color: #71879A;
        font-size: .68rem;
        font-style: italic;
    }

    /* ---------- Value panel ---------- */
    .sx-value-panel {
        min-height: 190px;
        border: 1px solid #1D3A50;
        border-radius: 12px;
        background: linear-gradient(145deg, #0A1723, #08131E);
        padding: 22px 22px;
    }

    .sx-value-title {
        color: #75DDBA;
        font-size: .69rem;
        font-weight: 800;
    }

    .sx-value-main {
        color: #20E5A0;
        font-size: 2.15rem;
        line-height: 1;
        font-weight: 900;
        margin: 9px 0 7px;
        letter-spacing: -.045em;
    }

    .sx-value-change {
        display: inline-block;
        padding: 4px 7px;
        border-radius: 5px;
        color: #20E5A0;
        background: rgba(33,230,162,.08);
        font-size: .63rem;
        font-weight: 800;
    }

    .sx-value-row {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        padding: 9px 0;
        border-bottom: 1px solid #172B3C;
        font-size: .7rem;
    }

    .sx-value-row:last-child {
        border-bottom: 0;
    }

    .sx-value-row span:first-child {
        color: #8297A9;
    }

    .sx-value-row span:last-child {
        color: #D9E4EC;
        font-weight: 700;
        text-align: right;
    }

    /* ---------- KPI cards ---------- */
    .sx-kpi {
        min-height: 70px;
        border: 1px solid #1D3850;
        border-radius: 9px;
        background: linear-gradient(135deg, #0B1927, #0A1622);
        padding: 11px 12px 9px;
        position: relative;
        overflow: hidden;
    }

    .sx-kpi::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background: var(--accent);
    }

    .sx-kpi-label {
        color: #7D92A5;
        font-size: .59rem;
        font-weight: 750;
    }

    .sx-kpi-value {
        color: #EDF5FA;
        font-size: 1.16rem;
        font-weight: 900;
        margin-top: 6px;
    }

    .sx-kpi-note {
        color: #637B8F;
        font-size: .58rem;
        margin-top: 3px;
    }

    /* ---------- Cards ---------- */
    .sx-card {
        border: 1px solid #1B3449;
        border-radius: 10px;
        background: linear-gradient(145deg, #091522, #08131E);
        padding: 14px 15px 12px;
        height: 100%;
    }

    .sx-card-title {
        color: #F0F5F8;
        font-size: .86rem;
        font-weight: 850;
    }

    .sx-card-note {
        color: #70869A;
        font-size: .63rem;
        margin-top: 3px;
        line-height: 1.4;
    }

    .sx-section-space {
        height: 6px;
    }

    .sx-footnote {
        text-align: center;
        color: #637A6E;
        font-size: .58rem;
        padding-top: 2px;
    }

    /* ---------- Profile list ---------- */
    .sx-profile-row {
        display: flex;
        justify-content: space-between;
        gap: 14px;
        padding: 7px 0;
        border-bottom: 1px solid #14283A;
        font-size: .68rem;
    }

    .sx-profile-row:last-child {
        border-bottom: 0;
    }

    .sx-profile-label {
        color: #73899C;
    }

    .sx-profile-value {
        color: #E3ECF2;
        font-weight: 750;
        text-align: right;
    }

    /* ---------- Timeline ---------- */
    .sx-timeline {
        margin-top: 7px;
    }

    .sx-timeline-row {
        display: grid;
        grid-template-columns: 75px 1fr 70px;
        gap: 8px;
        align-items: center;
        min-height: 38px;
        border-bottom: 1px solid #14283A;
        font-size: .66rem;
    }

    .sx-timeline-row:last-child {
        border-bottom: 0;
    }

    .sx-timeline-date {
        color: #73899C;
    }

    .sx-timeline-club {
        color: #E3ECF2;
        font-weight: 700;
    }

    .sx-timeline-fee {
        text-align: right;
        color: #9DB0C0;
    }

    /* ---------- Similar players ---------- */
    .sx-similar-row {
        display: grid;
        grid-template-columns: 30px 1fr 1.2fr 54px;
        gap: 7px;
        align-items: center;
        min-height: 34px;
        border-bottom: 1px solid #14283A;
        font-size: .63rem;
    }

    .sx-similar-row:last-child {
        border-bottom: 0;
    }

    .sx-sim-avatar {
        width: 25px;
        height: 25px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid #29445A;
    }

    .sx-bar {
        height: 7px;
        border-radius: 5px;
        background: #14273A;
        overflow: hidden;
    }

    .sx-bar > div {
        height: 100%;
        border-radius: 5px;
        background: linear-gradient(90deg, #16C987, #20E5A0);
    }

    .sx-sim-value {
        color: #D9E5ED;
        text-align: right;
        font-weight: 750;
    }

    /* ---------- Transfer table ---------- */
    .sx-table-wrap {
        border: 1px solid #1A344A;
        border-radius: 8px;
        overflow: hidden;
        margin-top: 8px;
    }

    .sx-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .65rem;
    }

    .sx-table th {
        text-align: left;
        color: #8EA3B5;
        background: #0E1C2B;
        padding: 8px 10px;
        border-right: 1px solid #1B3448;
        font-weight: 750;
    }

    .sx-table td {
        color: #DDE7EE;
        padding: 8px 10px;
        border-top: 1px solid #152A3C;
        border-right: 1px solid #152A3C;
    }

    .sx-table tr:last-child td {
        border-bottom: 0;
    }

    .sx-export {
        float: right;
        border: 1px solid #394F76;
        background: #202B55;
        color: #E7ECFA;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: .61rem;
        font-weight: 750;
    }

    /* ---------- Footer ---------- */
    .sx-footer {
        border-top: 1px solid #162B3E;
        margin-top: 17px;
        padding: 14px 4px 0;
        display: flex;
        justify-content: space-between;
        color: #647B90;
        font-size: .62rem;
    }

    /* ---------- Streamlit control cleanup ---------- */
    div[data-baseweb="select"] > div {
        background: #111A28 !important;
        border: 1px solid #263D55 !important;
        border-radius: 8px !important;
        min-height: 36px !important;
    }

    .stSelectbox label {
        color: #71879A !important;
        font-size: .61rem !important;
        font-weight: 750 !important;
    }

    button[kind="secondary"] {
        border-color: #29445B !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA HELPERS
# ============================================================
def norm(value):
    if pd.isna(value):
        return ""
    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return re.sub(r"\s+", " ", value)


def safe(value, fallback="—"):
    if pd.isna(value) or str(value).strip() in {"", "nan", "None"}:
        return fallback
    return str(value)


def money_gbp(value):
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"£{value/1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"£{value/1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"£{value/1_000:.1f}K"
    return f"£{value:,.0f}"


def map_position(row):
    text = f"{norm(row.get('sub_position'))} {norm(row.get('position'))}"
    rules = [
        (("goalkeeper",), "GK"),
        (("centre forward", "center forward", "striker"), "CF"),
        (("left winger", "left wing"), "LW"),
        (("right winger", "right wing"), "RW"),
        (("attacking midfield", "second striker"), "CAM"),
        (("defensive midfield",), "CDM"),
        (("central midfield", "midfield"), "CM"),
        (("left back",), "LB"),
        (("right back",), "RB"),
        (("centre back", "center back", "defender"), "CB"),
    ]
    for words, result in rules:
        if any(word in text for word in words):
            return result
    direct = safe(row.get("position"), "").upper()
    return direct if direct in {"GK","CB","LB","RB","CDM","CM","CAM","LW","RW","CF"} else "CF"


def role_name(position):
    names = {
        "GK": "Goalkeeper",
        "CB": "Centre-Back",
        "LB": "Left-Back",
        "RB": "Right-Back",
        "CDM": "Defensive Midfielder",
        "CM": "Central Midfielder",
        "CAM": "Attacking Midfielder",
        "LW": "Left Winger",
        "RW": "Right Winger",
        "CF": "Centre-Forward",
    }
    return names.get(position, position)


def load_heatmaps():
    path = os.path.join(RAW_DIR, "position_heatmaps_dataset.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        required = {"position", "style", "x_m", "y_m", "weight"}
        if not required.issubset(df.columns):
            return pd.DataFrame()
        for c in ["x_m", "y_m", "weight"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.dropna(subset=["position", "style", "x_m", "y_m", "weight"])
    except Exception:
        return pd.DataFrame()


def find_name_column(df):
    for c in ["name", "Name", "player_name", "Player", "player"]:
        if c in df.columns:
            return c
    return None


# ============================================================
# CHART BUILDERS
# ============================================================
def pitch_shapes():
    line = "#91A79C"
    return [
        dict(type="rect", x0=0, y0=0, x1=105, y1=68, line=dict(color=line, width=1.4)),
        dict(type="line", x0=52.5, y0=0, x1=52.5, y1=68, line=dict(color=line, width=1)),
        dict(type="circle", x0=43.35, y0=24.85, x1=61.65, y1=43.15, line=dict(color=line, width=1)),
        dict(type="rect", x0=0, y0=13.84, x1=16.5, y1=54.16, line=dict(color=line, width=1)),
        dict(type="rect", x0=88.5, y0=13.84, x1=105, y1=54.16, line=dict(color=line, width=1)),
        dict(type="rect", x0=0, y0=24.84, x1=5.5, y1=43.16, line=dict(color=line, width=1)),
        dict(type="rect", x0=99.5, y0=24.84, x1=105, y1=43.16, line=dict(color=line, width=1)),
    ]


def heatmap_chart(df):
    fig = go.Figure()
    fig.add_trace(
        go.Histogram2d(
            x=df["x_m"],
            y=df["y_m"],
            z=df["weight"],
            histfunc="sum",
            nbinsx=32,
            nbinsy=21,
            colorscale=[
                [0, "rgba(8,20,15,.02)"],
                [.18, "#0D4A30"],
                [.38, "#12834F"],
                [.58, "#19BA73"],
                [.76, "#A9D94E"],
                [.9, "#FFD34E"],
                [1, "#FF5D52"],
            ],
            showscale=False,
            hovertemplate="Role activity: %{z:.1f}<extra></extra>",
        )
    )
    for shape in pitch_shapes():
        fig.add_shape(**shape)

    fig.update_layout(
        height=300,
        margin=dict(l=3, r=3, t=3, b=3),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#08160F",
        xaxis=dict(visible=False, range=[-1,106], fixedrange=True),
        yaxis=dict(visible=False, range=[-1,69], scaleanchor="x", scaleratio=1, fixedrange=True),
        showlegend=False,
    )
    return fig


def line_chart(df, x, y, color, y_title, height=255):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            line=dict(color=color, width=2.7),
            marker=dict(color=color, size=5.5),
            fill="tozeroy",
            fillcolor="rgba(33,230,162,.045)" if color == GREEN else "rgba(36,199,245,.045)",
            hovertemplate="%{x}<br>%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=5, r=5, t=8, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=9),
        xaxis=dict(gridcolor=GRID, zeroline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False, title=y_title),
        showlegend=False,
    )
    return fig


def market_profile_radar(player_row, players, transfers, wages, valuations, position):
    """
    A real-data financial radar replacing the unavailable playerstats name
    mapping. Every axis is computed from the project's datasets.
    """
    current = pd.to_numeric(player_row.get("market_value_in_eur"), errors="coerce")
    peak = pd.to_numeric(player_row.get("highest_market_value_in_eur"), errors="coerce")

    p = players.copy()
    p["mv"] = pd.to_numeric(p["market_value_in_eur"], errors="coerce")
    p = p.dropna(subset=["mv"])

    same_pos = p[p["position"].astype(str).str.contains(str(player_row.get("position")), case=False, na=False)]
    if len(same_pos) < 20:
        same_pos = p

    def pct(series, value):
        series = pd.to_numeric(series, errors="coerce").dropna()
        if series.empty or pd.isna(value):
            return 50
        return float((series <= value).mean() * 100)

    axes = [
        ("Market Value", pct(same_pos["mv"], current)),
        ("Peak Value", pct(same_pos["mv"], peak)),
    ]

    # Career transfer volume.
    transfer_history = get_player_transfer_history(transfers, player_row["player_id"])
    fees = pd.to_numeric(transfer_history.get("transfer_fee"), errors="coerce") if not transfer_history.empty else pd.Series(dtype=float)
    fee_total = fees[fees > 0].sum() if not fees.empty else 0

    all_fee_totals = transfers.copy()
    all_fee_totals["fee"] = pd.to_numeric(all_fee_totals["transfer_fee"], errors="coerce")
    fee_by_player = all_fee_totals[all_fee_totals["fee"] > 0].groupby("player_id")["fee"].sum()

    axes.append(("Transfer Volume", pct(fee_by_player, fee_total)))

    # Latest wage.
    wage_rows = get_player_wage_history(wages, safe(player_row.get("name")))
    latest_wage = (
        pd.to_numeric(wage_rows.iloc[-1].get("annual_wage_gbp"), errors="coerce")
        if wage_rows is not None and not wage_rows.empty
        else np.nan
    )

    all_wages = []
    # Avoid inventing wage values: use the loaded wage file if it has an annual column.
    if wages is not None and not wages.empty and "annual_wage_gbp" in wages.columns:
        all_wages = pd.to_numeric(wages["annual_wage_gbp"], errors="coerce").dropna()

    axes.append(("Annual Wage", pct(all_wages, latest_wage) if len(all_wages) else 50))

    # Age percentile is descriptive, not performance.
    dob = pd.to_datetime(player_row.get("date_of_birth"), errors="coerce")
    age = (pd.Timestamp.now() - dob).days / 365.25 if pd.notna(dob) else np.nan
    # For age, invert so a younger age is visually "higher" as market profile,
    # while clearly labelling the axis as Age Advantage.
    age_series = (pd.Timestamp.now() - pd.to_datetime(p["date_of_birth"], errors="coerce")).dt.days / 365.25
    age_series = age_series.dropna()
    age_pct = 100 - pct(age_series, age) if len(age_series) else 50
    axes.append(("Age Advantage", age_pct))

    labels = [a[0] for a in axes]
    values = [max(5, min(100, a[1])) for a in axes]
    labels += [labels[0]]
    values += [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(33,230,162,.13)",
            line=dict(color=GREEN, width=2.4),
            marker=dict(color=GREEN, size=6),
            hovertemplate="%{theta}: %{r:.0f}th percentile<extra></extra>",
            name="Player",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=25, r=25, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=8),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0,100],
                tickvals=[25,50,75,100],
                tickfont=dict(color=MUTED_2, size=7),
                gridcolor=GRID,
                linecolor=GRID,
            ),
            angularaxis=dict(gridcolor=GRID, linecolor=GRID),
        ),
        showlegend=False,
    )
    return fig


def transfer_creation(transfers_df, valuation_df):
    t = transfers_df.copy()
    v = valuation_df.copy()

    if t.empty or v.empty:
        return pd.DataFrame()

    t["date"] = pd.to_datetime(t["transfer_date"], errors="coerce")
    t["fee"] = pd.to_numeric(t["transfer_fee"], errors="coerce")
    t = t.dropna(subset=["date"])
    t = t[t["fee"].notna() & (t["fee"] > 0)].sort_values("date")

    v["date"] = pd.to_datetime(v["date"], errors="coerce")
    v["value"] = pd.to_numeric(v["market_value_in_eur"], errors="coerce")
    v = v.dropna(subset=["date", "value"]).sort_values("date")

    rows = []
    for _, move in t.iterrows():
        later = t[t["date"] > move["date"]]["date"]
        end = later.min() if not later.empty else pd.Timestamp.max
        window = v[(v["date"] >= move["date"]) & (v["date"] < end)]
        if window.empty:
            continue
        peak = window["value"].max()
        rows.append({
            "date": move["date"],
            "move": f'{safe(move.get("from_club_name"))} → {safe(move.get("to_club_name"))}',
            "fee": move["fee"],
            "peak": peak,
            "change": (peak - move["fee"]) / move["fee"] * 100,
        })
    return pd.DataFrame(rows)


def transfer_creation_chart(df):
    if df.empty:
        return None
    labels = [d.strftime("%Y") for d in df["date"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=df["fee"]/1_000_000,
        name="Transfer Fee",
        marker_color="#2384C6",
        hovertemplate="%{x}<br>Fee: €%{y:.1f}M<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=labels,
        y=df["peak"]/1_000_000,
        name="Peak Value After Move",
        marker_color=GREEN,
        hovertemplate="%{x}<br>Peak value: €%{y:.1f}M<extra></extra>",
    ))
    fig.update_layout(
        height=300,
        barmode="group",
        margin=dict(l=5,r=5,t=15,b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT,size=8),
        xaxis=dict(gridcolor=GRID, title=""),
        yaxis=dict(gridcolor=GRID, title="€M"),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=8)),
        hovermode="x unified",
    )
    return fig


# ============================================================
# LOAD
# ============================================================
clubs = load_clubs()
players = load_players()
transfers = load_transfers()
valuations = load_player_valuations()
wages = load_player_wages()
heatmaps = load_heatmaps()

searchable = (
    players.dropna(subset=["name"])
    .drop_duplicates("player_id")
    .sort_values("name")
    .reset_index(drop=True)
)

if searchable.empty:
    st.error("players.csv contains no searchable player records.")
    st.stop()

names = searchable["name"].astype(str).tolist()
default = names.index("Erling Haaland") if "Erling Haaland" in names else 0

# ============================================================
# DATA HELPERS
# ============================================================
def norm(value):
    if pd.isna(value):
        return ""
    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return re.sub(r"\s+", " ", value)


def safe(value, fallback="—"):
    if pd.isna(value) or str(value).strip() in {"", "nan", "None"}:
        return fallback
    return str(value)


def money_gbp(value):
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"£{value/1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"£{value/1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"£{value/1_000:.1f}K"
    return f"£{value:,.0f}"


def map_position(row):
    text = f"{norm(row.get('sub_position'))} {norm(row.get('position'))}"
    rules = [
        (("goalkeeper",), "GK"),
        (("centre forward", "center forward", "striker"), "CF"),
        (("left winger", "left wing"), "LW"),
        (("right winger", "right wing"), "RW"),
        (("attacking midfield", "second striker"), "CAM"),
        (("defensive midfield",), "CDM"),
        (("central midfield", "midfield"), "CM"),
        (("left back",), "LB"),
        (("right back",), "RB"),
        (("centre back", "center back", "defender"), "CB"),
    ]
    for words, result in rules:
        if any(word in text for word in words):
            return result
    direct = safe(row.get("position"), "").upper()
    return direct if direct in {"GK","CB","LB","RB","CDM","CM","CAM","LW","RW","CF"} else "CF"


def role_name(position):
    names = {
        "GK": "Goalkeeper",
        "CB": "Centre-Back",
        "LB": "Left-Back",
        "RB": "Right-Back",
        "CDM": "Defensive Midfielder",
        "CM": "Central Midfielder",
        "CAM": "Attacking Midfielder",
        "LW": "Left Winger",
        "RW": "Right Winger",
        "CF": "Centre-Forward",
    }
    return names.get(position, position)


def load_heatmaps():
    path = os.path.join(RAW_DIR, "position_heatmaps_dataset.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        required = {"position", "style", "x_m", "y_m", "weight"}
        if not required.issubset(df.columns):
            return pd.DataFrame()
        for c in ["x_m", "y_m", "weight"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.dropna(subset=["position", "style", "x_m", "y_m", "weight"])
    except Exception:
        return pd.DataFrame()


def find_name_column(df):
    for c in ["name", "Name", "player_name", "Player", "player"]:
        if c in df.columns:
            return c
    return None


# ============================================================
# CHART BUILDERS
# ============================================================
def pitch_shapes():
    line = "#91A79C"
    return [
        dict(type="rect", x0=0, y0=0, x1=105, y1=68, line=dict(color=line, width=1.4)),
        dict(type="line", x0=52.5, y0=0, x1=52.5, y1=68, line=dict(color=line, width=1)),
        dict(type="circle", x0=43.35, y0=24.85, x1=61.65, y1=43.15, line=dict(color=line, width=1)),
        dict(type="rect", x0=0, y0=13.84, x1=16.5, y1=54.16, line=dict(color=line, width=1)),
        dict(type="rect", x0=88.5, y0=13.84, x1=105, y1=54.16, line=dict(color=line, width=1)),
        dict(type="rect", x0=0, y0=24.84, x1=5.5, y1=43.16, line=dict(color=line, width=1)),
        dict(type="rect", x0=99.5, y0=24.84, x1=105, y1=43.16, line=dict(color=line, width=1)),
    ]


def heatmap_chart(df):
    fig = go.Figure()
    fig.add_trace(
        go.Histogram2d(
            x=df["x_m"],
            y=df["y_m"],
            z=df["weight"],
            histfunc="sum",
            nbinsx=32,
            nbinsy=21,
            colorscale=[
                [0, "rgba(8,20,15,.02)"],
                [.18, "#0D4A30"],
                [.38, "#12834F"],
                [.58, "#19BA73"],
                [.76, "#A9D94E"],
                [.9, "#FFD34E"],
                [1, "#FF5D52"],
            ],
            showscale=False,
            hovertemplate="Role activity: %{z:.1f}<extra></extra>",
        )
    )
    for shape in pitch_shapes():
        fig.add_shape(**shape)

    fig.update_layout(
        height=300,
        margin=dict(l=3, r=3, t=3, b=3),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#08160F",
        xaxis=dict(visible=False, range=[-1,106], fixedrange=True),
        yaxis=dict(visible=False, range=[-1,69], scaleanchor="x", scaleratio=1, fixedrange=True),
        showlegend=False,
    )
    return fig


def line_chart(df, x, y, color, y_title, height=255):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            line=dict(color=color, width=2.7),
            marker=dict(color=color, size=5.5),
            fill="tozeroy",
            fillcolor="rgba(33,230,162,.045)" if color == GREEN else "rgba(36,199,245,.045)",
            hovertemplate="%{x}<br>%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=5, r=5, t=8, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=9),
        xaxis=dict(gridcolor=GRID, zeroline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False, title=y_title),
        showlegend=False,
    )
    return fig


def market_profile_radar(player_row, players, transfers, wages, valuations, position):
    """
    A real-data financial radar replacing the unavailable playerstats name
    mapping. Every axis is computed from the project's datasets.
    """
    current = pd.to_numeric(player_row.get("market_value_in_eur"), errors="coerce")
    peak = pd.to_numeric(player_row.get("highest_market_value_in_eur"), errors="coerce")

    p = players.copy()
    p["mv"] = pd.to_numeric(p["market_value_in_eur"], errors="coerce")
    p = p.dropna(subset=["mv"])

    same_pos = p[p["position"].astype(str).str.contains(str(player_row.get("position")), case=False, na=False)]
    if len(same_pos) < 20:
        same_pos = p

    def pct(series, value):
        series = pd.to_numeric(series, errors="coerce").dropna()
        if series.empty or pd.isna(value):
            return 50
        return float((series <= value).mean() * 100)

    axes = [
        ("Market Value", pct(same_pos["mv"], current)),
        ("Peak Value", pct(same_pos["mv"], peak)),
    ]

    # Career transfer volume.
    transfer_history = get_player_transfer_history(transfers, player_row["player_id"])
    fees = pd.to_numeric(transfer_history.get("transfer_fee"), errors="coerce") if not transfer_history.empty else pd.Series(dtype=float)
    fee_total = fees[fees > 0].sum() if not fees.empty else 0

    all_fee_totals = transfers.copy()
    all_fee_totals["fee"] = pd.to_numeric(all_fee_totals["transfer_fee"], errors="coerce")
    fee_by_player = all_fee_totals[all_fee_totals["fee"] > 0].groupby("player_id")["fee"].sum()

    axes.append(("Transfer Volume", pct(fee_by_player, fee_total)))

    # Latest wage.
    wage_rows = get_player_wage_history(wages, safe(player_row.get("name")))
    latest_wage = (
        pd.to_numeric(wage_rows.iloc[-1].get("annual_wage_gbp"), errors="coerce")
        if wage_rows is not None and not wage_rows.empty
        else np.nan
    )

    all_wages = []
    # Avoid inventing wage values: use the loaded wage file if it has an annual column.
    if wages is not None and not wages.empty and "annual_wage_gbp" in wages.columns:
        all_wages = pd.to_numeric(wages["annual_wage_gbp"], errors="coerce").dropna()

    axes.append(("Annual Wage", pct(all_wages, latest_wage) if len(all_wages) else 50))

    # Age percentile is descriptive, not performance.
    dob = pd.to_datetime(player_row.get("date_of_birth"), errors="coerce")
    age = (pd.Timestamp.now() - dob).days / 365.25 if pd.notna(dob) else np.nan
    # For age, invert so a younger age is visually "higher" as market profile,
    # while clearly labelling the axis as Age Advantage.
    age_series = (pd.Timestamp.now() - pd.to_datetime(p["date_of_birth"], errors="coerce")).dt.days / 365.25
    age_series = age_series.dropna()
    age_pct = 100 - pct(age_series, age) if len(age_series) else 50
    axes.append(("Age Advantage", age_pct))

    labels = [a[0] for a in axes]
    values = [max(5, min(100, a[1])) for a in axes]
    labels += [labels[0]]
    values += [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(33,230,162,.13)",
            line=dict(color=GREEN, width=2.4),
            marker=dict(color=GREEN, size=6),
            hovertemplate="%{theta}: %{r:.0f}th percentile<extra></extra>",
            name="Player",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=25, r=25, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=8),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0,100],
                tickvals=[25,50,75,100],
                tickfont=dict(color=MUTED_2, size=7),
                gridcolor=GRID,
                linecolor=GRID,
            ),
            angularaxis=dict(gridcolor=GRID, linecolor=GRID),
        ),
        showlegend=False,
    )
    return fig


def transfer_creation(transfers_df, valuation_df):
    t = transfers_df.copy()
    v = valuation_df.copy()

    if t.empty or v.empty:
        return pd.DataFrame()

    t["date"] = pd.to_datetime(t["transfer_date"], errors="coerce")
    t["fee"] = pd.to_numeric(t["transfer_fee"], errors="coerce")
    t = t.dropna(subset=["date"])
    t = t[t["fee"].notna() & (t["fee"] > 0)].sort_values("date")

    v["date"] = pd.to_datetime(v["date"], errors="coerce")
    v["value"] = pd.to_numeric(v["market_value_in_eur"], errors="coerce")
    v = v.dropna(subset=["date", "value"]).sort_values("date")

    rows = []
    for _, move in t.iterrows():
        later = t[t["date"] > move["date"]]["date"]
        end = later.min() if not later.empty else pd.Timestamp.max
        window = v[(v["date"] >= move["date"]) & (v["date"] < end)]
        if window.empty:
            continue
        peak = window["value"].max()
        rows.append({
            "date": move["date"],
            "move": f'{safe(move.get("from_club_name"))} → {safe(move.get("to_club_name"))}',
            "fee": move["fee"],
            "peak": peak,
            "change": (peak - move["fee"]) / move["fee"] * 100,
        })
    return pd.DataFrame(rows)


def transfer_creation_chart(df):
    if df.empty:
        return None
    labels = [d.strftime("%Y") for d in df["date"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=df["fee"]/1_000_000,
        name="Transfer Fee",
        marker_color="#2384C6",
        hovertemplate="%{x}<br>Fee: €%{y:.1f}M<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=labels,
        y=df["peak"]/1_000_000,
        name="Peak Value After Move",
        marker_color=GREEN,
        hovertemplate="%{x}<br>Peak value: €%{y:.1f}M<extra></extra>",
    ))
    fig.update_layout(
        height=300,
        barmode="group",
        margin=dict(l=5,r=5,t=15,b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT,size=8),
        xaxis=dict(gridcolor=GRID, title=""),
        yaxis=dict(gridcolor=GRID, title="€M"),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=8)),
        hovermode="x unified",
    )
    return fig


# ============================================================
# LOAD
# ============================================================
clubs = load_clubs()
players = load_players()
transfers = load_transfers()
valuations = load_player_valuations()
wages = load_player_wages()
heatmaps = load_heatmaps()

searchable = (
    players.dropna(subset=["name"])
    .drop_duplicates("player_id")
    .sort_values("name")
    .reset_index(drop=True)
)

if searchable.empty:
    st.error("players.csv contains no searchable player records.")
    st.stop()

names = searchable["name"].astype(str).tolist()
default = names.index("Erling Haaland") if "Erling Haaland" in names else 0

# ============================================================
# TOP NAV
# ============================================================
st.markdown(
    """
    <div class="sx-nav">
        <div class="sx-brand">
            <div class="sx-logo"></div>
            <div>
                <div class="sx-brand-name">Soccernomics</div>
                <div class="sx-brand-sub">Football. Data. Insights.</div>
            </div>
        </div>
        <div class="sx-navlinks">
            <span>Home</span>
            <span class="sx-nav-active">Players</span>
            <span>Clubs</span>
            <span>Competitions</span>
            <span>Market</span>
            <span>Analysis</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

crumb_col, search_col = st.columns([1.25, 2.0], gap="small")
with crumb_col:
    st.markdown('<div class="sx-crumb">Players &nbsp;›&nbsp; Player Market Profile</div>', unsafe_allow_html=True)
with search_col:
    selected_name = st.selectbox(
        "Search player",
        names,
        index=default,
        key="sx_player_search",
        label_visibility="visible",
    )

player = searchable[searchable["name"] == selected_name].iloc[0]
player_id = player["player_id"]

valuation = get_player_valuation_history(valuations, player_id)
transfers_player = get_player_transfer_history(transfers, player_id)
wage_rows = get_player_wage_history(wages, selected_name)
financials = player_career_financial_summary(transfers, player_id)

current_value = pd.to_numeric(player.get("market_value_in_eur"), errors="coerce")
peak_value = pd.to_numeric(player.get("highest_market_value_in_eur"), errors="coerce")
dob = pd.to_datetime(player.get("date_of_birth"), errors="coerce")
age = int((pd.Timestamp.now() - dob).days / 365.25) if pd.notna(dob) else None
contract = pd.to_datetime(player.get("contract_expiration_date"), errors="coerce")

latest_wage = wage_rows.iloc[-1] if wage_rows is not None and not wage_rows.empty else None
annual_wage = pd.to_numeric(latest_wage.get("annual_wage_gbp"), errors="coerce") if latest_wage is not None else np.nan
weekly_wage = pd.to_numeric(latest_wage.get("weekly_wage_gbp"), errors="coerce") if latest_wage is not None else np.nan

paid_fees = pd.to_numeric(transfers_player.get("transfer_fee"), errors="coerce") if not transfers_player.empty else pd.Series(dtype=float)
paid_fees = paid_fees[paid_fees > 0]
paid_count = len(paid_fees)
transfer_volume = paid_fees.sum() if paid_count else 0
avg_fee = transfer_volume / paid_count if paid_count else np.nan

largest_fee = paid_fees.max() if paid_count else np.nan

# ============================================================
# HERO
# ============================================================
hero_col, value_col = st.columns([3.65, 1.35], gap="small")

with hero_col:
    image_url = safe(player.get("image_url"), "")
    image_html = f'<img class="sx-player-image" src="{image_url}">' if image_url else ""

    position = map_position(player)
    position_label = role_name(position)
    club = safe(player.get("current_club_name"), "Club unavailable")
    country = safe(player.get("country_of_citizenship"), "")
    foot = safe(player.get("foot"), "").title()
    height = f'{int(player.get("height_in_cm"))} cm' if pd.notna(player.get("height_in_cm")) else "—"
    contract_text = contract.strftime("%b %Y") if pd.notna(contract) else "Unavailable"

    st.markdown(
        f"""
        <div class="sx-hero">
            <div class="sx-hero-glow"></div>
            {image_html}
            <div class="sx-hero-content">
                <div class="sx-player-name">
                    <span>{selected_name.split()[0] if selected_name.split() else selected_name}</span>
                    <span>{" ".join(selected_name.split()[1:])}</span>
                </div>
                <div class="sx-player-line">
                    <span class="sx-pill">{country}</span>
                    <span>{position_label} ({position})</span>
                    <span>•</span>
                    <span>{club}</span>
                </div>
                <div class="sx-hero-stats">
                    <div class="sx-hero-stat">
                        <div class="sx-hero-value">{age if age is not None else "—"}</div>
                        <div class="sx-hero-label">AGE</div>
                    </div>
                    <div class="sx-hero-stat">
                        <div class="sx-hero-value">{height}</div>
                        <div class="sx-hero-label">HEIGHT</div>
                    </div>
                    <div class="sx-hero-stat">
                        <div class="sx-hero-value">{foot if foot else "—"}</div>
                        <div class="sx-hero-label">PREFERRED FOOT</div>
                    </div>
                    <div class="sx-hero-stat">
                        <div class="sx-hero-value">{contract_text}</div>
                        <div class="sx-hero-label">CONTRACT UNTIL</div>
                    </div>
                </div>
                
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with value_col:
    peak_date = None
    if not valuation.empty and pd.notna(peak_value):
        vv = valuation.copy()
        vv["mv"] = pd.to_numeric(vv["market_value_in_eur"], errors="coerce")
        match = vv[vv["mv"] == peak_value]
        if not match.empty:
            peak_date = pd.to_datetime(match.iloc[0]["date"], errors="coerce")

    peak_text = (
        f'{format_eur_m(peak_value)} ({peak_date.strftime("%b %Y")})'
        if pd.notna(peak_value) and pd.notna(peak_date)
        else format_eur_m(peak_value) if pd.notna(peak_value) else "—"
    )

    st.markdown(
        f"""
        <div class="sx-value-panel">
            <div class="sx-value-title">Current Market Value</div>
            <div class="sx-value-main">{format_eur_m(current_value) if pd.notna(current_value) else "—"}</div>
            <div class="sx-value-change">● latest recorded value</div>
            <div style="height:10px"></div>
            <div class="sx-value-row"><span>Peak Value</span><span>{peak_text}</span></div>
            <div class="sx-value-row"><span>Latest Wage</span><span>{money_gbp(annual_wage)} / year</span></div>
            <div class="sx-value-row"><span>Contract</span><span>{contract_text}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# KPI STRIP
# ============================================================
kpis = [
    ("MARKET VALUE", format_eur_m(current_value) if pd.notna(current_value) else "—", "current", GREEN),
    ("PEAK VALUE", format_eur_m(peak_value) if pd.notna(peak_value) else "—", "career high", PURPLE),
    ("TOTAL TRANSFER VOLUME", format_eur_m(transfer_volume), f"{paid_count} paid moves", GREEN),
    ("AVG. TRANSFER FEE", format_eur_m(avg_fee) if pd.notna(avg_fee) else "—", "paid moves", CYAN),
    ("WEEKLY WAGE", money_gbp(weekly_wage), "latest record", BLUE),
    ("TOTAL PAID MOVES", str(paid_count), "recorded", PINK),
]

cols = st.columns(6, gap="small")
for col, (label, value, note, accent) in zip(cols, kpis):
    with col:
        st.markdown(
            f"""
            <div class="sx-kpi" style="--accent:{accent}">
                <div class="sx-kpi-label">{label}</div>
                <div class="sx-kpi-value">{value}</div>
                <div class="sx-kpi-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================
# VALUE + WAGE TRAJECTORIES
# ============================================================
value_col, wage_col = st.columns(2, gap="small")

with value_col:
    with styles.panel():
        st.markdown('<div class="sx-card-title">Market Value Trajectory</div>', unsafe_allow_html=True)
        st.markdown('<div class="sx-card-note">Recorded market value history — not transfer fees.</div>', unsafe_allow_html=True)

        if not valuation.empty:
            vd = valuation.copy()
            vd["date"] = pd.to_datetime(vd["date"], errors="coerce")
            vd["value_m"] = pd.to_numeric(vd["market_value_in_eur"], errors="coerce") / 1_000_000
            vd = vd.dropna(subset=["date","value_m"]).sort_values("date")
            if not vd.empty:
                fig = line_chart(vd, "date", "value_m", GREEN, "€M")
                fig.update_traces(
                    hovertemplate="%{x|%b %Y}<br>€%{y:.1f}M<extra></extra>"
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
                first = vd.iloc[0]["value_m"]
                last = vd.iloc[-1]["value_m"]
                st.caption(f"Available range: €{first:.1f}M → €{last:.1f}M")
        else:
            st.caption("No market-value history is available for this player.")

with wage_col:
    with styles.panel():
        st.markdown('<div class="sx-card-title">Wage Trajectory</div>', unsafe_allow_html=True)
        st.markdown('<div class="sx-card-note">Annual wages by available season.</div>', unsafe_allow_html=True)

        if wage_rows is not None and not wage_rows.empty and "annual_wage_gbp" in wage_rows.columns:
            wd = wage_rows.copy()
            wd["annual_m"] = pd.to_numeric(wd["annual_wage_gbp"], errors="coerce") / 1_000_000
            wd = wd.dropna(subset=["annual_m"]).sort_values("season")
            if not wd.empty:
                fig = line_chart(wd, "season", "annual_m", CYAN, "£M / year")
                fig.update_traces(
                    hovertemplate="%{x}<br>£%{y:.2f}M / year<extra></extra>"
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
                if len(wd) > 1:
                    change = (wd.iloc[-1]["annual_m"] - wd.iloc[-2]["annual_m"]) / wd.iloc[-2]["annual_m"] * 100 if wd.iloc[-2]["annual_m"] else np.nan
                    st.caption(f"Latest recorded wage: £{wd.iloc[-1]['annual_m']:.2f}M / year" + (f" · {change:+.1f}% vs previous record" if pd.notna(change) else ""))
                else:
                    st.caption(f"Latest recorded wage: £{wd.iloc[-1]['annual_m']:.2f}M / year")
        else:
            st.caption("No annual wage history is available for this player.")

# ============================================================
# THREE-COLUMN ANALYTICS
# ============================================================
heat_col, radar_col, creation_col = st.columns([1, 1, 1], gap="small")

# ---------- Heatmap ----------
with heat_col:
    with styles.panel():
        st.markdown(
            '<div class="sx-card-title">Positional Heatmap <span style="color:#71879A;font-weight:500">(Role-Based Model)</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sx-card-note">Illustrative positional zones on a 105 × 68 m pitch — not actual tracking.</div>',
            unsafe_allow_html=True,
        )

        if not heatmaps.empty:
            available = heatmaps["position"].astype(str).unique().tolist()
            role_position = position if position in available else available[0]
            role_data = heatmaps[heatmaps["position"].astype(str) == role_position]
            styles_available = role_data["style"].astype(str).unique().tolist()

            c1, c2 = st.columns(2, gap="small")
            with c1:
                shown_position = st.selectbox(
                    "Position",
                    available,
                    index=available.index(role_position),
                    key=f"heat_pos_{player_id}",
                    format_func=lambda x: f"{role_name(x)} ({x})",
                )
            role_data = heatmaps[heatmaps["position"].astype(str) == shown_position]
            styles_available = role_data["style"].astype(str).unique().tolist()

            with c2:
                chosen_style = st.selectbox(
                    "Role Variation",
                    styles_available,
                    key=f"heat_style_{player_id}_{shown_position}",
                )

            selected_heat = role_data[role_data["style"].astype(str) == chosen_style]
            st.plotly_chart(
                heatmap_chart(selected_heat),
                width="stretch",
                config={"displayModeBar": False},
            )
            st.markdown(
                f'<div class="sx-footnote">Based on positional model · {role_name(shown_position)} · {chosen_style}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Position heatmap dataset not found in data/raw.")

# ---------- Financial radar ----------
with radar_col:
    with styles.panel():
        st.markdown(
            '<div class="sx-card-title">Market Profile <span style="color:#71879A;font-weight:500">(vs Position)</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sx-card-note">Percentiles calculated from the project’s market, wage and transfer data.</div>',
            unsafe_allow_html=True,
        )

        try:
            radar = market_profile_radar(player, players, transfers, wages, valuations, position)
            st.plotly_chart(radar, width="stretch", config={"displayModeBar": False})
            st.markdown(
                '<div style="display:flex;justify-content:center;gap:16px;color:#7B90A2;font-size:.61rem;"><span><b style="color:#21E6A2">■</b> Player</span><span><b style="color:#AAB8C2">●</b> 50th percentile</span></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.caption("Market profile could not be calculated from the available financial records.")

# ---------- Transfer value creation ----------
with creation_col:
    with styles.panel():
        st.markdown(
            '<div class="sx-card-title">Transfer Value Creation <span style="color:#71879A;font-weight:500">ⓘ</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sx-card-note">Transfer fee vs highest recorded market value before the next move.</div>',
            unsafe_allow_html=True,
        )

        creation = transfer_creation(transfers_player, valuation)
        if not creation.empty:
            st.plotly_chart(
                transfer_creation_chart(creation),
                width="stretch",
                config={"displayModeBar": False},
            )

            for _, r in creation.iterrows():
                st.markdown(
                    f"""
                    <div class="sx-timeline-row">
                        <span class="sx-timeline-date">{r["date"].strftime("%Y")}</span>
                        <span class="sx-timeline-club">{r["move"]}</span>
                        <span class="sx-timeline-fee">{format_eur_m(r["fee"])} → {format_eur_m(r["peak"])}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Insufficient transfer and valuation history for this analysis.")

# ============================================================
# PROFILE / CAREER / SIMILAR
# ============================================================
profile_col, career_col, similar_col = st.columns([1, 1, 1], gap="small")

# ---------- Profile ----------
with profile_col:
    with styles.panel():
        st.markdown('<div class="sx-card-title">Player Profile</div>', unsafe_allow_html=True)
        st.markdown('<div class="sx-card-note">Core player information.</div>', unsafe_allow_html=True)

        profile = [
            ("Full Name", safe(player.get("name"))),
            ("Date of Birth", dob.strftime("%d %b %Y") if pd.notna(dob) else "—"),
            ("Nationality", safe(player.get("country_of_citizenship"))),
            ("Position", f"{position_label} ({position})"),
            ("Height", height),
            ("Preferred Foot", foot),
            ("Current Club", club),
            ("Contract Until", contract_text),
        ]
        for label, value in profile:
            st.markdown(
                f'<div class="sx-profile-row"><span class="sx-profile-label">{label}</span><span class="sx-profile-value">{value}</span></div>',
                unsafe_allow_html=True,
            )

# ---------- Career timeline ----------
with career_col:
    with styles.panel():
        st.markdown('<div class="sx-card-title">Career Timeline</div>', unsafe_allow_html=True)
        st.markdown('<div class="sx-card-note">Recorded transfer sequence.</div>', unsafe_allow_html=True)

        if not transfers_player.empty:
            td = transfers_player.copy()
            td["date"] = pd.to_datetime(td["transfer_date"], errors="coerce")
            td = td.sort_values("date")

            for _, r in td.iterrows():
                fee = pd.to_numeric(r.get("transfer_fee"), errors="coerce")
                fee_text = format_eur_m(fee) if pd.notna(fee) and fee > 0 else "Free"
                st.markdown(
                    f"""
                    <div class="sx-timeline-row">
                        <span class="sx-timeline-date">{r["date"].strftime("%Y") if pd.notna(r["date"]) else "—"}</span>
                        <span class="sx-timeline-club">{safe(r.get("from_club_name"))} → {safe(r.get("to_club_name"))}</span>
                        <span class="sx-timeline-fee">{fee_text}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No transfer timeline available.")

# ---------- Similar players ----------
with similar_col:
    with styles.panel():
        st.markdown('<div class="sx-card-title">Similar Players <span style="color:#71879A">(Market Value)</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="sx-card-note">Players with similar recorded market values in the same broad position.</div>', unsafe_allow_html=True)

        sp = players.copy()
        sp["mv"] = pd.to_numeric(sp["market_value_in_eur"], errors="coerce")
        sp = sp.dropna(subset=["mv"])
        broad_pos = safe(player.get("position"), "")
        if broad_pos:
            same = sp[sp["position"].astype(str).str.contains(broad_pos, case=False, na=False)].copy()
            if len(same) >= 6:
                sp = same

        target = current_value if pd.notna(current_value) else sp["mv"].median()
        sp["distance"] = (sp["mv"] - target).abs()
        sp = sp[sp["player_id"] != player_id].sort_values("distance").head(5)

        max_mv = max(sp["mv"].max() if not sp.empty else 1, target, 1)

        for _, r in sp.iterrows():
            img = safe(r.get("image_url"), "")
            avatar = f'<img class="sx-sim-avatar" src="{img}">' if img else '<div class="sx-sim-avatar"></div>'
            pct = max(3, min(100, float(r["mv"] / max_mv * 100)))

            st.markdown(
                f"""
                <div class="sx-similar-row">
                    {avatar}
                    <span style="color:#DCE7EE;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{safe(r.get("name"))}</span>
                    <div class="sx-bar"><div style="width:{pct:.0f}%"></div></div>
                    <span class="sx-sim-value">{format_eur_m(r["mv"])}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ============================================================
# TRANSFER HISTORY
# ============================================================
with styles.panel():
    st.markdown('<div class="sx-card-title">Transfer History <span class="sx-export">⇩ Export</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sx-card-note">Complete recorded transfer sequence for the selected player.</div>', unsafe_allow_html=True)

    if not transfers_player.empty:
        rows = []
        for _, r in transfers_player.iterrows():
            date = pd.to_datetime(r.get("transfer_date"), errors="coerce")
            fee = pd.to_numeric(r.get("transfer_fee"), errors="coerce")
            mv = pd.to_numeric(r.get("market_value_in_eur"), errors="coerce")

            rows.append(
                f"""
                <tr>
                    <td>{date.strftime("%b %Y") if pd.notna(date) else "—"}</td>
                    <td>{safe(r.get("from_club_name"))}</td>
                    <td>{safe(r.get("to_club_name"))}</td>
                    <td>{format_eur_m(fee) if pd.notna(fee) and fee > 0 else "Free / undisclosed"}</td>
                    <td>{format_eur_m(mv) if pd.notna(mv) else "—"}</td>
                </tr>
                """
            )

        st.markdown(
            f"""
            <div class="sx-table-wrap">
                <table class="sx-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>From</th>
                            <th>To</th>
                            <th>Fee</th>
                            <th>Market Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("No transfer history is available.")

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    """
    <div class="sx-footer">
        <div><b style="color:#B9C9D5">Soccernomics</b><br>Football. Data. Insights.</div>
        <div>Turning football data into deeper understanding.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
