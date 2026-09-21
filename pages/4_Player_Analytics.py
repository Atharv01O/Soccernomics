# ============================================================
# SOCCERNOMICS — PLAYER ANALYTICS & PERFORMANCE ROI
# ============================================================

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
    load_player_appearances_summary,
    get_player_performance_history,
    calculate_player_cost_per_performance,
    get_player_valuation_history,
    get_player_transfer_history,
    player_career_financial_summary,
    get_player_wage_history,
    format_eur_m,
    player_peak_vs_current,
    market_value_by_age_distribution,
)
from gemini_utils import get_ai_player_research


st.set_page_config(
    page_title="Soccernomics — Player Analytics",
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


# ============================================================
# Helpers
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
    """Fetch current Premier League roster for live player discovery."""
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Soccernomics/1.0",
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=6) as response:
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

        return roster.drop_duplicates(subset=["name", "club"]).reset_index(drop=True)

    except Exception:
        return pd.DataFrame()


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
    line = "#2D3D35"
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
                [0, "rgba(18,24,21,.02)"],
                [.18, "#0D4A30"],
                [.38, "#12834F"],
                [.58, "#19BA73"],
                [.76, "#A9D94E"],
                [.9, "#FFD34E"],
                [1, "#FF5D52"],
            ],
            showscale=False,
            hovertemplate="Role activity density: %{z:.1f}<extra></extra>",
        )
    )
    for shape in pitch_shapes():
        fig.add_shape(**shape)
    fig.update_layout(
        height=310,
        margin=dict(l=3, r=3, t=3, b=3),
        paper_bgcolor=PLOT_BG,
        plot_bgcolor="#0E1411",
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
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT, size=9),
        xaxis=dict(gridcolor=GRID, zeroline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False, title=y_title),
        showlegend=False,
    )
    return fig


# ============================================================
# Data Loading
# ============================================================

players = load_players()
transfers = load_transfers()
valuations = load_player_valuations()
wages = load_player_wages()
appearances_summary = load_player_appearances_summary()
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

current_pl = load_current_pl_roster()

if not current_pl.empty:
    current_pl["search_key"] = (
        current_pl["name"].map(norm) + " " + current_pl["web_name"].map(norm)
    )
    current_pl = current_pl.drop_duplicates(["name", "club"]).reset_index(drop=True)

if "player_search_query" not in st.session_state:
    st.session_state.player_search_query = "Erling Haaland"
if "player_search_results" not in st.session_state:
    st.session_state.player_search_results = [
        {"label": "Erling Haaland · Manchester City", "name": "Erling Haaland", "club": "Manchester City", "source": "local"}
    ]
if "selected_player_key" not in st.session_state:
    st.session_state.selected_player_key = "Erling Haaland|Manchester City|local"


# ============================================================
# Header + Search Bar
# ============================================================

styles.header(
    "Player Analytics & Performance ROI",
    "Market valuation trajectory, career transfer volume, wage history, and local performance efficiency.",
)

with st.form("player_search_form", clear_on_submit=False):
    search_col, button_col = st.columns([5.7, 1], gap="small")
    with search_col:
        query = st.text_input(
            "Search player",
            value=st.session_state.player_search_query,
            placeholder="Search player name (e.g. Haaland, Saka, Bruno Fernandes, Gyökeres)...",
        )
    with button_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Search", use_container_width=True)

if submitted:
    q = norm(query)
    result_rows = []

    if q and not current_pl.empty:
        current_matches = current_pl[
            current_pl["search_key"].str.contains(re.escape(q), regex=True, na=False)
        ].copy()

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
    st.warning("No matching player found. Try searching by surname or full name.")
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

# Fetch local player record
player_rows = searchable[searchable["name"].map(norm) == norm(selected_name)]
is_local_player = not player_rows.empty

if is_local_player:
    player = player_rows.iloc[0]
    player_id = player["player_id"]
else:
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

# Datasets
valuation = get_player_valuation_history(valuations, player_id) if is_local_player else pd.DataFrame()
transfers_player = get_player_transfer_history(transfers, player_id) if is_local_player else pd.DataFrame()
wage_rows = get_player_wage_history(wages, selected_name) if is_local_player else pd.DataFrame()
perf_summary = get_player_performance_history(appearances_summary, player_id) if is_local_player else {}

position = map_position(player)
position_label = role_name(position)
club = selected_club or safe(player.get("current_club_name"), "Club unavailable")
country = safe(player.get("country_of_citizenship"), "Country unavailable")
image_url = safe(player.get("image_url"), "")

current_value = pd.to_numeric(player.get("market_value_in_eur"), errors="coerce")
peak_value = pd.to_numeric(player.get("highest_market_value_in_eur"), errors="coerce")
dob = pd.to_datetime(player.get("date_of_birth"), errors="coerce")
age = int((pd.Timestamp.now() - dob).days / 365.25) if pd.notna(dob) else None

peak_analysis = player_peak_vs_current(current_value, peak_value)

