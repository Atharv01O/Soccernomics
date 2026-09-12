"""
Soccernomics — shared data loading & cleaning utilities.

Raw CSVs:
    data/raw/

Optional processed outputs:
    data/processed/
"""

import os
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
    df = pd.read_csv(
        f"{RAW_DIR}/player_valuations.csv"
    )

    # whatever code you already have here...

    return df

@st.cache_data
def load_club_financials():
    return pd.read_csv(
        f"{RAW_DIR}/soccernomics_club_financials_deloitte_2023_24_2024_25.csv"
    
    )
    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

    if "market_value_in_eur" in df.columns:
        df["market_value_in_eur"] = pd.to_numeric(
            df["market_value_in_eur"],
            errors="coerce"
        )

    return df


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
    return set(
        clubs[
            clubs["domestic_competition_id"] == "GB1"
        ]["club_id"]
    )


def get_pl_transfers(transfers, pl_club_ids):
    return transfers[
        transfers["from_club_id"].isin(pl_club_ids)
        |
        transfers["to_club_id"].isin(pl_club_ids)
    ].copy()


# ---------------------------------------------------------------------------
# SEASON ANALYSIS
# ---------------------------------------------------------------------------

def season_spending_trend(pl_transfers, pl_club_ids):
    """
    Total incoming spending and outgoing transfer income
    per season for Premier League clubs.
    """

    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        &
        pl_transfers["transfer_fee"].notna()
    ]

    outgoing = pl_transfers[
        pl_transfers["from_club_id"].isin(pl_club_ids)
        &
        pl_transfers["transfer_fee"].notna()
    ]

    spend = (
        incoming
        .groupby("transfer_season")["transfer_fee"]
        .sum()
        .rename("spending")
    )

    income = (
        outgoing
        .groupby("transfer_season")["transfer_fee"]
        .sum()
        .rename("revenue")
    )

    trend = pd.concat(
        [spend, income],
        axis=1
    ).fillna(0)

    return trend


def completed_seasons(
    pl_transfers,
    latest_incomplete=None
):
    """
    Return chronological season labels while excluding
    an in-progress season.
    """

    seasons = sorted(
        pl_transfers["transfer_season"]
        .dropna()
        .unique()
    )

    if (
        latest_incomplete
        and latest_incomplete in seasons
    ):
        seasons.remove(latest_incomplete)

    return seasons


# ---------------------------------------------------------------------------
# CLUB SPENDING
# ---------------------------------------------------------------------------

def top_spending_clubs(
    pl_transfers,
    pl_club_ids,
    season=None,
    top_n=10
):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        &
        pl_transfers["transfer_fee"].notna()
    ]

    if season:
        incoming = incoming[
            incoming["transfer_season"] == season
        ]

    return (
        incoming
        .groupby("to_club_name")["transfer_fee"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )


def top_expensive_transfers(
    pl_transfers,
    pl_club_ids,
    season=None,
    top_n=5
):
    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        &
        pl_transfers["transfer_fee"].notna()
    ].copy()

    if season:
        incoming = incoming[
            incoming["transfer_season"] == season
        ]

    return incoming.nlargest(
        top_n,
        "transfer_fee"
    )[
        [
            "player_name",
            "transfer_date",
            "to_club_name",
            "from_club_name",
            "transfer_fee"
        ]
    ]


# ---------------------------------------------------------------------------
# FEE VS MARKET VALUE
# ---------------------------------------------------------------------------

def overpay_bargain_table(pl_transfers):
    """
    Compare transfer fees with recorded market value
    at the time of transfer.
    """

    priced = pl_transfers.dropna(
        subset=[
            "transfer_fee",
            "market_value_in_eur"
        ]
    ).copy()

    priced = priced[
        priced["transfer_fee"] > 0
    ]

    priced = priced[
        priced["market_value_in_eur"] > 0
    ]

    priced["fee_vs_value_eur"] = (
        priced["transfer_fee"]
        -
        priced["market_value_in_eur"]
    )

    priced["overpay_pct"] = (
        priced["fee_vs_value_eur"]
        /
        priced["market_value_in_eur"]
        *
        100
    )

    priced["value_discount_pct"] = (
        (
            priced["market_value_in_eur"]
            -
            priced["transfer_fee"]
        )
        /
        priced["market_value_in_eur"]
        *
        100
    )

    return priced


