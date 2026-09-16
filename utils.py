"""
Soccernomics — shared data loading & cleaning utilities.

Raw CSVs:
    data/raw/

Optional processed outputs:
    data/processed/
"""

import os
import json
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import pandas as pd
import numpy as np
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

RAW_DIR = os.path.join(_PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data", "processed")


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_clubs():
    df = pd.read_csv(f"{RAW_DIR}/clubs.csv")

    if "net_transfer_record" in df.columns:

        def parse_net_transfer(val):
            if pd.isna(val):
                return np.nan

            s = (
                str(val)
                .replace("€", "")
                .replace("m", "")
                .replace("M", "")
                .replace(",", "")
                .strip()
            )

            s = s.replace("+", "")

            try:
                return float(s)
            except ValueError:
                return np.nan

        df["net_transfer_record_eur_m"] = (
            df["net_transfer_record"].apply(parse_net_transfer)
        )

    return df


def load_players():
    df = pd.read_csv(f"{RAW_DIR}/players.csv")

    if "date_of_birth" in df.columns:
        df["date_of_birth"] = pd.to_datetime(
            df["date_of_birth"],
            errors="coerce"
        )

    return df


def load_transfers():
    df = pd.read_csv(f"{RAW_DIR}/transfers.csv")

    if "transfer_date" in df.columns:
        df["transfer_date"] = pd.to_datetime(
            df["transfer_date"],
            errors="coerce"
        )

    for column in ["transfer_fee", "market_value_in_eur"]:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


def load_player_valuations():
    df = pd.read_csv(f"{RAW_DIR}/player_valuations.csv")

    if "date" in df.columns:
        # Source format is DD-MM-YYYY. Without dayfirst=True, pandas silently
        # swaps day/month for every row where both are <=12 (confirmed: ~37%
        # of rows, e.g. "09-12-2003" parsed as Sep 12 instead of Dec 9) —
        # this was corrupting every age-vs-valuation-date calculation.
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)

    if "market_value_in_eur" in df.columns:
        df["market_value_in_eur"] = pd.to_numeric(
            df["market_value_in_eur"], errors="coerce"
        )

    return df


@st.cache_data
def load_club_financials():
    return pd.read_csv(
        f"{RAW_DIR}/soccernomics_club_financials_deloitte_2023_24_2024_25.csv"
    )


# ---------------------------------------------------------------------------
# DATA PROFILE
# ---------------------------------------------------------------------------

def profile(df, name="df"):
    """Quick shape / missingness / dtype summary for EDA."""
    print(f"=== {name} ===")
    print("shape:", df.shape)
    print("dtypes:\n", df.dtypes)
    miss = df.isnull().sum()
    miss = miss[miss > 0]
    if len(miss):
        print("missing:\n", miss)
    print()


# ---------------------------------------------------------------------------
# PREMIER LEAGUE HELPERS
# ---------------------------------------------------------------------------

def get_pl_club_ids(clubs):
    return set(clubs[clubs["domestic_competition_id"] == "GB1"]["club_id"])


def get_pl_transfers(transfers, pl_club_ids):
    return transfers[
        transfers["from_club_id"].isin(pl_club_ids)
        | transfers["to_club_id"].isin(pl_club_ids)
    ].copy()


# ---------------------------------------------------------------------------
# SEASON ANALYSIS
# ---------------------------------------------------------------------------

def season_spending_trend(pl_transfers, pl_club_ids):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()
    ]
    outgoing = pl_transfers[
        pl_transfers["from_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()
    ]
    spend = incoming.groupby("transfer_season")["transfer_fee"].sum().rename("spending")
    income = outgoing.groupby("transfer_season")["transfer_fee"].sum().rename("revenue")
    trend = pd.concat([spend, income], axis=1).fillna(0)
    return trend


def completed_seasons(pl_transfers, latest_incomplete=None):
    seasons = sorted(pl_transfers["transfer_season"].dropna().unique())
    if latest_incomplete and latest_incomplete in seasons:
        seasons.remove(latest_incomplete)
    return seasons


# ---------------------------------------------------------------------------
# CLUB SPENDING
# ---------------------------------------------------------------------------

def top_spending_clubs(pl_transfers, pl_club_ids, season=None, top_n=10):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()
    ]
    if season:
        incoming = incoming[incoming["transfer_season"] == season]
    return (
        incoming.groupby("to_club_name")["transfer_fee"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )


def top_expensive_transfers(pl_transfers, pl_club_ids, season=None, top_n=5):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()
    ].copy()
    if season:
        incoming = incoming[incoming["transfer_season"] == season]
    return incoming.nlargest(top_n, "transfer_fee")[
        ["player_name", "transfer_date", "to_club_name", "from_club_name", "transfer_fee"]
    ]