latest_wage = wage_rows.iloc[-1] if wage_rows is not None and not wage_rows.empty else None
annual_wage = pd.to_numeric(latest_wage.get("annual_wage_gbp"), errors="coerce") if latest_wage is not None else np.nan

paid_fees = pd.to_numeric(transfers_player.get("transfer_fee"), errors="coerce") if not transfers_player.empty else pd.Series(dtype=float)
paid_fees = paid_fees[paid_fees > 0]
paid_count = len(paid_fees)
transfer_volume = paid_fees.sum() if paid_count else 0
largest_fee = paid_fees.max() if paid_count else np.nan

cost_efficiency = calculate_player_cost_per_performance(transfer_volume, annual_wage, perf_summary)


# ============================================================
# Hero Section
# ============================================================

hero_col, value_col = st.columns([3.5, 1.5], gap="small")

with hero_col:
    img = (
        f'<img src="{image_url}" style="width:105px;height:105px;object-fit:cover;'
        f'border-radius:10px;border:1px solid #1E2823;">'
        if image_url
        else ""
    )

    st.markdown(
        f"""
        <div style="
            border:1px solid #1E2823;
            border-radius:12px;
            background:linear-gradient(135deg,#121815,#0B0F0D);
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
                <div style="color:#8FA398;margin-top:8px;font-size:.9rem;">
                    {club} · {position_label} · {country}
                </div>
                <div style="display:flex;gap:8px;margin-top:12px;">
                    <span style="padding:4px 9px;border-radius:14px;background:#15241D;
                    border:1px solid #1E3B2C;color:#2FBF71;font-size:.72rem;font-weight:600;">
                        {age if age is not None else "—"} yrs
                    </span>
                    <span style="padding:4px 9px;border-radius:14px;background:#15241D;
                    border:1px solid #1E3B2C;color:#2FBF71;font-size:.72rem;font-weight:600;">
                        {position}
                    </span>
                    <span style="padding:4px 9px;border-radius:14px;background:#18261E;
                    border:1px solid #1E2823;color:#D7E4DE;font-size:.72rem;">
                        {peak_analysis['status']}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with value_col:
    if not is_local_player:
        st.caption("Found via current Premier League roster. Historical database records unavailable.")
    peak_delta_text = (
        "Career Peak"
        if peak_analysis["is_at_peak"]
        else f"{peak_analysis['pct_delta']:+.1f}% vs peak ({format_eur_m(peak_value)})"
    )
    styles.kpi_card(
        "Current market value",
        format_eur_m(current_value) if pd.notna(current_value) else "—",
        peak_delta_text,
        delta_positive=peak_analysis["is_at_peak"],
    )
    st.caption(f"Latest wage estimate: {money_gbp(annual_wage)}/yr")

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ============================================================
# Performance & Cost Efficiency (From local appearances.csv)
# ============================================================

styles.section_label("Local Performance & Cost-Per-Output Analysis")
st.caption("Aggregated match data from historical appearances dataset.")

if perf_summary:
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    with p1:
        styles.kpi_card("Appearances", f"{perf_summary['total_appearances']:,}", "tracked matches")
    with p2:
        styles.kpi_card("Goals", f"{perf_summary['total_goals']:,}", f"{perf_summary['goals_per_90']:.2f} per 90m")
    with p3:
        styles.kpi_card("Assists", f"{perf_summary['total_assists']:,}", f"{perf_summary['assists_per_90']:.2f} per 90m")
    with p4:
        styles.kpi_card("Minutes Played", f"{perf_summary['total_minutes']:,} mins")
    with p5:
        c_goal = cost_efficiency.get("cost_per_goal")
        styles.kpi_card("Transfer Fee / Goal", format_eur_m(c_goal) if pd.notna(c_goal) else "—", "fee per goal scored")
    with p6:
        c_min = cost_efficiency.get("cost_per_minute")
        styles.kpi_card("Transfer Fee / Minute", f"€{c_min:,.0f}/min" if pd.notna(c_min) and c_min > 0 else "—", "fee per minute on pitch")
else:
    st.caption("No local appearance records available for this player.")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# Player Accounting & Contract Amortisation Impact
# ============================================================

styles.section_label("Player Accounting & Annual Club P&L Burden")
st.caption("Annual financial impact on club income statement (Transfer Fee Amortisation + Annual Wage Expense).")

if pd.notna(largest_fee) and largest_fee > 0:
    ann_amort = largest_fee / 5.0
    ann_wage_eur = (annual_wage * 1.18) if pd.notna(annual_wage) else 0.0
    total_pl_impact = ann_amort + ann_wage_eur

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        styles.kpi_card("Acquisition Fee", format_eur_m(largest_fee), "recorded transfer fee")
    with f2:
        styles.kpi_card("Annual Amortisation", format_eur_m(ann_amort), "5-year straight-line depreciation")
    with f3:
        styles.kpi_card("Annual Wage Commitment", money_gbp(annual_wage) if pd.notna(annual_wage) else "—", "base salary estimate")
    with f4:
        styles.kpi_card("Annual Club P&L Hit", format_eur_m(total_pl_impact), "Amortisation + Wage Charge")
else:
    st.caption("No paid acquisition fee on record to compute contract amortisation.")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)



# ============================================================
# Valuation & Wage Trajectories
# ============================================================

styles.section_label("Player Economics & Valuation Trajectory")

value_col, wage_col = st.columns(2, gap="medium")

with value_col:
    with styles.panel():
        styles.section_label("Market Value Trajectory")
        st.caption("Recorded Transfermarkt valuation history across career milestones.")
        if not valuation.empty:
            vd = valuation.copy()
            vd["date"] = pd.to_datetime(vd["date"], errors="coerce")
            vd["value_m"] = pd.to_numeric(vd["market_value_in_eur"], errors="coerce") / 1_000_000
            vd = vd.dropna(subset=["date", "value_m"]).sort_values("date")
            if not vd.empty:
                fig = line_chart(
                    vd, "date", "value_m", GREEN, "€M", hover="%{x|%b %Y}<br>€%{y:.1f}M<extra></extra>"
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.caption("No market-value trajectory available for this player.")

with wage_col:
    with styles.panel():
        styles.section_label("Wage Trajectory")
        st.caption("Annual wage commitments recorded across Premier League seasons.")
        if wage_rows is not None and not wage_rows.empty and "annual_wage_gbp" in wage_rows.columns:
            wd = wage_rows.copy()
            wd["annual_m"] = pd.to_numeric(wd["annual_wage_gbp"], errors="coerce") / 1_000_000
            wd = wd.dropna(subset=["annual_m"]).sort_values("season")
            if not wd.empty:
                fig = line_chart(
                    wd, "season", "annual_m", AMBER, "£M / year", hover="%{x}<br>£%{y:.2f}M / year<extra></extra>"
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.caption("No wage trajectory available for this player.")

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)


# ============================================================
# Positional Tactical Model
# ============================================================

heat_col, transfer_col = st.columns(2, gap="medium")

with heat_col:
    with styles.panel():
        styles.section_label("Positional Heatmap Profile")
        st.caption("Tactical activity profile model for position and style.")

        if not heatmaps.empty:
            available_positions = sorted(heatmaps["position"].astype(str).unique().tolist())
            default_position = position if position in available_positions else available_positions[0]

            shown_position = st.selectbox(
                "Tactical position",
                available_positions,
                index=available_positions.index(default_position),
                format_func=lambda x: f"{role_name(x)} ({x})",
                key=f"heat_pos_{selected_name}",
            )

            role_data = heatmaps[heatmaps["position"].astype(str) == shown_position]
            styles_available = sorted(role_data["style"].astype(str).unique().tolist())

            chosen_style = st.selectbox(
                "Role variation",
                styles_available,
                key=f"heat_style_{selected_name}_{shown_position}",
            )

            selected_heat = role_data[role_data["style"].astype(str) == chosen_style]
            st.plotly_chart(heatmap_chart(selected_heat), width="stretch", config={"displayModeBar": False})
        else:
            st.caption("Heatmap dataset unavailable.")

with transfer_col:
    with styles.panel():
        styles.section_label("Career Transfer Ledger")
        st.caption("Complete transfer history recorded in Transfermarkt dataset.")

        if not transfers_player.empty:
            rows = transfers_player.copy()
            rows["Date"] = pd.to_datetime(rows["transfer_date"], errors="coerce").dt.strftime("%b %Y")
            rows["Fee"] = pd.to_numeric(rows["transfer_fee"], errors="coerce").apply(
                lambda x: format_eur_m(x) if pd.notna(x) and x > 0 else "Free / Undisclosed"
            )
            rows["Market Value"] = pd.to_numeric(rows["market_value_in_eur"], errors="coerce").apply(
                lambda x: format_eur_m(x) if pd.notna(x) and x > 0 else "—"
            )
            display = rows[["Date", "from_club_name", "to_club_name", "Fee", "Market Value"]].rename(
                columns={"from_club_name": "From Club", "to_club_name": "To Club"}
            )
            st.dataframe(display, hide_index=True, width="stretch", height=280)
        else:
            st.caption("No transfer history records found for this player.")

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

with st.expander("Methodology & Disclosures"):
    st.markdown(
        """
        - **Local Performance Metrics:** Aggregated directly from `appearances.csv` covering domestic and European matches.
        - **Cost-Per-Output:** Evaluates Total Acquisition Fees relative to total goals, assists, and minutes on pitch.
        - **Valuations & Wages:** Sourced from Transfermarkt historical valuations and Premier League wage dataset.
        """
    )

st.markdown(
    "<div style='height:1rem'></div><div style='text-align:center;color:#5C6E66;font-size:.75rem;'>"
    "Soccernomics · Football. Data. Economics."
    "</div>",
    unsafe_allow_html=True,
)