# ---------------------------------------------------------------------------
# TRADING EFFICIENCY
# ---------------------------------------------------------------------------

def trading_efficiency_by_club(
    transfers,
    pl_club_ids,
    min_trades=6
):
    """
    Match a PL club's purchase of a player to that player's
    next paid transfer.

    ROI:
        (money recouped - money invested)
        / money invested
    """

    t = transfers.sort_values(
        ["player_id", "transfer_date"]
    ).copy()

    t["next_from_club_id"] = (
        t.groupby("player_id")["from_club_id"]
        .shift(-1)
    )

    t["next_transfer_fee"] = (
        t.groupby("player_id")["transfer_fee"]
        .shift(-1)
    )

    buy_sell = t[
        t["to_club_id"].isin(pl_club_ids)
        &
        (
            t["next_from_club_id"]
            ==
            t["to_club_id"]
        )
        &
        t["transfer_fee"].notna()
        &
        (t["transfer_fee"] > 0)
        &
        t["next_transfer_fee"].notna()
        &
        (t["next_transfer_fee"] > 0)
    ].copy()

    grouped = (
        buy_sell
        .groupby("to_club_name")
        .agg(
            n_trades=("transfer_fee", "count"),
            total_invested=("transfer_fee", "sum"),
            total_recouped=("next_transfer_fee", "sum"),
        )
    )

    grouped["profit_per_euro_invested"] = (
        (
            grouped["total_recouped"]
            -
            grouped["total_invested"]
        )
        /
        grouped["total_invested"]
    )

    return (
        grouped[
            grouped["n_trades"] >= min_trades
        ]
        .sort_values(
            "profit_per_euro_invested",
            ascending=False
        )
    )


# ---------------------------------------------------------------------------
# PLAYER IMAGE
# ---------------------------------------------------------------------------

def get_player_image_column(players):
    """
    Find the player image column automatically.
    """

    possible_columns = [
        "image_url",
        "img_url",
        "player_image_url",
        "image",
        "img",
    ]

    for column in possible_columns:
        if column in players.columns:
            return column

    return None


def get_player_image(
    players,
    player_id
):
    """
    Return a player's image URL.
    """

    image_column = get_player_image_column(
        players
    )

    if image_column is None:
        return None

    rows = players[
        players["player_id"] == player_id
    ]

    if rows.empty:
        return None

    image_url = rows.iloc[0][image_column]

    if pd.isna(image_url):
        return None

    return str(image_url)


# ---------------------------------------------------------------------------
# PLAYER SPOTLIGHT
# ---------------------------------------------------------------------------

def player_spotlight(
    transfers,
    players=None,
    season=None
):
    """
    Largest recorded incoming transfer for a season.

    If no season is supplied, returns the largest
    paid transfer in the supplied dataset.
    """

    rows = transfers.copy()

    if season:
        rows = rows[
            rows["transfer_season"] == season
        ]

    rows = rows[
        rows["transfer_fee"].notna()
        &
        (rows["transfer_fee"] > 0)
    ]

    if rows.empty:
        return None

    row = rows.loc[
        rows["transfer_fee"].idxmax()
    ]

    image_url = None

    if players is not None:
        image_url = get_player_image(
            players,
            row["player_id"]
        )

    return {
        "name": row["player_name"],
        "player_id": row["player_id"],
        "from_club": row["from_club_name"],
        "to_club": row["to_club_name"],
        "transfer_date": row["transfer_date"],
        "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row.get(
            "market_value_in_eur",
            None
        ),
        "image_url": image_url,
    }


# ---------------------------------------------------------------------------
# SEASON BARGAIN
# ---------------------------------------------------------------------------

