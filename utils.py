# ============================================================
# SOCCERNOMICS — UTILITY FUNCTIONS
# ============================================================

from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_clubs():
    return pd.read_csv(
        DATA_DIR / "clubs.csv"
    )


@st.cache_data
def load_players():
    return pd.read_csv(
        DATA_DIR / "players.csv"
    )


@st.cache_data
def load_transfers():

    df = pd.read_csv(
        DATA_DIR / "transfers.csv"
    )

    # Convert dates
    if "transfer_date" in df.columns:

        df["transfer_date"] = pd.to_datetime(
            df["transfer_date"],
            errors="coerce"
        )

    # Convert numeric columns
    for column in [
        "transfer_fee",
        "market_value_in_eur",
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


@st.cache_data
def load_player_valuations():

    return pd.read_csv(
        DATA_DIR / "player_valuations.csv"
    )


# ============================================================
# DATA PROFILE
# ============================================================

def profile(df):

    return {
        "rows": len(df),

        "columns": len(
            df.columns
        ),

        "missing_values": int(
            df.isna()
            .sum()
            .sum()
        ),

        "duplicates": int(
            df.duplicated()
            .sum()
        ),
    }


# ============================================================
# PREMIER LEAGUE CLUB IDs
# ============================================================

def get_pl_club_ids(clubs):

    return set(
        clubs[
            clubs[
                "domestic_competition_id"
            ] == "GB1"
        ]["club_id"]
    )


# ============================================================
# PREMIER LEAGUE TRANSFERS
# ============================================================

def get_pl_transfers(
    transfers,
    pl_club_ids
):

    mask = (
        transfers[
            "from_club_id"
        ].isin(pl_club_ids)

        |

        transfers[
            "to_club_id"
        ].isin(pl_club_ids)
    )

    return transfers[
        mask
    ].copy()


# ============================================================
# SEASON SPENDING / TRANSFER INCOME
# ============================================================

def season_spending_trend(
    pl_transfers,
    pl_club_ids
):

    # --------------------------------------------------------
    # Incoming transfers = PL spending
    # --------------------------------------------------------

    incoming = pl_transfers[
        pl_transfers[
            "to_club_id"
        ].isin(pl_club_ids)

        &

        pl_transfers[
            "transfer_fee"
        ].notna()
    ]

    # --------------------------------------------------------
    # Outgoing transfers = PL transfer income
    # --------------------------------------------------------

    outgoing = pl_transfers[
        pl_transfers[
            "from_club_id"
        ].isin(pl_club_ids)

        &

        pl_transfers[
            "transfer_fee"
        ].notna()
    ]

    spending = (
        incoming
        .groupby(
            "transfer_season"
        )[
            "transfer_fee"
        ]
        .sum()
        .rename(
            "spending"
        )
    )

    income = (
        outgoing
        .groupby(
            "transfer_season"
        )[
            "transfer_fee"
        ]
        .sum()
        .rename(
            "revenue"
        )
    )

    trend = pd.concat(
        [
            spending,
            income,
        ],
        axis=1
    ).fillna(0)

    return trend


# ============================================================
# TOP SPENDING CLUBS
# ============================================================

def top_spending_clubs(
    pl_transfers,
    pl_club_ids,
    season=None,
    top_n=10
):

    incoming = pl_transfers[
        pl_transfers[
            "to_club_id"
        ].isin(pl_club_ids)

        &

        pl_transfers[
            "transfer_fee"
        ].notna()
    ].copy()

    if season is not None:

        incoming = incoming[
            incoming[
                "transfer_season"
            ] == season
        ]

    result = (
        incoming
        .groupby(
            "to_club_name"
        )[
            "transfer_fee"
        ]
        .sum()
        .sort_values(
            ascending=False
        )
        .head(top_n)
    )

    return result


# ============================================================
# MOST EXPENSIVE TRANSFERS
# ============================================================

def top_expensive_transfers(
    pl_transfers,
    pl_club_ids,
    season=None,
    top_n=5
):

    incoming = pl_transfers[
        pl_transfers[
            "to_club_id"
        ].isin(pl_club_ids)

        &

        pl_transfers[
            "transfer_fee"
        ].notna()
    ].copy()

    if season is not None:

        incoming = incoming[
            incoming[
                "transfer_season"
            ] == season
        ]

    return (
        incoming
        .nlargest(
            top_n,
            "transfer_fee"
        )[
            [
                "player_name",
                "transfer_date",
                "to_club_name",
                "from_club_name",
                "transfer_fee",
            ]
        ]
    )


# ============================================================
# FEE VS MARKET VALUE
# ============================================================

def overpay_bargain_table(
    pl_transfers
):

    priced = pl_transfers.dropna(
        subset=[
            "transfer_fee",
            "market_value_in_eur",
        ]
    ).copy()

    priced = priced[
        priced[
            "transfer_fee"
        ] > 0
    ]

    priced[
        "fee_vs_value_eur"
    ] = (
        priced[
            "transfer_fee"
        ]

        -

        priced[
            "market_value_in_eur"
        ]
    )

    priced[
        "overpay_pct"
    ] = (
        priced[
            "fee_vs_value_eur"
        ]

        /

        priced[
            "market_value_in_eur"
        ]

        *

        100
    )

    return priced


# ============================================================
# TRANSFER RETURN / TRADING EFFICIENCY
# ============================================================

def trading_efficiency_by_club(
    transfers,
    pl_club_ids,
    min_trades=6
):

    t = transfers.sort_values(
        [
            "player_id",
            "transfer_date",
        ]
    ).copy()

    # --------------------------------------------------------
    # Find each player's next transfer
    # --------------------------------------------------------

    t[
        "next_from_club_id"
    ] = (
        t.groupby(
            "player_id"
        )[
            "from_club_id"
        ]
        .shift(-1)
    )

    t[
        "next_transfer_fee"
    ] = (
        t.groupby(
            "player_id"
        )[
            "transfer_fee"
        ]
        .shift(-1)
    )

    # --------------------------------------------------------
    # Buy → next sale
    # --------------------------------------------------------

    buy_sell = t[
        t[
            "to_club_id"
        ].isin(pl_club_ids)

        &

        (
            t[
                "next_from_club_id"
            ]
            ==

            t[
                "to_club_id"
            ]
        )

        &

        t[
            "transfer_fee"
        ].notna()

        &

        (
            t[
                "transfer_fee"
            ] > 0
        )

        &

        t[
            "next_transfer_fee"
        ].notna()

        &

        (
            t[
                "next_transfer_fee"
            ] > 0
        )
    ].copy()

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    grouped = (
        buy_sell
        .groupby(
            "to_club_name"
        )
        .agg(
            n_trades=(
                "transfer_fee",
                "count"
            ),

            total_invested=(
                "transfer_fee",
                "sum"
            ),

            total_recouped=(
                "next_transfer_fee",
                "sum"
            ),
        )
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Transfer return = sale proceeds / acquisition fee
    #
    # Example:
    # €40M sale / €10M purchase = 4.0x
    # --------------------------------------------------------

    grouped[
        "profit_per_euro_invested"
    ] = (
        grouped[
            "total_recouped"
        ]

        /

        grouped[
            "total_invested"
        ]
    )

    # --------------------------------------------------------
    # Minimum sample size
    # --------------------------------------------------------

    grouped = grouped[
        grouped[
            "n_trades"
        ] >= min_trades
    ]

    return (
        grouped
        .sort_values(
            "profit_per_euro_invested",
            ascending=False
        )
    )


# ============================================================
# PLAYER IMAGE COLUMN
# ============================================================

def get_player_image_column(
    players
):

    possible_columns = [
        "img_url",
        "image_url",
        "player_image_url",
        "image",
        "img",
    ]

    for column in possible_columns:

        if column in players.columns:

            return column

    return None


# ============================================================
# SEASON-AWARE PLAYER SPOTLIGHT
# ============================================================

def player_spotlight(
    transfers,
    players=None,
    season=None
):

    # --------------------------------------------------------
    # Only incoming PL transfers
    #
    # This function assumes transfers has already been
    # filtered to PL-related transfers.
    # --------------------------------------------------------

    rows = transfers.copy()

    if season is not None:

        rows = rows[
            rows[
                "transfer_season"
            ] == season
        ]

    rows = rows[
        rows[
            "transfer_fee"
        ].notna()
    ].copy()

    rows = rows[
        rows[
            "transfer_fee"
        ] > 0
    ]

    if rows.empty:

        return None

    # --------------------------------------------------------
    # Select the biggest incoming transfer
    # --------------------------------------------------------

    row = rows.loc[
        rows[
            "transfer_fee"
        ].idxmax()
    ]

    # --------------------------------------------------------
    # Player image
    # --------------------------------------------------------

    image_url = None

    if players is not None:

        image_column = (
            get_player_image_column(
                players
            )
        )

        if image_column:

            player_rows = players[
                players[
                    "player_id"
                ]
                ==

                row[
                    "player_id"
                ]
            ]

            if not player_rows.empty:

                image_url = (
                    player_rows.iloc[0][
                        image_column
                    ]
                )

                if pd.isna(
                    image_url
                ):

                    image_url = None

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {

        "name":
            row[
                "player_name"
            ],

        "player_id":
            row[
                "player_id"
            ],

        "from_club":
            row[
                "from_club_name"
            ],

        "to_club":
            row[
                "to_club_name"
            ],

        "transfer_date":
            row[
                "transfer_date"
            ],

        "transfer_fee":
            row[
                "transfer_fee"
            ],

        "market_value_in_eur":
            row.get(
                "market_value_in_eur",
                None
            ),

        "image_url":
            image_url,
    }


# ============================================================
# FORMAT EURO VALUES
# ============================================================

def format_eur_m(
    value
):

    if value is None:

        return "€0"

    if pd.isna(value):

        return "€0"

    value = float(
        value
    )

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

    return (
        f"€{value:,.0f}"
    )