# ---------------------------------------------------------------------------
# FEE VS MARKET VALUE
# ---------------------------------------------------------------------------

def overpay_bargain_table(pl_transfers):
    priced = pl_transfers.dropna(subset=["transfer_fee", "market_value_in_eur"]).copy()
    priced = priced[priced["transfer_fee"] > 0]
    priced = priced[priced["market_value_in_eur"] > 0]
    priced["fee_vs_value_eur"] = priced["transfer_fee"] - priced["market_value_in_eur"]
    priced["overpay_pct"] = priced["fee_vs_value_eur"] / priced["market_value_in_eur"] * 100
    priced["value_discount_pct"] = (
        (priced["market_value_in_eur"] - priced["transfer_fee"]) / priced["market_value_in_eur"] * 100
    )
    return priced


# ---------------------------------------------------------------------------
# TRADING EFFICIENCY
# ---------------------------------------------------------------------------

def trading_efficiency_by_club(transfers, pl_club_ids, min_trades=6):
    t = transfers.sort_values(["player_id", "transfer_date"]).copy()
    t["next_from_club_id"] = t.groupby("player_id")["from_club_id"].shift(-1)
    t["next_transfer_fee"] = t.groupby("player_id")["transfer_fee"].shift(-1)

    buy_sell = t[
        t["to_club_id"].isin(pl_club_ids)
        & (t["next_from_club_id"] == t["to_club_id"])
        & t["transfer_fee"].notna() & (t["transfer_fee"] > 0)
        & t["next_transfer_fee"].notna() & (t["next_transfer_fee"] > 0)
    ].copy()

    grouped = buy_sell.groupby("to_club_name").agg(
        n_trades=("transfer_fee", "count"),
        total_invested=("transfer_fee", "sum"),
        total_recouped=("next_transfer_fee", "sum"),
    )
    grouped["profit_per_euro_invested"] = (
        grouped["total_recouped"] - grouped["total_invested"]
    ) / grouped["total_invested"]

    return grouped[grouped["n_trades"] >= min_trades].sort_values(
        "profit_per_euro_invested", ascending=False
    )


# ---------------------------------------------------------------------------
# PLAYER IMAGE
# ---------------------------------------------------------------------------

def get_player_image_column(players):
    possible_columns = ["image_url", "img_url", "player_image_url", "image", "img"]
    for column in possible_columns:
        if column in players.columns:
            return column
    return None


def get_player_image(players, player_id):
    image_column = get_player_image_column(players)
    if image_column is None:
        return None
    rows = players[players["player_id"] == player_id]
    if rows.empty:
        return None
    image_url = rows.iloc[0][image_column]
    if pd.isna(image_url):
        return None
    return str(image_url)


# ---------------------------------------------------------------------------
# PLAYER SPOTLIGHT
# ---------------------------------------------------------------------------

def player_spotlight(transfers, players=None, season=None):
    rows = transfers.copy()
    if season:
        rows = rows[rows["transfer_season"] == season]
    rows = rows[rows["transfer_fee"].notna() & (rows["transfer_fee"] > 0)]
    if rows.empty:
        return None
    row = rows.loc[rows["transfer_fee"].idxmax()]
    image_url = None
    if players is not None:
        image_url = get_player_image(players, row["player_id"])
    return {
        "name": row["player_name"],
        "player_id": row["player_id"],
        "from_club": row["from_club_name"],
        "to_club": row["to_club_name"],
        "transfer_date": row["transfer_date"],
        "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row.get("market_value_in_eur", None),
        "image_url": image_url,
    }


# ---------------------------------------------------------------------------
# SEASON BARGAIN
# ---------------------------------------------------------------------------

def season_biggest_bargain(pl_transfers, pl_club_ids, season):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        & (pl_transfers["transfer_season"] == season)
        & pl_transfers["transfer_fee"].notna()
        & (pl_transfers["transfer_fee"] >= 5_000_000)
        & pl_transfers["market_value_in_eur"].notna()
        & (pl_transfers["market_value_in_eur"] > 0)
    ].copy()
    if incoming.empty:
        return None
    incoming["value_gap"] = incoming["market_value_in_eur"] - incoming["transfer_fee"]
    incoming["discount_pct"] = incoming["value_gap"] / incoming["market_value_in_eur"] * 100
    row = incoming.nlargest(1, "discount_pct").iloc[0]
    return {
        "name": row["player_name"], "player_id": row["player_id"],
        "to_club": row["to_club_name"], "from_club": row["from_club_name"],
        "transfer_date": row["transfer_date"], "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row["market_value_in_eur"],
        "value_gap": row["value_gap"], "discount_pct": row["discount_pct"],
    }


# ---------------------------------------------------------------------------
# STEAL DEAL
# ---------------------------------------------------------------------------