def season_biggest_bargain(
    pl_transfers,
    pl_club_ids,
    season
):
    """
    Biggest absolute market-value discount among
    incoming PL transfers in a season.

    Minimum transfer fee: €5M.
    """

    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        &
        (
            pl_transfers["transfer_season"]
            ==
            season
        )
        &
        pl_transfers["transfer_fee"].notna()
        &
        (pl_transfers["transfer_fee"] >= 5_000_000)
        &
        pl_transfers["market_value_in_eur"].notna()
        &
        (pl_transfers["market_value_in_eur"] > 0)
    ].copy()

    if incoming.empty:
        return None

    incoming["value_gap"] = (
        incoming["market_value_in_eur"]
        -
        incoming["transfer_fee"]
    )

    incoming["discount_pct"] = (
        incoming["value_gap"]
        /
        incoming["market_value_in_eur"]
        *
        100
    )

    row = incoming.nlargest(
        1,
        "discount_pct"
    ).iloc[0]

    return {
        "name": row["player_name"],
        "player_id": row["player_id"],
        "to_club": row["to_club_name"],
        "from_club": row["from_club_name"],
        "transfer_date": row["transfer_date"],
        "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row["market_value_in_eur"],
        "value_gap": row["value_gap"],
        "discount_pct": row["discount_pct"],
    }


# ---------------------------------------------------------------------------
# STEAL DEAL
# ---------------------------------------------------------------------------

def biggest_steal_deal(
    pl_transfers,
    pl_club_ids,
    season=None,
    min_fee=5_000_000
):
    """
    Find the transfer where a PL club paid the largest
    percentage discount relative to the player's recorded
    market value at the time of transfer.

    Minimum fee defaults to €5M to avoid meaningless
    low-value/free-transfer noise.
    """

    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        &
        pl_transfers["transfer_fee"].notna()
        &
        (pl_transfers["transfer_fee"] >= min_fee)
        &
        pl_transfers["market_value_in_eur"].notna()
        &
        (pl_transfers["market_value_in_eur"] > 0)
    ].copy()

    if season:
        incoming = incoming[
            incoming["transfer_season"] == season
        ]

    if incoming.empty:
        return None

    incoming["value_gap"] = (
        incoming["market_value_in_eur"]
        -
        incoming["transfer_fee"]
    )

    incoming["discount_pct"] = (
        incoming["value_gap"]
        /
        incoming["market_value_in_eur"]
        *
        100
    )

    incoming = incoming[
        incoming["discount_pct"] > 0
    ]

    if incoming.empty:
        return None

    row = incoming.loc[
        incoming["discount_pct"].idxmax()
    ]

    return {
        "name": row["player_name"],
        "player_id": row["player_id"],
        "from_club": row["from_club_name"],
        "to_club": row["to_club_name"],
        "transfer_date": row["transfer_date"],
        "transfer_fee": row["transfer_fee"],
        "market_value_in_eur": row["market_value_in_eur"],
        "value_gap": row["value_gap"],
        "discount_pct": row["discount_pct"],
    }


# ---------------------------------------------------------------------------
# BOOM PLAYER
# ---------------------------------------------------------------------------

def boom_player(
    pl_transfers,
    valuations,
    pl_club_ids,
    season=None,
    min_fee=5_000_000,
    min_growth_pct=50
):
    """
    Find a player bought by a Premier League club whose
    market value subsequently increased the most.

    Definition:
        starting value = player's latest recorded market value
        on or before the transfer date

        peak value = highest recorded market value after
        the transfer date

        growth = peak value - starting value

        growth_pct = growth / starting value * 100

    Minimum transfer fee defaults to €5M.
    """

    incoming = pl_transfers[
        pl_transfers["to_club_id"].isin(pl_club_ids)
        &
        pl_transfers["transfer_fee"].notna()
        &
        (pl_transfers["transfer_fee"] >= min_fee)
        &
        pl_transfers["transfer_date"].notna()
    ].copy()

    if season:
        incoming = incoming[
            incoming["transfer_season"] == season
        ]

    if incoming.empty:
        return None

    valuations = valuations.copy()

    valuations = valuations[
        valuations["player_id"].notna()
        &
        valuations["date"].notna()
        &
        valuations["market_value_in_eur"].notna()
    ].copy()

    valuations["player_id"] = (
        valuations["player_id"].astype(int)
    )

    incoming["player_id"] = (
        incoming["player_id"].astype(int)
    )

    results = []

    for _, transfer in incoming.iterrows():

        player_vals = valuations[
            valuations["player_id"]
            ==
            transfer["player_id"]
        ].sort_values("date")

        if player_vals.empty:
            continue

        transfer_date = transfer["transfer_date"]

        # Latest valuation at or before transfer.
        before = player_vals[
            player_vals["date"] <= transfer_date
        ]

        if before.empty:
            continue

        starting_row = before.iloc[-1]

        starting_value = (
            starting_row["market_value_in_eur"]
        )

        if (
            pd.isna(starting_value)
            or starting_value <= 0
        ):
            continue

        # Only valuations after the transfer.
        after = player_vals[
            player_vals["date"] > transfer_date
        ]

        if after.empty:
            continue

        peak_idx = after[
            "market_value_in_eur"
        ].idxmax()

        peak_row = after.loc[peak_idx]

        peak_value = (
            peak_row["market_value_in_eur"]
        )

        growth = (
            peak_value
            -
            starting_value
        )

        growth_pct = (
            growth
            /
            starting_value
            *
            100
        )

        if growth_pct < min_growth_pct:
            continue

        results.append({
            "name": transfer["player_name"],
            "player_id": transfer["player_id"],
            "from_club": transfer["from_club_name"],
            "to_club": transfer["to_club_name"],
            "transfer_date": transfer_date,
            "transfer_fee": transfer["transfer_fee"],
            "starting_value": starting_value,
            "peak_value": peak_value,
            "peak_date": peak_row["date"],
            "value_growth": growth,
            "growth_pct": growth_pct,
        })

    if not results:
        return None

    result_df = pd.DataFrame(results)

    row = result_df.loc[
        result_df["value_growth"].idxmax()
    ]

    return row.to_dict()


