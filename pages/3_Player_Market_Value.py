import os
import re
import sys
from datetime import datetime
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import styles
from utils import (
    RAW_DIR,
    load_players,
    load_transfers,
    load_player_valuations,
    load_player_wages,
    get_player_valuation_history,
    get_player_transfer_history,
    player_career_financial_summary,
    get_player_wage_history,
    format_eur_m,
)
from gemini_utils import get_ai_player_research


st.set_page_config(
    page_title="Soccernomics — Player Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)
styles.inject()


# ============================================================
# Small page-only helpers
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
        return f"£{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"£{value / 1_000:.1f}K"
    return f"£{value:,.0f}"


def map_position(row):
    text = f"{norm(row.get('sub_position'))} {norm(row.get('position'))}"
    rules = [
        (("goalkeeper",), "GK"),
        (("centre forward", "center forward", "striker", "second striker"), "CF"),
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
    return direct if direct in {"GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "CF"} else "CF"


ROLE_NAMES = {
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


def role_name(position):
    return ROLE_NAMES.get(position, position)


@st.cache_data(ttl=1800, show_spinner=False)
def load_current_pl_roster():
    """Fetch the current Premier League fantasy roster for player discovery only.

    We intentionally do not use the FPL performance fields here. Current-season
    performance is still sourced through Gemini's grounded research layer.
    """
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Soccernomics/1.0",
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=8) as response:
            payload = response.read().decode("utf-8")
        data = __import__("json").loads(payload)

        teams = {
            int(t["id"]): t["name"]
            for t in data.get("teams", [])
        }

        rows = []
        for item in data.get("elements", []):
            team_id = int(item.get("team", 0) or 0)
            first = str(item.get("first_name", "")).strip()
            second = str(item.get("second_name", "")).strip()
            web_name = str(item.get("web_name", "")).strip()

            full_name = " ".join(x for x in [first, second] if x).strip() or web_name
            if not full_name:
                continue

            rows.append(
                {
                    "fpl_id": item.get("id"),
                    "name": full_name,
                    "web_name": web_name or full_name,
                    "club": teams.get(team_id, "Premier League"),
                    "team_id": team_id,
                    "position_type": item.get("element_type"),
                }
            )

        roster = pd.DataFrame(rows)
        if roster.empty:
            return roster

        return roster.drop_duplicates(
            subset=["name", "club"]
        ).reset_index(drop=True)

    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def cached_player_research(player_name, season="2026/27"):
    """Gemini is used for current-season football performance only."""
    try:
        return get_ai_player_research(
            player_name,
            season,
            "Premier League",
        )
    except Exception as exc:
        return {
            "ok": False,
            "statistics": {},
            "limitations": f"Research unavailable: {exc}",
        }


@st.cache_data(ttl=3600, show_spinner=False)
def load_heatmaps():
    path = os.path.join(RAW_DIR, "position_heatmaps_dataset.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        required = {"position", "style", "x_m", "y_m", "weight"}
        if not required.issubset(df.columns):
            return pd.DataFrame()
        for col in ["x_m", "y_m", "weight"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna(subset=["position", "style", "x_m", "y_m", "weight"])
    except Exception:
        return pd.DataFrame()


def pitch_shapes():
    line = "#91A79C"
    return [
        dict(type="rect", x0=0, y0=0, x1=105, y1=68, line=dict(color=line, width=1.2)),
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
        height=310,
        margin=dict(l=3, r=3, t=3, b=3),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#08160F",
        xaxis=dict(visible=False, range=[-1, 106], fixedrange=True),
        yaxis=dict(
            visible=False,
            range=[-1, 69],
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True,
        ),
        showlegend=False,
    )
    return fig


def line_chart(df, x, y, color, y_title, height=270, hover=None):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(color=color, size=5),
            fill="tozeroy",
            fillcolor="rgba(47,191,113,.045)",
            hovertemplate=hover or "%{x}<br>%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D7E4DE", size=9),
        xaxis=dict(gridcolor="#223029", zeroline=False),
        yaxis=dict(gridcolor="#223029", zeroline=False, title=y_title),
        showlegend=False,
    )
    return fig


def transfer_value_chart(df):
    fig = go.Figure()
    labels = [d.strftime("%Y") for d in df["date"]]
    fig.add_trace(
        go.Bar(
            x=labels,
            y=df["fee"] / 1_000_000,
            name="Transfer fee",
            marker_color="#5B9BD5",
            hovertemplate="%{x}<br>Fee: €%{y:.1f}M<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=df["market_value"] / 1_000_000,
            name="Market value at move",
            marker_color="#2FBF71",
            hovertemplate="%{x}<br>Market value: €%{y:.1f}M<extra></extra>",
        )
    )
    fig.update_layout(
        height=290,
        barmode="group",
        margin=dict(l=8, r=8, t=12, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D7E4DE", size=9),
        xaxis=dict(gridcolor="#223029"),
        yaxis=dict(gridcolor="#223029", title="€M"),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    return fig


def transfer_value_rows(transfers_player):
    t = transfers_player.copy()
    if t.empty:
        return pd.DataFrame()
    t["date"] = pd.to_datetime(t["transfer_date"], errors="coerce")
    t["fee"] = pd.to_numeric(t["transfer_fee"], errors="coerce")
    t["market_value"] = pd.to_numeric(t["market_value_in_eur"], errors="coerce")
    t = t.dropna(subset=["date"])
    t = t[t["fee"].notna() & (t["fee"] > 0)]
    t = t.sort_values("date")
    return t


def performance_value(stats, key):
    value = (stats or {}).get(key)
    if value is None or pd.isna(value):
        return "—"
    try:
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return f"{number:.2f}"
    except Exception:
        return safe(value)


def performance_note(research):
    if not research or not research.get("ok"):
        return "Current-season performance could not be verified."
    source = research.get("primary_stats_source") or "Grounded football-statistics sources"
    as_of = research.get("data_as_of")
    return f"Source: {source}" + (f" · as of {as_of}" if as_of else "")


# ============================================================
# Data
# ============================================================

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

# The historical player database is retained for financial history.
# Current PL discovery comes from the live FPL roster so recent signings/
# registrations absent from players.csv (e.g. Gyökeres, João Pedro) are still searchable.
current_pl = load_current_pl_roster()

if not current_pl.empty:
    current_pl["search_key"] = (
        current_pl["name"].map(norm) + " " + current_pl["web_name"].map(norm)
    )
    current_pl = current_pl.drop_duplicates(["name", "club"]).reset_index(drop=True)

historical_names = searchable["name"].astype(str).tolist()

if "player_search_query" not in st.session_state:
    st.session_state.player_search_query = "Erling Haaland"
if "player_search_results" not in st.session_state:
    st.session_state.player_search_results = [
        {"label": "Erling Haaland · Manchester City", "name": "Erling Haaland", "club": "Manchester City", "source": "local"}
    ]
if "selected_player_key" not in st.session_state:
    st.session_state.selected_player_key = "Erling Haaland|Manchester City|local"

# ============================================================
# Header + search
# ============================================================

styles.header(
    "Player Analytics",
    "Market value, wages, transfer economics, performance and positional intelligence.",
)

with st.form("player_search_form", clear_on_submit=False):
    search_col, button_col = st.columns([5.7, 1], gap="small")
    with search_col:
        query = st.text_input(
            "Search player",
            value=st.session_state.player_search_query,
            placeholder="Type a player name...",
        )
    with button_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Search", use_container_width=True)

if submitted:
    q = norm(query)
    result_rows = []

    # 1) Current PL roster first — this is what fixes Pedro/João Pedro/Gyökeres
    # and other recent signings missing from the historical players.csv.
    if q and not current_pl.empty:
        current_matches = current_pl[
            current_pl["search_key"].str.contains(re.escape(q), regex=True, na=False)
        ].copy()

        # Prefix matches first, then substring matches.
        current_matches["rank"] = current_matches.apply(
            lambda r: 0 if norm(r["name"]).startswith(q) or norm(r["web_name"]).startswith(q) else 1,
            axis=1,
        )
        current_matches = current_matches.sort_values(["rank", "name", "club"])

        for _, r in current_matches.head(12).iterrows():
            result_rows.append(
                {
                    "label": f"{r['name']} · {r['club']}",
                    "name": r["name"],
                    "club": r["club"],
                    "source": "fpl",
                }
            )

    # 2) Historical database fallback/addition.
    if q:
        hist_matches = searchable[
            searchable["name"].map(norm).str.contains(re.escape(q), regex=True, na=False)
        ].copy()
        for _, r in hist_matches.iterrows():
            club_name = safe(r.get("current_club_name"), "")
            label = f"{r['name']} · {club_name}" if club_name else str(r["name"])
            candidate = {
                "label": label,
                "name": str(r["name"]),
                "club": club_name,
                "source": "local",
            }
            if not any(
                x["name"] == candidate["name"] and x["club"] == candidate["club"]
                for x in result_rows
            ):
                result_rows.append(candidate)
            if len(result_rows) >= 12:
                break
    else:
        result_rows = [
            {
                "label": f"{r['name']} · {r['club']}",
                "name": r["name"],
                "club": r["club"],
                "source": "fpl",
            }
            for _, r in current_pl.head(12).iterrows()
        ]

    result_rows = result_rows[:12]
    st.session_state.player_search_query = query
    st.session_state.player_search_results = result_rows

results = st.session_state.player_search_results

if not results:
    st.warning(
        "No player found. Try a current Premier League player name, "
        "surname, or a shorter search."
    )
    st.stop()

labels = [r["label"] for r in results]
keys = [f"{r['name']}|{r['club']}|{r['source']}" for r in results]

if len(results) == 1:
    selected_idx = 0
else:
    selected_idx = st.selectbox(
        "Matching players",
        range(len(results)),
        index=(
            keys.index(st.session_state.selected_player_key)
            if st.session_state.selected_player_key in keys
            else 0
        ),
        format_func=lambda i: labels[i],
        label_visibility="collapsed",
        key="player_result_select",
    )

selected_result = results[selected_idx]
selected_name = selected_result["name"]
selected_club = selected_result["club"]
selected_source = selected_result["source"]

st.session_state.selected_player_key = (
    f"{selected_name}|{selected_club}|{selected_source}"
)

player_rows = searchable[searchable["name"].map(norm) == norm(selected_name)]

# If the current PL roster contains a player absent from players.csv,
# create a lightweight profile record. Financial history remains unavailable
# rather than being fabricated.
is_local_player = not player_rows.empty

if is_local_player:
    player = player_rows.iloc[0]
    player_id = player["player_id"]
else:
    roster_rows = current_pl[
        (current_pl["name"] == selected_name)
        & (current_pl["club"] == selected_club)
    ]
    roster_row = roster_rows.iloc[0] if not roster_rows.empty else pd.Series(dtype=object)

    player = pd.Series(
        {
            "player_id": np.nan,
            "name": selected_name,
            "current_club_name": selected_club,
            "country_of_citizenship": "—",
            "sub_position": "—",
            "position": "—",
            "image_url": "",
            "market_value_in_eur": np.nan,
            "highest_market_value_in_eur": np.nan,
            "date_of_birth": pd.NaT,
            "contract_expiration_date": pd.NaT,
        }
    )
    player_id = np.nan

valuation = (
    get_player_valuation_history(valuations, player_id)
    if is_local_player
    else pd.DataFrame()
)
transfers_player = (
    get_player_transfer_history(transfers, player_id)
    if is_local_player
    else pd.DataFrame()
)
wage_rows = (
    get_player_wage_history(wages, selected_name)
    if is_local_player
    else pd.DataFrame()
)
financials = (
    player_career_financial_summary(transfers, player_id)
    if is_local_player
    else {}
)

position = map_position(player)
position_label = role_name(position)
club = selected_club or safe(player.get("current_club_name"), "Club unavailable")
country = safe(player.get("country_of_citizenship"), "Country unavailable")
image_url = safe(player.get("image_url"), "")

current_value = pd.to_numeric(player.get("market_value_in_eur"), errors="coerce")
peak_value = pd.to_numeric(player.get("highest_market_value_in_eur"), errors="coerce")
dob = pd.to_datetime(player.get("date_of_birth"), errors="coerce")
age = int((pd.Timestamp.now() - dob).days / 365.25) if pd.notna(dob) else None
contract = pd.to_datetime(player.get("contract_expiration_date"), errors="coerce")

latest_wage = wage_rows.iloc[-1] if wage_rows is not None and not wage_rows.empty else None
annual_wage = (
    pd.to_numeric(latest_wage.get("annual_wage_gbp"), errors="coerce")
    if latest_wage is not None
    else np.nan
)
weekly_wage = (
    pd.to_numeric(latest_wage.get("weekly_wage_gbp"), errors="coerce")
    if latest_wage is not None
    else np.nan
)

paid_fees = (
    pd.to_numeric(transfers_player.get("transfer_fee"), errors="coerce")
    if not transfers_player.empty
    else pd.Series(dtype=float)
)
paid_fees = paid_fees[paid_fees > 0]
paid_count = len(paid_fees)
transfer_volume = paid_fees.sum() if paid_count else 0
largest_fee = paid_fees.max() if paid_count else np.nan

# ============================================================
# Current-season performance — Gemini only
# ============================================================

CURRENT_SEASON = "2026/27"

with st.spinner(f"Researching {selected_name}'s {CURRENT_SEASON} Premier League statistics..."):
    research = cached_player_research(selected_name, CURRENT_SEASON)

stats = research.get("statistics", {}) if research and research.get("ok") else {}

valuation = get_player_valuation_history(valuations, player_id)
transfers_player = get_player_transfer_history(transfers, player_id)
wage_rows = get_player_wage_history(wages, selected_name)
financials = player_career_financial_summary(transfers, player_id)

position = map_position(player)
position_label = role_name(position)
club = safe(player.get("current_club_name"), "Club unavailable")
country = safe(player.get("country_of_citizenship"), "Country unavailable")
image_url = safe(player.get("image_url"), "")

current_value = pd.to_numeric(player.get("market_value_in_eur"), errors="coerce")
peak_value = pd.to_numeric(player.get("highest_market_value_in_eur"), errors="coerce")
dob = pd.to_datetime(player.get("date_of_birth"), errors="coerce")
age = int((pd.Timestamp.now() - dob).days / 365.25) if pd.notna(dob) else None
contract = pd.to_datetime(player.get("contract_expiration_date"), errors="coerce")

latest_wage = wage_rows.iloc[-1] if wage_rows is not None and not wage_rows.empty else None
annual_wage = (
    pd.to_numeric(latest_wage.get("annual_wage_gbp"), errors="coerce")
    if latest_wage is not None
    else np.nan
)
weekly_wage = (
    pd.to_numeric(latest_wage.get("weekly_wage_gbp"), errors="coerce")
    if latest_wage is not None
    else np.nan
)

paid_fees = (
    pd.to_numeric(transfers_player.get("transfer_fee"), errors="coerce")
    if not transfers_player.empty
    else pd.Series(dtype=float)
)
paid_fees = paid_fees[paid_fees > 0]
paid_count = len(paid_fees)
transfer_volume = paid_fees.sum() if paid_count else 0
largest_fee = paid_fees.max() if paid_count else np.nan

# ============================================================
# Hero
# ============================================================

hero_col, value_col = st.columns([3.6, 1.4], gap="small")

with hero_col:
    img = (
        f'<img src="{image_url}" style="width:105px;height:105px;object-fit:cover;'
        f'border-radius:10px;border:1px solid #2B3D34;">'
        if image_url
        else ""
    )

    st.markdown(
        f"""
        <div style="
            border:1px solid #223029;
            border-radius:12px;
            background:linear-gradient(135deg,#101A15,#0D1511);
            padding:20px 22px;
            min-height:120px;
            display:flex;
            align-items:center;
            gap:20px;
        ">
            {img}
            <div>
                <div style="font-size:2rem;font-weight:800;color:#EAF2ED;line-height:1.05;">
                    {selected_name}
                </div>
                <div style="color:#91A79C;margin-top:8px;font-size:.9rem;">
                    {club} · {position_label} · {country}
                </div>
                <div style="display:flex;gap:8px;margin-top:12px;">
                    <span style="padding:4px 9px;border-radius:14px;background:#123522;
                    border:1px solid #1D6B43;color:#61D89A;font-size:.72rem;">
                        {age if age is not None else "—"} yrs
                    </span>
                    <span style="padding:4px 9px;border-radius:14px;background:#123522;
                    border:1px solid #1D6B43;color:#61D89A;font-size:.72rem;">
                        {position}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with value_col:
    if not is_local_player:
        st.caption(
            "Current PL roster found from the live FPL player registry. "
            "This player is not present in the project's historical financial datasets."
        )
    styles.kpi_card(
        "Current market value",
        format_eur_m(current_value) if pd.notna(current_value) else "—",
        f"Peak: {format_eur_m(peak_value)}",
    )
    st.caption(f"Latest annual wage: {money_gbp(annual_wage)}")

# ============================================================
# Financial snapshot
# ============================================================

styles.section_label("Financial Snapshot")

kpi_values = [
    ("Market value", format_eur_m(current_value) if pd.notna(current_value) else "—", "latest recorded"),
    ("Peak value", format_eur_m(peak_value) if pd.notna(peak_value) else "—", "career high"),
    ("Transfer volume", format_eur_m(transfer_volume) if is_local_player else "—", f"{paid_count} paid moves" if is_local_player else "not in local dataset"),
    ("Largest fee", format_eur_m(largest_fee) if is_local_player and pd.notna(largest_fee) else "—", "recorded career move" if is_local_player else "not in local dataset"),
    ("Annual wage", money_gbp(annual_wage) if is_local_player else "—", "latest wage record" if is_local_player else "not in local dataset"),
]

cols = st.columns(5, gap="small")
for col, (label, value, note) in zip(cols, kpi_values):
    with col:
        styles.kpi_card(label, value, note)

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

# ============================================================
# Player performance
# ============================================================

styles.section_label(f"Player Performance · {CURRENT_SEASON}")

perf_items = [
    ("Appearances", performance_value(stats, "appearances")),
    ("Minutes", performance_value(stats, "minutes")),
    ("Goals", performance_value(stats, "goals")),
    ("Assists", performance_value(stats, "assists")),
    ("Shots", performance_value(stats, "shots")),
    ("On target", performance_value(stats, "shots_on_target")),
    ("xG", performance_value(stats, "xg")),
    ("xA", performance_value(stats, "xa")),
]

cols = st.columns(8, gap="small")
for col, (label, value) in zip(cols, perf_items):
    with col:
        styles.kpi_card(label, value)

st.caption(performance_note(research))

# ============================================================
# Financial visuals
# ============================================================

styles.section_label("Player Economics")

value_col, wage_col = st.columns(2, gap="small")

with value_col:
    with styles.panel():
        styles.section_label("Market Value Trajectory")
        st.caption("Recorded market-value history, independent of transfer fees.")
        if not valuation.empty:
            vd = valuation.copy()
            vd["date"] = pd.to_datetime(vd["date"], errors="coerce")
            vd["value_m"] = pd.to_numeric(vd["market_value_in_eur"], errors="coerce") / 1_000_000
            vd = vd.dropna(subset=["date", "value_m"]).sort_values("date")
            if not vd.empty:
                fig = line_chart(
                    vd,
                    "date",
                    "value_m",
                    "#2FBF71",
                    "€M",
                    hover="%{x|%b %Y}<br>€%{y:.1f}M<extra></extra>",
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.caption("No market-value history available.")

with wage_col:
    with styles.panel():
        styles.section_label("Wage Trajectory")
        st.caption("Annual wages across the available wage dataset.")
        if wage_rows is not None and not wage_rows.empty and "annual_wage_gbp" in wage_rows.columns:
            wd = wage_rows.copy()
            wd["annual_m"] = pd.to_numeric(wd["annual_wage_gbp"], errors="coerce") / 1_000_000
            wd = wd.dropna(subset=["annual_m"]).sort_values("season")
            if not wd.empty:
                fig = line_chart(
                    wd,
                    "season",
                    "annual_m",
                    "#E8B75D",
                    "£M / year",
                    hover="%{x}<br>£%{y:.2f}M / year<extra></extra>",
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.caption("No wage history available for this player.")

# ============================================================
# Positional intelligence + transfer economics
# ============================================================

heat_col, transfer_col = st.columns(2, gap="small")

with heat_col:
    with styles.panel():
        styles.section_label("Positional Heatmap")
        st.caption(
            "Synthetic role-based positional model — not event-level tracking. "
            "Use the controls to compare positional styles."
        )

        if not heatmaps.empty:
            available_positions = sorted(
                heatmaps["position"].astype(str).unique().tolist()
            )
            default_position = position if position in available_positions else available_positions[0]

            shown_position = st.selectbox(
                "Position",
                available_positions,
                index=available_positions.index(default_position),
                format_func=lambda x: f"{role_name(x)} ({x})",
                key=f"heat_position_{player_id}",
            )

            role_data = heatmaps[
                heatmaps["position"].astype(str) == shown_position
            ]
            styles_available = sorted(role_data["style"].astype(str).unique().tolist())

            chosen_style = st.selectbox(
                "Role variation",
                styles_available,
                key=f"heat_style_{player_id}_{shown_position}",
            )

            selected_heat = role_data[
                role_data["style"].astype(str) == chosen_style
            ]

            st.plotly_chart(
                heatmap_chart(selected_heat),
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption(
                f"Modelled role: {role_name(shown_position)} · {chosen_style}"
            )
        else:
            st.warning("position_heatmaps_dataset.csv was not found.")

with transfer_col:
    with styles.panel():
        styles.section_label("Transfer Fee vs Market Value")
        st.caption(
            "Financial comparison at each recorded paid transfer. "
            "A gap does not represent club profit."
        )

        tv = transfer_value_rows(transfers_player)

        if not tv.empty:
            fig = transfer_value_chart(tv)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            priced = tv.dropna(subset=["market_value"])
            if not priced.empty:
                priced = priced.copy()
                priced["gap_pct"] = (
                    (priced["market_value"] - priced["fee"])
                    / priced["market_value"]
                    * 100
                )
                avg_gap = priced["gap_pct"].mean()
                latest_gap = priced.iloc[-1]["gap_pct"]

                a, b = st.columns(2)
                with a:
                    styles.kpi_card(
                        "Avg value discount",
                        f"{avg_gap:+.1f}%",
                        "market value vs fee",
                    )
                with b:
                    styles.kpi_card(
                        "Latest value gap",
                        f"{latest_gap:+.1f}%",
                        "latest priced move",
                    )
        else:
            st.caption("No paid transfer records with comparable market values.")

# ============================================================
# Transfer history
# ============================================================

styles.section_label("Transfer History")

with styles.panel():
    if not transfers_player.empty:
        rows = transfers_player.copy()
        rows["Date"] = pd.to_datetime(rows["transfer_date"], errors="coerce").dt.strftime("%b %Y")
        rows["Fee"] = pd.to_numeric(rows["transfer_fee"], errors="coerce").apply(
            lambda x: format_eur_m(x) if pd.notna(x) and x > 0 else "Free / undisclosed"
        )
        rows["Market value"] = pd.to_numeric(
            rows["market_value_in_eur"], errors="coerce"
        ).apply(lambda x: format_eur_m(x) if pd.notna(x) else "—")
        display = rows[
            ["Date", "from_club_name", "to_club_name", "Fee", "Market value"]
        ].rename(
            columns={
                "from_club_name": "From",
                "to_club_name": "To",
            }
        )
        st.dataframe(display, hide_index=True, width="stretch")
    else:
        st.caption("No transfer history is available for this player.")

# ============================================================
# Current scouting research
# ============================================================

styles.section_label("Current Research")

if research and research.get("ok"):
    summary = research.get("scouting_summary")
    notes = research.get("statistics_notes")
    limitations = research.get("limitations")

    if summary:
        with styles.panel():
            st.markdown(summary)

    if notes:
        st.caption(notes)

    if limitations:
        st.caption(f"Limitations: {limitations}")
else:
    st.caption(
        "Gemini research is unavailable for this player. "
        "Financial and positional sections above continue to use local project data."
    )

# ============================================================
# Methodology
# ============================================================

with st.expander("Methodology & data limitations"):
    st.markdown(
        """
        - **Player search:** current Premier League roster discovery comes from the live FPL player registry, while the historical `players.csv` remains available as a fallback. Only a small result set is rendered, avoiding a giant Streamlit selectbox.
        - **Market value:** from the project's player valuation dataset.
        - **Wages:** from the project's Premier League wage dataset.
        - **Transfer economics:** compares recorded transfer fees with recorded
          market values. This is not a measure of club profit.
        - **Positional heatmap:** synthetic role-based positional model supplied for
          the project. It is illustrative and is not player tracking data.
        - **Performance:** current-season values are retrieved through Gemini's
          grounded football-statistics research layer when available. Missing values
          remain unavailable rather than being invented.
        """
    )

st.markdown(
    "<div style='height:1rem'></div><div style='text-align:center;color:#5C6E66;font-size:.75rem;'>"
    "Soccernomics · Football. Data. Insights."
    "</div>",
    unsafe_allow_html=True,
)