def biggest_steal_deal(pl_transfers, pl_club_ids, season=None, min_fee=5_000_000):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        & pl_transfers["transfer_fee"].notna()
        & (pl_transfers["transfer_fee"] >= min_fee)
        & pl_transfers["market_value_in_eur"].notna()
        & (pl_transfers["market_value_in_eur"] > 0)
    ].copy()
    if season:
        incoming = incoming[incoming["transfer_season"] == season]
    if incoming.empty:
        return None
    incoming["value_gap"] = incoming["market_value_in_eur"] - incoming["transfer_fee"]
    incoming["discount_pct"] = incoming["value_gap"] / incoming["market_value_in_eur"] * 100
    incoming = incoming[incoming["discount_pct"] > 0]
    if incoming.empty:
        return None
    row = incoming.loc[incoming["discount_pct"].idxmax()]
    return {
        "name": row["player_name"], "player_id": row["player_id"],
        "from_club": row["from_club_name"], "to_club": row["to_club_name"],
        "transfer_date": row["transfer_date"], "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row["market_value_in_eur"],
        "value_gap": row["value_gap"], "discount_pct": row["discount_pct"],
    }


# ---------------------------------------------------------------------------
# BOOM PLAYER
# ---------------------------------------------------------------------------

def boom_player(pl_transfers, valuations, pl_club_ids, season=None, min_fee=5_000_000, min_growth_pct=50):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        & pl_transfers["transfer_fee"].notna()
        & (pl_transfers["transfer_fee"] >= min_fee)
        & pl_transfers["transfer_date"].notna()
    ].copy()
    if season:
        incoming = incoming[incoming["transfer_season"] == season]
    if incoming.empty:
        return None

    valuations = valuations.copy()
    valuations = valuations[
        valuations["player_id"].notna() & valuations["date"].notna() & valuations["market_value_in_eur"].notna()
    ].copy()
    valuations["player_id"] = valuations["player_id"].astype(int)
    incoming["player_id"] = incoming["player_id"].astype(int)

    results = []
    for _, transfer in incoming.iterrows():
        player_vals = valuations[valuations["player_id"] == transfer["player_id"]].sort_values("date")
        if player_vals.empty:
            continue
        transfer_date = transfer["transfer_date"]
        before = player_vals[player_vals["date"] <= transfer_date]
        if before.empty:
            continue
        starting_row = before.iloc[-1]
        starting_value = starting_row["market_value_in_eur"]
        if pd.isna(starting_value) or starting_value <= 0:
            continue
        after = player_vals[player_vals["date"] > transfer_date]
        if after.empty:
            continue
        peak_idx = after["market_value_in_eur"].idxmax()
        peak_row = after.loc[peak_idx]
        peak_value = peak_row["market_value_in_eur"]
        growth = peak_value - starting_value
        growth_pct = growth / starting_value * 100
        if growth_pct < min_growth_pct:
            continue
        results.append({
            "name": transfer["player_name"], "player_id": transfer["player_id"],
            "from_club": transfer["from_club_name"], "to_club": transfer["to_club_name"],
            "transfer_date": transfer_date, "transfer_fee": transfer["transfer_fee"],
            "starting_value": starting_value, "peak_value": peak_value,
            "peak_date": peak_row["date"], "value_growth": growth, "growth_pct": growth_pct,
        })
    if not results:
        return None
    result_df = pd.DataFrame(results)
    row = result_df.loc[result_df["value_growth"].idxmax()]
    return row.to_dict()


# ---------------------------------------------------------------------------
# CLUB TRANSFER PROFILE
# ---------------------------------------------------------------------------

def club_transfer_profile(pl_transfers, club_name, season=None):
    transfers = pl_transfers.copy()
    if season:
        transfers = transfers[transfers["transfer_season"] == season]
    incoming = transfers[
        (transfers["to_club_name"] == club_name) & transfers["transfer_fee"].notna() & (transfers["transfer_fee"] > 0)
    ]
    outgoing = transfers[
        (transfers["from_club_name"] == club_name) & transfers["transfer_fee"].notna() & (transfers["transfer_fee"] > 0)
    ]
    spending = incoming["transfer_fee"].sum()
    income = outgoing["transfer_fee"].sum()
    return {
        "club": club_name, "incoming": incoming, "outgoing": outgoing,
        "spending": spending, "income": income, "net_spend": spending - income,
        "paid_buys": len(incoming), "paid_sales": len(outgoing),
        "average_buy": incoming["transfer_fee"].mean() if not incoming.empty else 0,
        "average_sale": outgoing["transfer_fee"].mean() if not outgoing.empty else 0,
    }


# ---------------------------------------------------------------------------
# CLUB BADGE
# ---------------------------------------------------------------------------

