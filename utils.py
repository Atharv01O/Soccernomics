"""
Soccernomics — shared data loading & cleaning utilities.
Keep all raw CSVs in data/raw/, cleaned outputs go to data/processed/.
"""
import pandas as pd
import numpy as np
import re
import os

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(_PROJECT_ROOT, "data/raw")
PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data/processed")


def load_clubs():
    df = pd.read_csv(f"{RAW_DIR}/clubs.csv")
    # net_transfer_record comes as a string like "+€5.90m" or "€-25.00m" — parse to float (millions EUR)
    def parse_net_transfer(val):
        if pd.isna(val):
            return np.nan
        s = str(val).replace("€", "").replace("m", "").replace(",", "").strip()
        s = s.replace("+", "")
        try:
            return float(s)
        except ValueError:
            return np.nan
    df["net_transfer_record_eur_m"] = df["net_transfer_record"].apply(parse_net_transfer)
    return df


def load_players():
    df = pd.read_csv(f"{RAW_DIR}/players.csv")
    if "date_of_birth" in df.columns:
        df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce")
    return df


def load_transfers():
    df = pd.read_csv(f"{RAW_DIR}/transfers.csv")
    if "transfer_date" in df.columns:
        df["transfer_date"] = pd.to_datetime(df["transfer_date"], errors="coerce")
    return df


def load_player_valuations():
    df = pd.read_csv(f"{RAW_DIR}/player_valuations.csv")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def profile(df, name="df"):
    """Quick shape/missingness/dtype summary for EDA."""
    print(f"=== {name} ===")
    print("shape:", df.shape)
    print("dtypes:\n", df.dtypes)
    miss = df.isnull().sum()
    miss = miss[miss > 0]
    if len(miss):
        print("missing:\n", miss)
    print()


# ---------------------------------------------------------------------------
# PL-scoped aggregate helpers used by the Streamlit app.
# Kept here (not in the pages) so every page queries the same logic.
# ---------------------------------------------------------------------------

def get_pl_club_ids(clubs):
    return set(clubs[clubs["domestic_competition_id"] == "GB1"]["club_id"])


def get_pl_transfers(transfers, pl_club_ids):
    return transfers[
        transfers["from_club_id"].isin(pl_club_ids) | transfers["to_club_id"].isin(pl_club_ids)
    ].copy()


def season_spending_trend(pl_transfers, pl_club_ids):
    """Total incoming (spending) and outgoing (revenue) fees per season, PL clubs only."""
    incoming = pl_transfers[pl_transfers["to_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()]
    outgoing = pl_transfers[pl_transfers["from_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()]
    spend = incoming.groupby("transfer_season")["transfer_fee"].sum().rename("spending")
    revenue = outgoing.groupby("transfer_season")["transfer_fee"].sum().rename("revenue")
    trend = pd.concat([spend, revenue], axis=1).fillna(0)
    return trend


def top_spending_clubs(pl_transfers, pl_club_ids, season=None, top_n=10):
    incoming = pl_transfers[pl_transfers["to_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()]
    if season:
        incoming = incoming[incoming["transfer_season"] == season]
    return (
        incoming.groupby("to_club_name")["transfer_fee"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )


def top_expensive_transfers(pl_transfers, pl_club_ids, top_n=5):
    incoming = pl_transfers[pl_transfers["to_club_id"].isin(pl_club_ids) & pl_transfers["transfer_fee"].notna()]
    return incoming.nlargest(top_n, "transfer_fee")[
        ["player_name", "transfer_date", "to_club_name", "from_club_name", "transfer_fee"]
    ]


def overpay_bargain_table(pl_transfers):
    priced = pl_transfers.dropna(subset=["transfer_fee", "market_value_in_eur"])
    priced = priced[priced["transfer_fee"] > 0].copy()
    priced["fee_vs_value_eur"] = priced["transfer_fee"] - priced["market_value_in_eur"]
    priced["overpay_pct"] = priced["fee_vs_value_eur"] / priced["market_value_in_eur"] * 100
    return priced


def trading_efficiency_by_club(transfers, pl_club_ids, min_trades=6):
    """Buy-then-sell pairs for PL clubs; returns ROI (profit per euro invested) per club."""
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


def player_spotlight(transfers, name="Erling Haaland"):
    rows = transfers[transfers["player_name"] == name].dropna(subset=["transfer_fee", "market_value_in_eur"])
    if rows.empty:
        return None
    row = rows.sort_values("transfer_date", ascending=False).iloc[0]
    return {
        "name": name,
        "to_club": row["to_club_name"],
        "transfer_date": row["transfer_date"],
        "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row["market_value_in_eur"],
    }


def completed_seasons(pl_transfers, latest_incomplete=None):
    """Season labels sorted chronologically, excluding an in-progress season (e.g. current one)."""
    seasons = sorted(pl_transfers["transfer_season"].dropna().unique())
    if latest_incomplete and latest_incomplete in seasons:
        seasons.remove(latest_incomplete)
    return seasons


def season_biggest_bargain(pl_transfers, pl_club_ids, season):
    """Biggest fee-vs-value bargain among incoming transfers in a given season (min €5m fee to avoid noise)."""
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        & (pl_transfers["transfer_season"] == season)
        & pl_transfers["transfer_fee"].notna() & (pl_transfers["transfer_fee"] >= 5_000_000)
        & pl_transfers["market_value_in_eur"].notna()
    ].copy()
    if incoming.empty:
        return None
    incoming["value_gap"] = incoming["market_value_in_eur"] - incoming["transfer_fee"]
    row = incoming.nlargest(1, "value_gap").iloc[0]
    return {
        "name": row["player_name"],
        "to_club": row["to_club_name"],
        "from_club": row["from_club_name"],
        "transfer_date": row["transfer_date"],
        "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row["market_value_in_eur"],
        "value_gap": row["value_gap"],
    }


def club_badge_style(club_name):
    """Deterministic initials + accent color for a club, avoiding real crest images (copyright)."""
    palette = ["#2FBF71", "#E8B75D", "#5B9BD5", "#D97757", "#9B7FD4", "#4FBFBF"]
    words = [w for w in club_name.replace("'", "").split() if w[0].isupper()]
    initials = "".join(w[0] for w in words[:2]) if words else club_name[:2].upper()
    color = palette[hash(club_name) % len(palette)]
    return initials.upper(), color