# ---------------------------------------------------------------------------
# CLUB TRANSFER PROFILE
# ---------------------------------------------------------------------------

def club_transfer_profile(
    pl_transfers,
    club_name,
    season=None
):
    """
    Compact transfer profile for one Premier League club.
    """

    transfers = pl_transfers.copy()

    if season:
        transfers = transfers[
            transfers["transfer_season"] == season
        ]

    incoming = transfers[
        (
            transfers["to_club_name"]
            ==
            club_name
        )
        &
        transfers["transfer_fee"].notna()
        &
        (transfers["transfer_fee"] > 0)
    ]

    outgoing = transfers[
        (
            transfers["from_club_name"]
            ==
            club_name
        )
        &
        transfers["transfer_fee"].notna()
        &
        (transfers["transfer_fee"] > 0)
    ]

    spending = incoming["transfer_fee"].sum()
    income = outgoing["transfer_fee"].sum()

    return {
        "club": club_name,
        "incoming": incoming,
        "outgoing": outgoing,
        "spending": spending,
        "income": income,
        "net_spend": spending - income,
        "paid_buys": len(incoming),
        "paid_sales": len(outgoing),
        "average_buy": (
            incoming["transfer_fee"].mean()
            if not incoming.empty
            else 0
        ),
        "average_sale": (
            outgoing["transfer_fee"].mean()
            if not outgoing.empty
            else 0
        ),
    }


# ---------------------------------------------------------------------------
# CLUB BADGE
# ---------------------------------------------------------------------------

def club_badge_style(club_name):
    """
    Deterministic initials + accent color for a club.
    """

    palette = [
        "#2FBF71",
        "#E8B75D",
        "#5B9BD5",
        "#D97757",
        "#9B7FD4",
        "#4FBFBF",
    ]

    words = [
        w
        for w in club_name.replace(
            "'",
            ""
        ).split()
        if w
    ]

    initials = (
        "".join(
            w[0]
            for w in words[:2]
        )
        if words
        else club_name[:2]
    )

    color = palette[
        hash(club_name) % len(palette)
    ]

    return initials.upper(), color


# ---------------------------------------------------------------------------
# FORMATTING
# ---------------------------------------------------------------------------

def format_eur_m(value):
    """
    Format EUR values into readable B/M/K notation.
    """

    if value is None or pd.isna(value):
        return "€0"

    value = float(value)

    if abs(value) >= 1_000_000_000:
        return (
            f"€{value / 1_000_000_000:.2f}B"
        )

    if abs(value) >= 1_000_000:
        return (
            f"€{value / 1_000_000:.1f}M"
        )

    if abs(value) >= 1_000:
        return (
            f"€{value / 1_000:.1f}K"
        )

    return f"€{value:,.0f}"