def club_badge_style(club_name):
    palette = ["#2FBF71", "#E8B75D", "#5B9BD5", "#D97757", "#9B7FD4", "#4FBFBF"]
    words = [w for w in club_name.replace("'", "").split() if w]
    initials = "".join(w[0] for w in words[:2]) if words else club_name[:2]
    color = palette[hash(club_name) % len(palette)]
    return initials.upper(), color


# ---------------------------------------------------------------------------
# FORMATTING
# ---------------------------------------------------------------------------

def format_eur_m(value):
    if value is None or pd.isna(value):
        return "€0"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"€{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"€{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"€{value / 1_000:.1f}K"
    return f"€{value:,.0f}"



# ---------------------------------------------------------------------------
# PLAYER PERFORMANCE / WAGES / EVENT DATA
# ---------------------------------------------------------------------------

def _first_existing_csv(filenames):
    for filename in filenames:
        path = os.path.join(RAW_DIR, filename)
        if os.path.exists(path):
            return path
    return None


@st.cache_data(ttl=3600)
def load_player_wages():
    """Load the cleaned PL wage dataset, preferring numeric columns."""
    path = _first_existing_csv([
        "premier_league_wages_cleaned.csv",
        "premier_league_wages.csv",
    ])
    if path is None:
        return pd.DataFrame()

    df = pd.read_csv(path)
    rename = {
        "Player": "player_name",
        "Name": "player_name",
        "Squad": "club",
        "Season": "season",
        "Weekly Wages (£)": "weekly_wage_gbp",
        "Annual Wages (£)": "annual_wage_gbp",
        "Weekly Wages": "weekly_wage_gbp",
        "Annual Wages": "annual_wage_gbp",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    for col in ["weekly_wage_gbp", "annual_wage_gbp"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
                errors="coerce",
            )

    if "season" in df.columns:
        df["season"] = df["season"].astype(str)
    if "player_name" in df.columns:
        df["name_key"] = df["player_name"].astype(str).str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()

    return df


@st.cache_data(ttl=3600)
def load_player_stats():
    """Load the supplied playerstats.csv without inventing a player-name mapping.

    The supplied file is kept as a local fallback for FPL-style advanced metrics.
    Player identity, goals, assists and minutes are now sourced from Sportmonks
    when a Sportmonks token is configured.
    """
    path = _first_existing_csv(["playerstats.csv"])
    if path is None:
        return pd.DataFrame()

    df = pd.read_csv(path)
    numeric_columns = [
        "id", "total_points", "event_points", "points_per_game", "bonus", "bps",
        "form", "value_form", "value_season", "transfers_in", "transfers_out",
        "expected_goals", "expected_assists", "expected_goal_involvements",
        "expected_goals_conceded", "expected_goals_per_90",
        "expected_assists_per_90", "expected_goal_involvements_per_90",
        "expected_goals_conceded_per_90", "influence", "creativity",
        "threat", "ict_index", "now_cost",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_player_shots():
    """Load supplied shot-event data with numeric pitch coordinates."""
    path = _first_existing_csv(["player_shots.csv", "shots.csv", "sample_shots.csv", "premier_league_shots.csv"])
    if path is None:
        return pd.DataFrame()

    df = pd.read_csv(path)
    for col in ["x", "y", "xg", "minute"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "player" in df.columns:
        df["player"] = df["player"].astype(str)
    return df


# ---------------------------------------------------------------------------
# Sportmonks Football API
# ---------------------------------------------------------------------------

SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
SPORTMONKS_PL_LEAGUE_ID = 8


def get_sportmonks_token():
    """Read the Sportmonks token from Streamlit secrets or an environment variable."""
    try:
        token = st.secrets.get("SPORTMONKS_API_TOKEN")
        if token:
            return str(token).strip()
    except Exception:
        pass

    token = os.getenv("SPORTMONKS_API_TOKEN", "").strip()
    return token or None


def sportmonks_is_configured():
    return bool(get_sportmonks_token())


@st.cache_data(ttl=3600, show_spinner=False)
def _sportmonks_get(path, params=None):
    """Small cached GET wrapper for Sportmonks API 3.0."""
    token = get_sportmonks_token()
    if not token:
        return None

    params = dict(params or {})
    params["api_token"] = token
    query = "&".join(f"{quote(str(k))}={quote(str(v))}" for k, v in params.items())
    url = f"{SPORTMONKS_BASE_URL}/{path.lstrip('/')}?{query}"

    try:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "Soccernomics/1.0",
            },
        )
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None


def _sm_data(payload):
    if isinstance(payload, dict):
        return payload.get("data")
    return None


def _sm_normalise_name(value):
    if pd.isna(value):
        return ""
    value = str(value).lower().strip()
    value = "".join(ch for ch in value if ch.isalnum() or ch == " ")
    return " ".join(value.split())


@st.cache_data(ttl=86400, show_spinner=False)
def sportmonks_current_pl_season():
    """Return the current Premier League season id/name from Sportmonks."""
    payload = _sportmonks_get(
        f"leagues/{SPORTMONKS_PL_LEAGUE_ID}",
        {"include": "currentSeason"},
    )
    data = _sm_data(payload) or {}
    season = data.get("currentseason") or data.get("currentSeason") or {}
    if not season:
        return None
    return {
        "id": season.get("id"),
        "name": season.get("name"),
        "starting_at": season.get("starting_at"),
        "ending_at": season.get("ending_at"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def _sportmonks_find_player(player_name):
    """Find the closest Sportmonks player record by name."""
    query = quote(str(player_name).strip())
    payload = _sportmonks_get(f"players/search/{query}", {"per_page": 10})
    rows = _sm_data(payload)
    if not isinstance(rows, list) or not rows:
        return None

    target = _sm_normalise_name(player_name)

    # Prefer exact full/display/common name matches.
    exact = []
    for row in rows:
        names = [
            row.get("name"),
            row.get("display_name"),
            row.get("common_name"),
            f"{row.get('firstname', '')} {row.get('lastname', '')}",
        ]
        if any(_sm_normalise_name(n) == target for n in names if n):
            exact.append(row)

    if exact:
        return exact[0]

    # Conservative fallback: only accept containment when the names are close.
    for row in rows:
        candidate = _sm_normalise_name(row.get("name") or row.get("display_name") or "")
        if candidate and (candidate in target or target in candidate):
            return row

    return None


def _sportmonks_detail_total(detail):
    """Extract the season total from a Sportmonks statistic detail."""
    value = detail.get("value")
    if isinstance(value, dict):
        for key in ("total", "value", "count", "average"):
            if key in value and value[key] is not None:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    pass
    elif value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return np.nan


def _sportmonks_stats_dict(player_data):
    """Flatten Sportmonks statistics.details into {stat_code: total}."""
    output = {}
    for stat in player_data.get("statistics", []) or []:
        for detail in stat.get("details", []) or []:
            stat_type = detail.get("type") or {}
            code = stat_type.get("code") or stat_type.get("developer_name")
            name = stat_type.get("name")
            key = str(code or name or "").lower().strip()
            if not key:
                continue
            value = _sportmonks_detail_total(detail)
            if pd.notna(value):
                output[key] = value
    return output


def _first_stat(stats, *keys):
    for key in keys:
        if key in stats and pd.notna(stats[key]):
            return stats[key]
    return np.nan


@st.cache_data(ttl=1800, show_spinner=False)
def get_sportmonks_player_performance(player_name):
    """Return current PL season player performance from Sportmonks.

    Goals, assists, minutes and standard event stats come from Sportmonks.
    xG is included when the account has the Sportmonks xG add-on. xA is only
    shown if Sportmonks supplies it; it is never guessed from FPL data.
    """
    if not sportmonks_is_configured():
        return None

    season = sportmonks_current_pl_season()
    if not season or not season.get("id"):
        return None

    player = _sportmonks_find_player(player_name)
    if not player or not player.get("id"):
        return None

    filters = f"playerStatisticSeasons:{season['id']}"
    payload = _sportmonks_get(
        f"players/{player['id']}",
        {
            "include": "statistics.details.type",
            "filters": filters,
        },
    )
    data = _sm_data(payload)
    if not isinstance(data, dict):
        return None

    stats = _sportmonks_stats_dict(data)

    minutes = _first_stat(stats, "minutes-played", "total-minutes-played")
    goals = _first_stat(stats, "goals")
    assists = _first_stat(stats, "assists")
    shots = _first_stat(stats, "shots-total")
    shots_on_target = _first_stat(stats, "shots-on-target")
    passes = _first_stat(stats, "passes")
    accurate_passes = _first_stat(stats, "accurate-passes", "successful-passes")
    key_passes = _first_stat(stats, "key-passes")
    tackles = _first_stat(stats, "tackles")
    interceptions = _first_stat(stats, "interceptions")
    duels_won = _first_stat(stats, "duels-won")
    dribbles = _first_stat(stats, "successful-dribbles")
    touches = _first_stat(stats, "touches")
    rating = _first_stat(stats, "rating")
    xg = _first_stat(
        stats,
        "expected-goals",
        "xg",
        "expected_goals",
        "expected-goals-total",
    )
    xa = _first_stat(
        stats,
        "expected-assists",
        "xa",
        "expected_assists",
    )

    xg90 = (xg / minutes * 90) if pd.notna(xg) and pd.notna(minutes) and minutes > 0 else np.nan
    xa90 = (xa / minutes * 90) if pd.notna(xa) and pd.notna(minutes) and minutes > 0 else np.nan

    # Sportmonks may expose no xG in the base plan. Keep it missing rather than
    # replacing it with a different live source.
    return {
        "player_name": data.get("display_name") or data.get("name") or player_name,
        "sportmonks_player_id": data.get("id"),
        "team_id": (data.get("statistics") or [{}])[0].get("team_id"),
        "season_id": season.get("id"),
        "season_name": season.get("name"),
        "minutes": minutes,
        "goals_scored": goals,
        "assists": assists,
        "shots": shots,
        "shots_on_target": shots_on_target,
        "passes": passes,
        "accurate_passes": accurate_passes,
        "key_passes": key_passes,
        "tackles": tackles,
        "interceptions": interceptions,
        "duels_won": duels_won,
        "successful_dribbles": dribbles,
        "touches": touches,
        "rating": rating,
        "expected_goals": xg,
        "expected_assists": xa,
        "expected_goals_per_90": xg90,
        "expected_assists_per_90": xa90,
        "expected_goal_involvements_per_90": (
            ((xg + xa) / minutes * 90)
            if pd.notna(xg) and pd.notna(xa) and pd.notna(minutes) and minutes > 0
            else np.nan
        ),
        "source": "Sportmonks",
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_sportmonks_player_shot_events(player_name):
    """Return Sportmonks shot events for the selected player's current PL team.

    Sportmonks events provide the player/result/minute context. They do not
    provide per-shot x/y coordinates, so this function intentionally does not
    fabricate coordinates. The existing supplied coordinate file remains the
    source for the visual shot map when it contains records.
    """
    if not sportmonks_is_configured():
        return pd.DataFrame()

    perf = get_sportmonks_player_performance(player_name)
    if not perf or not perf.get("sportmonks_player_id") or not perf.get("team_id") or not perf.get("season_id"):
        return pd.DataFrame()

    team_id = perf["team_id"]
    season_id = perf["season_id"]

    payload = _sportmonks_get(
        "fixtures",
        {
            "filters": f"fixtureLeagues:{SPORTMONKS_PL_LEAGUE_ID};fixtureSeasons:{season_id}",
            "include": "events.player;participants",
            "per_page": 50,
            "order": "desc",
        },
    )
    rows = _sm_data(payload)
    if not isinstance(rows, list):
        return pd.DataFrame()

    target_id = int(perf["sportmonks_player_id"])
    events = []
    for fixture in rows:
        participants = fixture.get("participants") or []
        participant_ids = {p.get("id") for p in participants if p.get("id") is not None}
        if team_id not in participant_ids:
            continue

        for event in fixture.get("events") or []:
            player = event.get("player") or {}
            player_id = event.get("player_id") or player.get("id")
            event_type = event.get("type") or {}
            code = str(event_type.get("code") or event_type.get("name") or "").lower()

            if player_id != target_id:
                continue
            if not any(token in code for token in ("shot", "goal")):
                continue

            events.append({
                "fixture_id": fixture.get("id"),
                "date": fixture.get("starting_at"),
                "minute": event.get("minute"),
                "result": event.get("result") or event_type.get("name") or "Shot",
                "event_type": event_type.get("name") or code,
                "player": player.get("display_name") or player.get("name") or player_name,
                "has_coordinates": False,
            })

    return pd.DataFrame(events)


def get_player_wage_history(wages, player_name):
    if wages is None or wages.empty or "name_key" not in wages.columns:
        return pd.DataFrame()
    key = str(player_name).lower().strip()
    key = "".join(ch for ch in key if ch.isalnum() or ch == " ")
    key = " ".join(key.split())
    return wages[wages["name_key"] == key].sort_values("season").copy()


def get_player_performance(player_stats, player_name):
    if player_stats is None or player_stats.empty or "player_name" not in player_stats.columns:
        return None
    target = str(player_name).strip().lower()
    rows = player_stats[player_stats["player_name"].astype(str).str.lower() == target].copy()
    if rows.empty:
        # Second pass for names such as full name vs web name.
        rows = player_stats[player_stats["player_name"].astype(str).str.lower().str.contains(target, regex=False)].copy()
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def get_player_shots(shots, player_name):
    """Match shot events to the selected player, including common-name records."""
    if shots is None or shots.empty or "player" not in shots.columns:
        return pd.DataFrame()

    def norm(value):
        value = str(value).strip().lower()
        value = "".join(ch for ch in value if ch.isalnum() or ch == " ")
        return " ".join(value.split())

    target_key = norm(player_name)
    names = shots["player"].map(norm)
    rows = shots[names == target_key].copy()

    # The event sample can use a common/surname name such as "Haaland"
    # while players.csv uses the full name "Erling Haaland".
    if rows.empty and target_key:
        surname = target_key.split()[-1]
        surname_mask = names.map(lambda x: bool(x) and x.split()[-1] == surname)
        surname_rows = shots[surname_mask].copy()
        unique_names = names[surname_mask].dropna().unique()
        if len(unique_names) == 1:
            rows = surname_rows

    return rows.copy()


def player_wage_summary(wage_history):
    if wage_history is None or wage_history.empty:
        return {"current": None, "previous": None, "change_pct": None, "highest": None, "lowest": None}
    rows = wage_history.dropna(subset=["annual_wage_gbp"]).sort_values("season")
    if rows.empty:
        return {"current": None, "previous": None, "change_pct": None, "highest": None, "lowest": None}
    current = rows.iloc[-1]["annual_wage_gbp"]
    previous = rows.iloc[-2]["annual_wage_gbp"] if len(rows) > 1 else np.nan
    change = ((current - previous) / previous * 100) if pd.notna(previous) and previous else None
    return {
        "current": current,
        "previous": previous,
        "change_pct": change,
        "highest": rows["annual_wage_gbp"].max(),
        "lowest": rows["annual_wage_gbp"].min(),
    }


def player_shot_summary(shot_history):
    if shot_history is None or shot_history.empty:
        return {"shots": 0, "goals": 0, "xg": 0.0, "conversion": None}
    goals = int(shot_history["result"].astype(str).str.lower().eq("goal").sum()) if "result" in shot_history.columns else 0
    xg = pd.to_numeric(shot_history.get("xg"), errors="coerce").sum() if "xg" in shot_history.columns else 0.0
    shots = len(shot_history)
    return {
        "shots": shots,
        "goals": goals,
        "xg": float(xg),
        "conversion": (goals / shots * 100) if shots else None,
    }

# ---------------------------------------------------------------------------
# PLAYER PAGE
# ---------------------------------------------------------------------------

def get_searchable_players(players, pl_transfers=None):
    """Return the full player dataset for the Player Analytics search.

    The player selector should search ``players.csv`` itself rather than
    restricting the options to current Premier League players or players
    found in Premier League transfers. This allows players such as Messi,
    Mbappe, Lewandowski, Bellingham and Pedri to be selected when they exist
    in players.csv, even if they have no Premier League transfer history.

    ``pl_transfers`` is kept as an optional argument for backwards
    compatibility with existing page code.
    """
    if players is None or players.empty:
        return pd.DataFrame()

    return players.copy()


def get_player_valuation_history(valuations, player_id):
    rows = valuations[valuations["player_id"] == player_id].copy()
    return rows.sort_values("date")


def get_player_transfer_history(transfers, player_id):
    rows = transfers[transfers["player_id"] == player_id].copy()
    return rows.sort_values("transfer_date")


def player_career_financial_summary(transfers, player_id):
    """Aggregate financial facts across a player's own transfer history.
    Note: for a single player there's no 'bought vs sold' split the way
    there is for a club — every row is one move with one fee."""
    rows = get_player_transfer_history(transfers, player_id)
    paid = rows[rows["transfer_fee"].notna() & (rows["transfer_fee"] > 0)].copy()

    summary = {
        "n_moves": len(rows),
        "n_paid_moves": len(paid),
        "total_fee_volume": paid["transfer_fee"].sum() if not paid.empty else 0,
        "highest_fee": None,
        "first_fee": None,
        "latest_fee": None,
        "avg_discount_pct": None,
    }

    if not paid.empty:
        top = paid.nlargest(1, "transfer_fee").iloc[0]
        summary["highest_fee"] = {
            "fee": top["transfer_fee"], "date": top["transfer_date"],
            "from_club": top["from_club_name"], "to_club": top["to_club_name"],
        }
        summary["first_fee"] = paid.iloc[0]["transfer_fee"]
        summary["latest_fee"] = paid.iloc[-1]["transfer_fee"]

    priced = paid.dropna(subset=["market_value_in_eur"])
    priced = priced[priced["market_value_in_eur"] > 0]
    if not priced.empty:
        discount_pct = (
            (priced["market_value_in_eur"] - priced["transfer_fee"]) / priced["market_value_in_eur"] * 100
        )
        summary["avg_discount_pct"] = discount_pct.mean()

    return summary


def position_age_value_curve(valuations, players):
    """Mean market value by age, split by position — the same curve used in
    the EDA notebook, formalized here so the player page can overlay a
    player's own trajectory against their position's typical curve."""
    merged = valuations.merge(
        players[["player_id", "date_of_birth", "position"]], on="player_id", how="inner"
    )
    merged["age_at_valuation"] = (merged["date"] - merged["date_of_birth"]).dt.days / 365.25
    merged = merged.dropna(subset=["age_at_valuation", "position"])
    merged["age_int"] = merged["age_at_valuation"].round().astype(int)
    merged = merged[(merged["age_int"] >= 16) & (merged["age_int"] <= 40)]
    return merged.groupby(["position", "age_int"])["market_value_in_eur"].mean().unstack(level=0)


# ---------------------------------------------------------------------------
# POSITION VALUE HEATMAP (pitch diagram)
# ---------------------------------------------------------------------------

# Approximate pitch coordinates (0-100 x, 0-100 y, attacking goal at y=100).
# Two-dot positions (centre-back, etc.) are offset left/right for a realistic look.
PITCH_POSITIONS = {
    "Goalkeeper": [(50, 6)],
    "Right-Back": [(82, 25)],
    "Centre-Back": [(38, 18), (62, 18)],
    "Left-Back": [(18, 25)],
    "Defensive Midfield": [(50, 40)],
    "Right Midfield": [(82, 52)],
    "Central Midfield": [(38, 55), (62, 55)],
    "Left Midfield": [(18, 52)],
    "Attacking Midfield": [(50, 70)],
    "Right Winger": [(85, 80)],
    "Second Striker": [(50, 82)],
    "Left Winger": [(15, 80)],
    "Centre-Forward": [(50, 92)],
}


def position_value_by_subposition(players_df):
    """Average current market value per sub-position, for the pitch heatmap."""
    rows = players_df.dropna(subset=["sub_position", "market_value_in_eur"])
    rows = rows[rows["market_value_in_eur"] > 0]
    return rows.groupby("sub_position")["market_value_in_eur"].agg(["mean", "count"])


# ---------------------------------------------------------------------------
# VALUE TREND (Rising / Peaked / Declining) — data-driven, not a scouting rating
# ---------------------------------------------------------------------------

def player_value_trend(val_history, min_points=3, lookback=4):
    """Classifies recent trajectory from the last `lookback` valuations using
    a simple linear slope. This is NOT a subjective potential rating — it's a
    description of recent recorded value movement, nothing more."""
    vh = val_history.dropna(subset=["date", "market_value_in_eur"]).sort_values("date")
    if len(vh) < min_points:
        return {"trend": "Insufficient data", "slope_pct_per_year": None, "n_points": len(vh)}

    recent = vh.tail(lookback).copy()
    recent["days"] = (recent["date"] - recent["date"].iloc[0]).dt.days
    if recent["days"].iloc[-1] == 0:
        return {"trend": "Insufficient data", "slope_pct_per_year": None, "n_points": len(vh)}

    x = recent["days"].values
    y = recent["market_value_in_eur"].values
    slope = np.polyfit(x, y, 1)[0]  # eur per day
    avg_value = y.mean()
    slope_pct_per_year = (slope * 365 / avg_value * 100) if avg_value else 0

    if slope_pct_per_year > 15:
        trend = "Rising"
    elif slope_pct_per_year < -15:
        trend = "Declining"
    else:
        trend = "Stable"

    return {"trend": trend, "slope_pct_per_year": slope_pct_per_year, "n_points": len(vh)}


# ---------------------------------------------------------------------------
# CONTRACT RISK
# ---------------------------------------------------------------------------

def contract_risk_players(players_df, pl_club_ids, months_ahead=12, min_value=5_000_000):
    """PL players with high value and a contract expiring soon — clubs at
    risk of losing recorded value for free (or a reduced fee) if not renewed
    or sold before the deadline."""
    rows = players_df[players_df["current_club_domestic_competition_id"] == "GB1"].copy()
    rows["contract_expiration_date"] = pd.to_datetime(rows["contract_expiration_date"], errors="coerce")

    cutoff = pd.Timestamp.now() + pd.DateOffset(months=months_ahead)
    rows = rows[
        rows["contract_expiration_date"].notna()
        & (rows["contract_expiration_date"] <= cutoff)
        & (rows["contract_expiration_date"] >= pd.Timestamp.now() - pd.DateOffset(months=1))
        & (rows["market_value_in_eur"] >= min_value)
    ].copy()

    return rows.sort_values("market_value_in_eur", ascending=False)[
        ["name", "current_club_name", "position", "contract_expiration_date", "market_value_in_eur"]
    ]


# ---------------------------------------------------------------------------
# AGENT LEADERBOARD
# ---------------------------------------------------------------------------

def agent_leaderboard(players_df, top_n=10, min_players=3):
    rows = players_df.dropna(subset=["agent_name", "market_value_in_eur"])
    rows = rows[rows["market_value_in_eur"] > 0]
    grouped = rows.groupby("agent_name").agg(
        total_value=("market_value_in_eur", "sum"),
        n_players=("player_id", "count"),
    )
    grouped = grouped[grouped["n_players"] >= min_players]
    return grouped.sort_values("total_value", ascending=False).head(top_n)