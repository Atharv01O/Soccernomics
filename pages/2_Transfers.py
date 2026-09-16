# ============================================================
# SOCCERNOMICS — TRANSFERS
# ============================================================

import sys
import os

# Allow pages/ files to import project modules
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import styles

from utils import (
    load_clubs,
    load_transfers,
    load_players,
    load_club_financials,
    get_pl_club_ids,
    get_pl_transfers,
    format_eur_m,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Soccernomics — Transfers",
    page_icon="⚽",
    layout="wide",
)

styles.inject()


# ============================================================
# CHART THEME
# ============================================================

PLOT_BG = "rgba(0,0,0,0)"
GRID = "#223029"
TEXT = "#EAF2ED"
MUTED = "#8FA398"

GREEN = "#2FBF71"
AMBER = "#E8B75D"


# ============================================================
# DATA
# ============================================================

clubs = load_clubs()
players = load_players()
transfers = load_transfers()
financials = load_club_financials()

pl_ids = get_pl_club_ids(clubs)

pl_transfers = get_pl_transfers(
    transfers,
    pl_ids,
).copy()


# ============================================================
# HELPERS
# ============================================================

def season_key(season):
    """
    Sort seasons chronologically.
    Example:
    03/04 -> 3
    24/25 -> 24
    """
    try:
        return int(
            str(season).split("/")[0]
        )
    except Exception:
        return 999


def short_club_name(name):
    """
    Make long club names easier to display.
    """

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
    }

    return replacements.get(
        name,
        name,
    )


# ============================================================
# SEASONS
# ============================================================

all_seasons = sorted(
    pl_transfers[
        "transfer_season"
    ]
    .dropna()
    .unique()
    .tolist(),
    key=season_key,
)

# Exclude incomplete 26/27 if it exists
all_seasons = [
    season
    for season in all_seasons
    if not str(season).startswith("26")
]

if not all_seasons:

    st.error(
        "No completed Premier League seasons were found."
    )

    st.stop()


# ============================================================
# PREMIER LEAGUE CLUBS ONLY
# ============================================================

pl_buying_clubs = set(
    pl_transfers[
        pl_transfers[
            "to_club_id"
        ].isin(pl_ids)
    ][
        "to_club_name"
    ]
    .dropna()
    .unique()
)

pl_selling_clubs = set(
    pl_transfers[
        pl_transfers[
            "from_club_id"
        ].isin(pl_ids)
    ][
        "from_club_name"
    ]
    .dropna()
    .unique()
)

pl_club_names = sorted(
    pl_buying_clubs
    |
    pl_selling_clubs
)


# ============================================================
# HEADER
# ============================================================

header_col, season_col = st.columns(
    [2.8, 1]
)

with header_col:

    styles.header(
        "Transfers",
        "Follow the money — explore how transfer fees move through the Premier League.",
    )

with season_col:

    selected_season = st.selectbox(
        "Season",
        all_seasons,
        index=len(all_seasons) - 1,
    )


# ============================================================
# FILTERS
# ============================================================

filter1, filter2, filter3, filter4 = st.columns(
    [1.25, 1.25, 1.25, 1.5]
)


with filter1:

    selected_club = st.selectbox(
        "Club",
        [
            "All Premier League clubs"
        ]
        +
        pl_club_names,
    )


with filter2:

    direction = st.selectbox(
        "Direction",
        [
            "All transfers",
            "Incoming",
            "Outgoing",
        ],
    )


with filter3:

    window_filter = st.selectbox(
        "Transfer Window",
        [
            "All Windows",
            "Summer Window",
            "Winter Window",
        ],
    )


with filter4:

    season_fees = pl_transfers[
        pl_transfers[
            "transfer_season"
        ]
        == selected_season
    ][
        "transfer_fee"
    ].dropna()

    if not season_fees.empty:

        max_fee_m = max(
            10,
            int(
                season_fees.max()
                / 1_000_000
            )
            + 5,
        )

    else:

        max_fee_m = 150

    minimum_fee_m = st.slider(
        "Minimum transfer fee",
        min_value=0,
        max_value=max_fee_m,
        value=0,
        step=5,
        format="€%dM",
    )


minimum_fee = (
    minimum_fee_m
    * 1_000_000
)


# ============================================================
# SELECTED SEASON
# ============================================================

season_data = pl_transfers[
    pl_transfers[
        "transfer_season"
    ]
    == selected_season
].copy()


# Paid transfers
paid_season = season_data[
    season_data[
        "transfer_fee"
    ].notna()
    &
    (
        season_data[
            "transfer_fee"
        ] > 0
    )
].copy()


# ============================================================
# APPLY FILTERS
# ============================================================

filtered = paid_season.copy()


# ------------------------------------------------------------
# CLUB FILTER
# ------------------------------------------------------------

if (
    selected_club
    != "All Premier League clubs"
):

    if direction == "Incoming":

        filtered = filtered[
            filtered[
                "to_club_name"
            ]
            == selected_club
        ]

    elif direction == "Outgoing":

        filtered = filtered[
            filtered[
                "from_club_name"
            ]
            == selected_club
        ]

    else:

        filtered = filtered[
            (
                filtered[
                    "to_club_name"
                ]
                == selected_club
            )
            |
            (
                filtered[
                    "from_club_name"
                ]
                == selected_club
            )
        ]


# ------------------------------------------------------------
# DIRECTION FILTER
# ------------------------------------------------------------

if direction == "Incoming":

    filtered = filtered[
        filtered[
            "to_club_id"
        ].isin(pl_ids)
    ]

elif direction == "Outgoing":

    filtered = filtered[
        filtered[
            "from_club_id"
        ].isin(pl_ids)
    ]


# ------------------------------------------------------------
# TRANSFER WINDOW
# ------------------------------------------------------------

if window_filter == "Summer Window":

    filtered = filtered[
        filtered["transfer_date"].dt.month.isin(
            [6, 7, 8, 9]
        )
    ]

elif window_filter == "Winter Window":

    filtered = filtered[
        filtered["transfer_date"].dt.month.isin(
            [1, 2]
        )
    ]


# ------------------------------------------------------------
# MINIMUM FEE
# ------------------------------------------------------------

filtered = filtered[
    filtered[
        "transfer_fee"
    ]
    >= minimum_fee
].copy()


# ============================================================
# KPI CALCULATIONS
# ============================================================

incoming = filtered[
    filtered[
        "to_club_id"
    ].isin(pl_ids)
]

outgoing = filtered[
    filtered[
        "from_club_id"
    ].isin(pl_ids)
]


spending = incoming[
    "transfer_fee"
].sum()

income = outgoing[
    "transfer_fee"
].sum()

paid_count = len(
    filtered
)

largest = (
    filtered[
        "transfer_fee"
    ].max()
    if not filtered.empty
    else None
)


# ============================================================
# KPI ROW
# ============================================================

k1, k2, k3, k4 = st.columns(4)


with k1:

    styles.kpi_card(
        "Transfer spending",
        format_eur_m(
            spending
        ),
    )


with k2:

    styles.kpi_card(
        "Transfer income",
        format_eur_m(
            income
        ),
    )


with k3:

    styles.kpi_card(
        "Paid transfers",
        f"{paid_count:,}",
    )


with k4:

    styles.kpi_card(
        "Largest transfer",
        (
            format_eur_m(
                largest
            )
            if largest is not None
            else "—"
        ),
    )


st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


# ============================================================
# TOP PREMIER LEAGUE TRANSFER FLOWS
# ============================================================

with styles.panel():

    styles.section_label(
        "Top Premier League transfer flows"
    )

    st.caption(
        "The largest recorded transfers between two Premier League clubs."
    )

    flow_data = paid_season[
        paid_season[
            "from_club_id"
        ].isin(pl_ids)
        &
        paid_season[
            "to_club_id"
        ].isin(pl_ids)
    ].copy()

    flow_data = flow_data[
        flow_data[
            "transfer_fee"
        ]
        >= minimum_fee
    ]

    if (
        selected_club
        != "All Premier League clubs"
    ):

        flow_data = flow_data[
            (
                flow_data[
                    "from_club_name"
                ]
                == selected_club
            )
            |
            (
                flow_data[
                    "to_club_name"
                ]
                == selected_club
            )
        ]

    flow_pairs = (
        flow_data
        .groupby(
            [
                "from_club_name",
                "to_club_name",
            ],
            as_index=False,
        )[
            "transfer_fee"
        ]
        .sum()
    )

    flow_pairs = flow_pairs.nlargest(
        8,
        "transfer_fee",
    )

    if not flow_pairs.empty:

        flow_pairs[
            "from"
        ] = flow_pairs[
            "from_club_name"
        ].apply(
            short_club_name
        )

        flow_pairs[
            "to"
        ] = flow_pairs[
            "to_club_name"
        ].apply(
            short_club_name
        )

        flow_pairs[
            "flow"
        ] = (
            flow_pairs[
                "from"
            ]
            + "  →  "
            + flow_pairs[
                "to"
            ]
        )

        flow_pairs[
            "fee_m"
        ] = (
            flow_pairs[
                "transfer_fee"
            ]
            / 1_000_000
        )

        flow_pairs = flow_pairs.sort_values(
            "fee_m",
            ascending=True,
        )

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=flow_pairs[
                    "fee_m"
                ],
                y=flow_pairs[
                    "flow"
                ],
                orientation="h",

                marker=dict(
                    color=GREEN,
                    opacity=0.9,
                ),

                customdata=flow_pairs[
                    "transfer_fee"
                ],

                hovertemplate=(
                    "<b>%{y}</b>"
                    "<br>"
                    "Recorded fee: "
                    "%{customdata:$,.0f}"
                    "<extra></extra>"
                ),

                showlegend=False,
            )
        )

        fig.update_layout(
            height=340,

            margin=dict(
                l=5,
                r=20,
                t=5,
                b=10,
            ),

            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,

            font=dict(
                color=TEXT,
                size=12,
            ),

            xaxis=dict(
                title="Transfer fee (€M)",
                gridcolor=GRID,
                zeroline=False,
            ),

            yaxis=dict(
                title="",
                gridcolor=GRID,
            ),
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )

    else:

        st.caption(
            "No Premier League-to-Premier League flows match the selected filters."
        )


# ============================================================
# CLUB ECONOMICS
# ============================================================

st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


left, right = st.columns(
    [1.25, 1]
)


# ============================================================
# CLUB FINANCE DATA
# ============================================================

club_spending = (
    paid_season[
        paid_season[
            "to_club_id"
        ].isin(pl_ids)
    ]
    .groupby(
        "to_club_name"
    )[
        "transfer_fee"
    ]
    .sum()
    .rename(
        "spending"
    )
)

club_income = (
    paid_season[
        paid_season[
            "from_club_id"
        ].isin(pl_ids)
    ]
    .groupby(
        "from_club_name"
    )[
        "transfer_fee"
    ]
    .sum()
    .rename(
        "income"
    )
)

club_finance = pd.concat(
    [
        club_spending,
        club_income,
    ],
    axis=1,
).fillna(0)

club_finance = (
    club_finance
    .reset_index()
    .rename(
        columns={
            "index": "club"
        }
    )
)

club_finance[
    "net_spend"
] = (
    club_finance[
        "spending"
    ]
    -
    club_finance[
        "income"
    ]
)


# ============================================================
# SPENDING VS INCOME
# ============================================================

with left:

    with styles.panel():

        styles.section_label(
            "Spending vs income"
        )

        st.caption(
            "Each dot is a Premier League club. Hover for exact values."
        )

        scatter = club_finance.copy()

        scatter[
            "spending_m"
        ] = (
            scatter[
                "spending"
            ]
            / 1_000_000
        )

        scatter[
            "income_m"
        ] = (
            scatter[
                "income"
            ]
            / 1_000_000
        )

        # ----------------------------------------------------
        # Label only major spenders
        # ----------------------------------------------------

        scatter[
            "label"
        ] = ""

        top_clubs = scatter.nlargest(
            6,
            "spending",
        )[
            "club"
        ].tolist()

        scatter.loc[
            scatter[
                "club"
            ].isin(top_clubs),
            "label"
        ] = scatter.loc[
            scatter[
                "club"
            ].isin(top_clubs),
            "club"
        ].apply(
            short_club_name
        )

        # ----------------------------------------------------
        # Marker styling
        # ----------------------------------------------------

        scatter[
            "marker_size"
        ] = 8

        scatter[
            "marker_color"
        ] = MUTED

        if (
            selected_club
            != "All Premier League clubs"
        ):

            scatter.loc[
                scatter[
                    "club"
                ]
                == selected_club,
                "marker_size"
            ] = 17

            scatter.loc[
                scatter[
                    "club"
                ]
                == selected_club,
                "marker_color"
            ] = GREEN


        fig = go.Figure()


        # ----------------------------------------------------
        # ALL CLUBS
        # ----------------------------------------------------

        fig.add_trace(
            go.Scatter(
                x=scatter[
                    "spending_m"
                ],

                y=scatter[
                    "income_m"
                ],

                mode="markers",

                marker=dict(
                    size=scatter[
                        "marker_size"
                    ],

                    color=scatter[
                        "marker_color"
                    ],

                    opacity=0.9,
                ),

                customdata=scatter[
                    [
                        "club",
                        "spending",
                        "income",
                        "net_spend",
                    ]
                ],

                hovertemplate=(
                    "<b>%{customdata[0]}</b>"
                    "<br>"
                    "Spending: "
                    "€%{customdata[1]:,.0f}"
                    "<br>"
                    "Income: "
                    "€%{customdata[2]:,.0f}"
                    "<br>"
                    "Net spend: "
                    "€%{customdata[3]:,.0f}"
                    "<extra></extra>"
                ),

                showlegend=False,
            )
        )


        # ----------------------------------------------------
        # MAJOR CLUB LABELS
        # ----------------------------------------------------

        label_data = scatter[
            scatter[
                "label"
            ] != ""
        ]

        label_positions = [
            "top center" if i % 2 == 0 else "bottom center"
            for i in range(len(label_data))
        ]

        fig.add_trace(
            go.Scatter(
                x=label_data[
                    "spending_m"
                ],

                y=label_data[
                    "income_m"
                ],

                mode="text",

                text=label_data[
                    "label"
                ],

                textposition=label_positions,

                textfont=dict(
                    size=9,
                    color=TEXT,
                ),

                hoverinfo="skip",
                showlegend=False,
            )
        )


        # ----------------------------------------------------
        # BALANCE LINE
        # ----------------------------------------------------

        max_axis = max(
            scatter[
                "spending_m"
            ].max(),
            scatter[
                "income_m"
            ].max(),
        )

        fig.add_trace(
            go.Scatter(
                x=[
                    0,
                    max_axis,
                ],

                y=[
                    0,
                    max_axis,
                ],

                mode="lines",

                line=dict(
                    color=GRID,
                    width=1,
                    dash="dot",
                ),

                hoverinfo="skip",
                showlegend=False,
            )
        )


        fig.update_layout(
            height=370,

            margin=dict(
                l=5,
                r=10,
                t=5,
                b=5,
            ),

            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,

            font=dict(
                color=TEXT,
            ),

            xaxis=dict(
                title="Spending (€M)",
                gridcolor=GRID,
                zeroline=False,
            ),

            yaxis=dict(
                title="Income (€M)",
                gridcolor=GRID,
                zeroline=False,
            ),

            showlegend=False,
        )


        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )


# ============================================================
# NET TRANSFER BALANCE
# ============================================================

with right:

    with styles.panel():

        styles.section_label(
            "Net transfer balance"
        )

        st.caption(
            "Spending minus income. Negative values indicate a net seller position."
        )

        balance = club_finance.sort_values(
            "net_spend",
            ascending=True,
        ).copy()

        balance[
            "club_short"
        ] = balance[
            "club"
        ].apply(
            short_club_name
        )

        balance[
            "bar_color"
        ] = [
            GREEN
            if value < 0
            else AMBER
            for value
            in balance[
                "net_spend"
            ]
        ]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=balance[
                    "net_spend"
                ]
                / 1_000_000,

                y=balance[
                    "club_short"
                ],

                orientation="h",

                marker=dict(
                    color=balance[
                        "bar_color"
                    ],
                    opacity=0.85,
                ),

                customdata=balance[
                    [
                        "club",
                        "spending",
                        "income",
                        "net_spend",
                    ]
                ],

                hovertemplate=(
                    "<b>%{customdata[0]}</b>"
                    "<br>"
                    "Spending: "
                    "€%{customdata[1]:,.0f}"
                    "<br>"
                    "Income: "
                    "€%{customdata[2]:,.0f}"
                    "<br>"
                    "Net spend: "
                    "€%{customdata[3]:,.0f}"
                    "<extra></extra>"
                ),

                showlegend=False,
            )
        )

        fig.add_vline(
            x=0,
            line_color=GRID,
            line_dash="dot",
            line_width=1,
        )

        fig.update_layout(
            height=370,

            margin=dict(
                l=5,
                r=10,
                t=5,
                b=5,
            ),

            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,

            font=dict(
                color=TEXT,
                size=10,
            ),

            xaxis=dict(
                title="Net spend (€M)",
                gridcolor=GRID,
                zeroline=False,
            ),

            yaxis=dict(
                title="",
                gridcolor=GRID,
            ),

            showlegend=False,
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )


# ============================================================
# TRANSFER FEE DISTRIBUTION
# ============================================================

st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


with styles.panel():

    styles.section_label(
        "Transfer fee distribution"
    )

    st.caption(
        "Most transfers sit at the lower end of the market, while a small number reach blockbuster levels."
    )

    distribution = filtered[
        "transfer_fee"
    ].dropna()

    if not distribution.empty:

        bins = [
            0,
            5_000_000,
            10_000_000,
            20_000_000,
            40_000_000,
            75_000_000,
            float("inf"),
        ]

        labels = [
            "€0–5M",
            "€5–10M",
            "€10–20M",
            "€20–40M",
            "€40–75M",
            "€75M+",
        ]

        bands = pd.cut(
            distribution,
            bins=bins,
            labels=labels,
            right=False,
        )

        band_counts = (
            bands
            .value_counts()
            .reindex(
                labels,
                fill_value=0,
            )
        )

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=band_counts.index,

                y=band_counts.values,

                marker=dict(
                    color=GREEN,
                    opacity=0.9,
                ),

                hovertemplate=(
                    "<b>%{x}</b>"
                    "<br>"
                    "Transfers: %{y}"
                    "<extra></extra>"
                ),

                showlegend=False,
            )
        )

        fig.update_layout(
            height=300,

            margin=dict(
                l=5,
                r=10,
                t=5,
                b=5,
            ),

            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,

            font=dict(
                color=TEXT,
            ),

            xaxis=dict(
                title="Recorded transfer fee",
                gridcolor=GRID,
            ),

            yaxis=dict(
                title="Number of transfers",
                gridcolor=GRID,
                zeroline=False,
            ),

            showlegend=False,
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )

    else:

        st.caption(
            "No paid transfers match the selected filters."
        )


# ============================================================
# TRANSFER ACTIVITY OVER TIME
# ============================================================

st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


with styles.panel():

    styles.section_label(
        "Transfer activity over time"
    )

    st.caption(
        "Track how transfer volume and fee levels have changed across seasons."
    )

    activity_data = pl_transfers[
        pl_transfers[
            "transfer_fee"
        ].notna()
        &
        (
            pl_transfers[
                "transfer_fee"
            ] > 0
        )
        &
        pl_transfers[
            "transfer_season"
        ].isin(
            all_seasons
        )
    ].copy()


    # Follow selected club historically
    if (
        selected_club
        != "All Premier League clubs"
    ):

        activity_data = activity_data[
            (
                activity_data[
                    "to_club_name"
                ]
                == selected_club
            )
            |
            (
                activity_data[
                    "from_club_name"
                ]
                == selected_club
            )
        ]


    activity = (
        activity_data
        .groupby(
            "transfer_season"
        )
        .agg(
            transfers=(
                "transfer_fee",
                "count",
            ),

            total_fees=(
                "transfer_fee",
                "sum",
            ),

            median_fee=(
                "transfer_fee",
                "median",
            ),
        )
        .reset_index()
    )


    metric = st.radio(
        "Metric",

        [
            "Number of transfers",
            "Total fees",
            "Median fee",
        ],

        horizontal=True,

        label_visibility="collapsed",
    )


    metric_map = {

        "Number of transfers": (
            "transfers",
            "Paid transfers",
        ),

        "Total fees": (
            "total_fees",
            "Transfer fees (€)",
        ),

        "Median fee": (
            "median_fee",
            "Median transfer fee (€)",
        ),

    }


    metric_column, y_title = metric_map[
        metric
    ]


    if not activity.empty:

        activity[
            "_order"
        ] = activity[
            "transfer_season"
        ].map(
            {
                season: i
                for i, season
                in enumerate(
                    all_seasons
                )
            }
        )

        activity = activity.sort_values(
            "_order"
        )


        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=activity[
                    "transfer_season"
                ],

                y=activity[
                    metric_column
                ],

                mode="lines+markers",

                line=dict(
                    color=GREEN,
                    width=2,
                ),

                marker=dict(
                    color=GREEN,
                    size=6,
                ),

                hovertemplate=(
                    "%{x}"
                    "<br>"
                    "<b>%{y}</b>"
                    "<extra></extra>"
                ),

                showlegend=False,
            )
        )


        fig.update_layout(
            height=300,

            margin=dict(
                l=5,
                r=10,
                t=5,
                b=5,
            ),

            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,

            font=dict(
                color=TEXT,
            ),

            xaxis=dict(
                title="",
                gridcolor=GRID,
            ),

            yaxis=dict(
                title=y_title,
                gridcolor=GRID,
                zeroline=False,
            ),

            showlegend=False,
        )


        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )

    else:

        st.caption(
            "No activity available for the selected filters."
        )


# ============================================================
# TRANSFER MARKET PROFILE
# ============================================================

st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


with styles.panel():

    styles.section_label(
        "Transfer market profile"
    )

    st.caption(
        f"Key characteristics of the {selected_season} Premier League transfer market."
    )


    # --------------------------------------------------------
    # MARKET DATA
    # --------------------------------------------------------

    all_season_transfers = season_data.copy()

    total_market_transfers = len(
        all_season_transfers
    )


    # Transfers with no positive recorded fee
    free_transfers = all_season_transfers[
        all_season_transfers[
            "transfer_fee"
        ].isna()
        |
        (
            all_season_transfers[
                "transfer_fee"
            ] <= 0
        )
    ]


    free_transfer_pct = (
        len(free_transfers)
        / total_market_transfers
        * 100
        if total_market_transfers
        else 0
    )


    paid = all_season_transfers[
        all_season_transfers[
            "transfer_fee"
        ].notna()
        &
        (
            all_season_transfers[
                "transfer_fee"
            ] > 0
        )
    ]


    if not paid.empty:

        median_fee = paid[
            "transfer_fee"
        ].median()

        average_fee = paid[
            "transfer_fee"
        ].mean()

        blockbuster_count = len(
            paid[
                paid[
                    "transfer_fee"
                ]
                >= 50_000_000
            ]
        )

    else:

        median_fee = 0
        average_fee = 0
        blockbuster_count = 0


    # ========================================================
    # FOUR PROFILE METRICS
    # ========================================================

    p1, p2, p3, p4 = st.columns(4)


    with p1:

        st.metric(
            "Median fee",
            format_eur_m(
                median_fee
            ),
        )


    with p2:

        st.metric(
            "Average fee",
            format_eur_m(
                average_fee
            ),
        )


    with p3:

        st.metric(
            "Free transfers",
            f"{free_transfer_pct:.1f}%",
        )


    with p4:

        st.metric(
            "€50M+ transfers",
            f"{blockbuster_count:,}",
        )


    st.markdown(
        "<div style='height:1rem'></div>",
        unsafe_allow_html=True,
    )


    # ========================================================
    # ROLLING TRANSFER TAPE
    # ========================================================

    styles.section_label(
        "Transfer market tape"
    )

    st.caption(
        "The biggest recorded deals of the selected season."
    )


    ticker_data = paid.sort_values(
        "transfer_fee",
        ascending=False,
    ).head(12).copy()


    if not ticker_data.empty:

        ticker_items = []


        for _, row in ticker_data.iterrows():

            player = str(
                row["player_name"]
            )

            from_club = short_club_name(
                row["from_club_name"]
            )

            to_club = short_club_name(
                row["to_club_name"]
            )

            fee = format_eur_m(
                row["transfer_fee"]
            )


            ticker_items.append(
                f"""
                <div class="transfer-card">

                    <div class="player">
                        {player}
                    </div>

                    <div class="route">
                        {from_club}
                        <span>→</span>
                        {to_club}
                    </div>

                    <div class="fee">
                        {fee}
                    </div>

                </div>
                """
            )


        ticker_html = "".join(
            ticker_items
        )


        # Duplicate content for seamless loop
        ticker_content = (
            ticker_html
            +
            ticker_html
        )


        # ----------------------------------------------------
        # TICKER HTML
        # ----------------------------------------------------

        ticker = f"""
        <style>

            * {{
                box-sizing: border-box;
            }}


            body {{
                margin: 0;
                padding: 0;
                background: transparent;
                overflow: hidden;
            }}


            .ticker-wrapper {{
                width: 100%;
                overflow: hidden;

                border:
                    1px solid #223029;

                border-radius: 10px;

                background:
                    #0E1613;

                position: relative;
            }}


            .ticker-track {{
                display: flex;

                width: max-content;

                animation:
                    soccernomics-scroll
                    35s
                    linear
                    infinite;
            }}


            .ticker-wrapper:hover
            .ticker-track {{
                animation-play-state:
                    paused;
            }}


            .transfer-card {{
                width: 225px;
                min-width: 225px;

                padding:
                    12px 15px;

                border-right:
                    1px solid #223029;
            }}


            .player {{
                color:
                    #EAF2ED;

                font-family:
                    Inter,
                    Arial,
                    sans-serif;

                font-size:
                    14px;

                font-weight:
                    600;

                white-space:
                    nowrap;

                overflow:
                    hidden;

                text-overflow:
                    ellipsis;
            }}


            .route {{
                margin-top:
                    6px;

                color:
                    #8FA398;

                font-family:
                    Inter,
                    Arial,
                    sans-serif;

                font-size:
                    12px;

                white-space:
                    nowrap;
            }}


            .route span {{
                color:
                    #2FBF71;

                padding:
                    0 5px;

                font-weight:
                    600;
            }}


            .fee {{
                margin-top:
                    6px;

                color:
                    #E8B75D;

                font-family:
                    Inter,
                    Arial,
                    sans-serif;

                font-size:
                    14px;

                font-weight:
                    600;
            }}


            @keyframes soccernomics-scroll {{

                from {{
                    transform:
                        translateX(0);
                }}

                to {{
                    transform:
                        translateX(-50%);
                }}

            }}

        </style>


        <div class="ticker-wrapper">

            <div class="ticker-track">

                {ticker_content}

            </div>

        </div>
        """


        components.html(
            ticker,
            height=76,
            scrolling=False,
        )


    else:

        st.caption(
            "No paid transfers available for this season."
        )



# ============================================================
# CLUB TRANSFER PROFILE + HISTORICAL STEAL
# ============================================================


st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)

if selected_club != "All Premier League clubs":

    # ------------------------------------------------------------
    # SELECTED CLUB PROFILE
    # ------------------------------------------------------------

    with styles.panel():

        styles.section_label(
            f"{short_club_name(selected_club)} — TRANSFER PROFILE"
        )

        club_incoming = paid_season[
            paid_season["to_club_name"] == selected_club
        ].copy()

        club_outgoing = paid_season[
            paid_season["from_club_name"] == selected_club
        ].copy()

        club_spending_value = club_incoming["transfer_fee"].sum()
        club_income_value = club_outgoing["transfer_fee"].sum()
        club_net_spend = club_spending_value - club_income_value

        club_paid_buys = len(club_incoming)
        club_paid_sales = len(club_outgoing)

        club_average_buy = (
            club_incoming["transfer_fee"].mean()
            if not club_incoming.empty
            else 0
        )

        club_average_sale = (
            club_outgoing["transfer_fee"].mean()
            if not club_outgoing.empty
            else 0
        )

        p1, p2, p3, p4 = st.columns(4)

        with p1:
            styles.kpi_card(
                "Incoming",
                format_eur_m(club_spending_value),
                caption=f"{club_paid_buys} paid buys",
            )

        with p2:
            styles.kpi_card(
                "Outgoing",
                format_eur_m(club_income_value),
                caption=f"{club_paid_sales} paid sales",
            )

        with p3:
            styles.kpi_card(
                "Net spend",
                format_eur_m(club_net_spend),
                caption="Spending − income",
            )

        with p4:
            styles.kpi_card(
                "Avg buy",
                format_eur_m(club_average_buy),
                caption=(
                    f"Avg sale {format_eur_m(club_average_sale)}"
                    if club_paid_sales
                    else "No paid sales"
                ),
            )

        st.markdown(
            "<div style='height:0.8rem'></div>",
            unsafe_allow_html=True,
        )

        profile_left, profile_right = st.columns(2)

        with profile_left:

            styles.section_label("Biggest arrival")

            if not club_incoming.empty:

                biggest_buy = club_incoming.nlargest(
                    1,
                    "transfer_fee",
                ).iloc[0]

                st.markdown(
                    f"""
                    <div style="
                        padding:12px 14px;
                        border:1px solid #26362e;
                        border-radius:10px;
                        background:#111914;
                    ">
                        <div style="
                            color:#EAF2ED;
                            font-size:16px;
                            font-weight:700;
                        ">
                            {biggest_buy["player_name"]}
                        </div>
                        <div style="
                            color:#8FA398;
                            font-size:12px;
                            margin-top:4px;
                        ">
                            {short_club_name(biggest_buy["from_club_name"])}
                            → {short_club_name(biggest_buy["to_club_name"])}
                        </div>
                        <div style="
                            color:#2FBF71;
                            font-size:18px;
                            font-weight:700;
                            margin-top:7px;
                        ">
                            {format_eur_m(biggest_buy["transfer_fee"])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:
                st.caption("No paid incoming transfers recorded.")

        with profile_right:

            styles.section_label("Biggest sale")

            if not club_outgoing.empty:

                biggest_sale = club_outgoing.nlargest(
                    1,
                    "transfer_fee",
                ).iloc[0]

                st.markdown(
                    f"""
                    <div style="
                        padding:12px 14px;
                        border:1px solid #26362e;
                        border-radius:10px;
                        background:#111914;
                    ">
                        <div style="
                            color:#EAF2ED;
                            font-size:16px;
                            font-weight:700;
                        ">
                            {biggest_sale["player_name"]}
                        </div>
                        <div style="
                            color:#8FA398;
                            font-size:12px;
                            margin-top:4px;
                        ">
                            {short_club_name(biggest_sale["from_club_name"])}
                            → {short_club_name(biggest_sale["to_club_name"])}
                        </div>
                        <div style="
                            color:#E8B75D;
                            font-size:18px;
                            font-weight:700;
                            margin-top:7px;
                        ">
                            {format_eur_m(biggest_sale["transfer_fee"])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:
                st.caption("No paid outgoing transfers recorded.")


    # ------------------------------------------------------------
    # HISTORICAL STEAL DEAL
    # ------------------------------------------------------------

    st.markdown("<div style='height:1.1rem'></div>", unsafe_allow_html=True)

    with styles.panel():
        styles.section_label("Historical steal deal")

        # Historical = all recorded incoming transfers for selected club.
        steal_pool = pl_transfers[
            (pl_transfers["to_club_name"] == selected_club)
            & pl_transfers["transfer_fee"].notna()
            & (pl_transfers["transfer_fee"] > 0)
        ].copy()

        if "market_value_in_eur" in steal_pool.columns:
            steal_pool = steal_pool[
                steal_pool["market_value_in_eur"].notna()
                & (steal_pool["market_value_in_eur"] > 0)
            ].copy()

            if not steal_pool.empty:
                steal_pool["discount_pct"] = (
                    (steal_pool["market_value_in_eur"] - steal_pool["transfer_fee"])
                    / steal_pool["market_value_in_eur"] * 100
                )
                steal_pool = steal_pool[steal_pool["discount_pct"] > 0].copy()

            if not steal_pool.empty:
                steal = steal_pool.nlargest(1, "discount_pct").iloc[0]
                player = str(steal["player_name"])
                route = f'{short_club_name(steal["from_club_name"])} → {short_club_name(steal["to_club_name"])}'
                discount = f'{steal["discount_pct"]:.0f}% below recorded value'
                fee = format_eur_m(steal["transfer_fee"])
                value = format_eur_m(steal["market_value_in_eur"])
                season = str(steal["transfer_season"])

                # Player image from players.csv
                image_column = next(
                    (c for c in ["image_url", "img_url", "player_image_url", "image", "img"] if c in players.columns),
                    None,
                )
                player_image = None
                if image_column is not None:
                    player_rows = players[players["player_id"] == steal["player_id"]]
                    if not player_rows.empty and pd.notna(player_rows.iloc[0][image_column]):
                        player_image = str(player_rows.iloc[0][image_column]).strip()

                steal_col1, steal_col2 = st.columns([1, 1], gap="medium")

                # Keep both cards in identical-height HTML boxes so their edges and content line up.
                if player_image:
                    image_html = (
                        f'<img src="{player_image}" style="width:88px;height:88px;object-fit:cover;'
                        'border-radius:50%;border:1px solid #26362e;background:#18221d;flex-shrink:0;">'
                    )
                else:
                    image_html = (
                        '<div style="width:88px;height:88px;border-radius:50%;background:#18221d;'
                        'display:flex;align-items:center;justify-content:center;font-size:34px;'
                        'border:1px solid #26362e;flex-shrink:0;">⚽</div>'
                    )

                deal_card = (
                    '<div style="height:230px;box-sizing:border-box;padding:18px 20px;border:1px solid #26362e;'
                    'border-radius:12px;background:#111914;display:flex;flex-direction:column;justify-content:center;">'
                    '<div style="color:#2FBF71;font-size:11px;font-weight:700;letter-spacing:1.2px;margin-bottom:12px;">'
                    'BEST VALUE GAP</div>'
                    f'<div style="display:flex;align-items:center;gap:16px;">{image_html}'
                    f'<div style="min-width:0;"><div style="color:#EAF2ED;font-size:21px;font-weight:700;">{steal["player_name"]}</div>'
                    f'<div style="color:#8FA398;font-size:13px;margin-top:5px;">{short_club_name(steal["from_club_name"])} → {short_club_name(steal["to_club_name"])}</div></div></div>'
                    f'<div style="color:#2FBF71;font-size:24px;font-weight:700;margin-top:16px;">{steal["discount_pct"]:.0f}% below recorded value</div>'
                    '</div>'
                )

                snapshot_card = (
                    '<div style="height:230px;box-sizing:border-box;padding:18px 20px;border:1px solid #26362e;'
                    'border-radius:12px;background:#111914;display:flex;flex-direction:column;justify-content:center;">'
                    '<div style="color:#8FA398;font-size:11px;font-weight:700;letter-spacing:1.2px;margin-bottom:18px;">'
                    'TRANSFER SNAPSHOT</div>'
                    f'<div style="color:#8FA398;font-size:12px;letter-spacing:.5px;">TRANSFER FEE</div>'
                    f'<div style="color:#EAF2ED;font-size:22px;font-weight:700;margin-top:4px;">{format_eur_m(steal["transfer_fee"])}</div>'
                    f'<div style="color:#8FA398;font-size:12px;letter-spacing:.5px;margin-top:17px;">RECORDED MARKET VALUE</div>'
                    f'<div style="color:#EAF2ED;font-size:22px;font-weight:700;margin-top:4px;">{format_eur_m(steal["market_value_in_eur"])}</div>'
                    f'<div style="color:#8FA398;font-size:12px;margin-top:16px;">Season {steal["transfer_season"]}</div>'
                    '</div>'
                )

                with steal_col1:
                    st.markdown(deal_card, unsafe_allow_html=True)
                with steal_col2:
                    st.markdown(snapshot_card, unsafe_allow_html=True)

            else:
                st.caption("No incoming transfer was recorded below market value for this club.")
        else:
            st.caption("Market-value data is not available in the transfer dataset.")

else:
    pass


# ============================================================
# DELOITTE FINANCIAL CONDITION
# ============================================================

st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


def normalise_financial_club_name(name):
    """Match Transfermarkt club names to Deloitte club names."""

    value = str(name).lower().strip()

    aliases = {
        "man utd": "manchester united",
        "manchester united": "manchester united",
        "man city": "manchester city",
        "manchester city": "manchester city",
        "newcastle": "newcastle united",
        "newcastle united": "newcastle united",
        "tottenham": "tottenham hotspur",
        "tottenham hotspur": "tottenham hotspur",
        "west ham": "west ham united",
        "west ham united": "west ham united",
        "wolves": "wolverhampton wanderers",
        "wolverhampton wanderers": "wolverhampton wanderers",
        "wolverhampton wdrs": "wolverhampton wanderers",
        "brighton": "brighton & hove albion",
        "brighton & hove albion": "brighton & hove albion",
        "nott'm forest": "nottingham forest",
        "nottingham forest": "nottingham forest",
        "leicester": "leicester city",
        "leicester city": "leicester city",
        "sheffield utd": "sheffield united",
        "sheffield united": "sheffield united",
        "bournemouth": "afc bournemouth",
        "afc bournemouth": "afc bournemouth",
    }

    return aliases.get(value, value)


financials_for_match = financials.copy()

financials_for_match["club_key"] = (
    financials_for_match["club"]
    .apply(normalise_financial_club_name)
)


# ============================================================
# SELECTED CLUB FINANCIAL CONDITION
# ============================================================

if selected_club != "All Premier League clubs":

    with styles.panel():

        styles.section_label(
            f"{short_club_name(selected_club)} — financial condition"
        )

        st.caption(
            "Reported 2024/25 financial snapshot from Deloitte's "
            "Annual Review of Football Finance."
        )

        selected_financial = financials_for_match[
            (
                financials_for_match["club_key"]
                == normalise_financial_club_name(selected_club)
            )
            &
            (
                financials_for_match["season"]
                == "2024/25"
            )
        ].copy()

        if not selected_financial.empty:

            row = selected_financial.iloc[0]

            revenue = row["revenue_gbp"]
            wages = row["wage_cost_gbp"]
            operating_result = row["operating_result_gbp"]
            pre_tax_result = row["pre_tax_profit_loss_gbp"]
            net_funds_debt = row["net_funds_debt_gbp"]

            wage_ratio = row["wage_to_revenue_pct"]
            operating_margin = row["operating_margin_pct"]
            net_debt_ratio = row["net_debt_to_revenue_pct"]

            f1, f2, f3, f4 = st.columns(4)

            with f1:
                styles.kpi_card(
                    "Revenue",
                    f"£{revenue / 1_000_000:.1f}M",
                    caption="2024/25",
                )

            with f2:
                styles.kpi_card(
                    "Wage costs",
                    f"£{wages / 1_000_000:.1f}M",
                    caption=f"{wage_ratio:.1f}% of revenue",
                )

            with f3:
                styles.kpi_card(
                    "Operating result",
                    f"£{operating_result / 1_000_000:.1f}M",
                    caption=f"{operating_margin:.1f}% margin",
                )

            with f4:
                balance_label = (
                    "Net funds"
                    if net_funds_debt >= 0
                    else "Net debt"
                )

                styles.kpi_card(
                    balance_label,
                    f"£{abs(net_funds_debt) / 1_000_000:.1f}M",
                    caption="Deloitte 2024/25",
                )

            st.markdown(
                "<div style='height:0.8rem'></div>",
                unsafe_allow_html=True,
            )

            s1, s2, s3 = st.columns(3)

            with s1:
                st.metric(
                    "Pre-tax profit / loss",
                    f"£{pre_tax_result / 1_000_000:.1f}M",
                )

            with s2:
                st.metric(
                    "Wage / revenue",
                    f"{wage_ratio:.1f}%",
                )

            with s3:
                st.metric(
                    "Net debt / revenue",
                    (
                        f"{net_debt_ratio:.1f}%"
                        if net_funds_debt < 0
                        else "Net funds"
                    ),
                )

            st.markdown(
                "<div style='height:0.8rem'></div>",
                unsafe_allow_html=True,
            )

            financial_left, financial_right = st.columns(
                [1.15, 1]
            )

            with financial_left:

                styles.section_label(
                    "Revenue vs. wage costs"
                )

                chart_df = pd.DataFrame(
                    {
                        "Metric": [
                            "Revenue",
                            "Wage costs",
                        ],
                        "Value": [
                            revenue / 1_000_000,
                            wages / 1_000_000,
                        ],
                    }
                )

                fig = go.Figure()

                fig.add_trace(
                    go.Bar(
                        x=chart_df["Metric"],
                        y=chart_df["Value"],
                        marker=dict(
                            color=[GREEN, AMBER],
                            opacity=0.9,
                        ),
                        hovertemplate=(
                            "<b>%{x}</b>"
                            "<br>£%{y:.1f}M"
                            "<extra></extra>"
                        ),
                        showlegend=False,
                    )
                )

                fig.update_layout(
                    height=300,
                    margin=dict(l=5, r=10, t=10, b=5),
                    paper_bgcolor=PLOT_BG,
                    plot_bgcolor=PLOT_BG,
                    font=dict(color=TEXT),
                    xaxis=dict(gridcolor=GRID),
                    yaxis=dict(
                        title="£ millions",
                        gridcolor=GRID,
                        zeroline=False,
                    ),
                    showlegend=False,
                )

                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            with financial_right:

                styles.section_label(
                    "OPERATING VS PRE-TAX RESULT"
                )

                result_df = pd.DataFrame(
                    {
                        "Metric": [
                            "Operating result",
                            "Pre-tax result",
                        ],
                        "Value": [
                            operating_result / 1_000_000,
                            pre_tax_result / 1_000_000,
                        ],
                    }
                )

                fig = go.Figure()

                fig.add_trace(
                    go.Bar(
                        x=result_df["Metric"],
                        y=result_df["Value"],
                        marker=dict(
                            color=GREEN,
                            opacity=0.9,
                        ),
                        hovertemplate=(
                            "<b>%{x}</b>"
                            "<br>£%{y:.1f}M"
                            "<extra></extra>"
                        ),
                        showlegend=False,
                    )
                )

                fig.add_hline(
                    y=0,
                    line_color=GRID,
                    line_dash="dot",
                    line_width=1,
                )

                fig.update_layout(
                    height=300,
                    margin=dict(l=5, r=10, t=10, b=5),
                    paper_bgcolor=PLOT_BG,
                    plot_bgcolor=PLOT_BG,
                    font=dict(color=TEXT),
                    xaxis=dict(gridcolor=GRID),
                    yaxis=dict(
                        title="£ millions",
                        gridcolor=GRID,
                        zeroline=False,
                    ),
                    showlegend=False,
                )

                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            if wage_ratio >= 80:
                wage_comment = (
                    "Wages absorb a very large share of reported revenue."
                )
            elif wage_ratio >= 60:
                wage_comment = (
                    "Wage costs represent a substantial share of reported revenue."
                )
            else:
                wage_comment = (
                    "Wage costs consume a comparatively lower share of reported revenue."
                )

            if operating_result >= 0:
                operating_comment = (
                    "The club recorded a positive operating result."
                )
            else:
                operating_comment = (
                    "The club recorded an operating loss."
                )

            if net_funds_debt >= 0:
                balance_comment = (
                    "Deloitte reports net funds rather than net debt."
                )
            else:
                balance_comment = (
                    "Deloitte reports net debt for the club."
                )

            styles.insight_card(
                "What the numbers say",
                (
                    f"{wage_comment} "
                    f"{operating_comment} "
                    f"{balance_comment}"
                ),
            )

        else:

            st.info(
                "Deloitte financial data is not available for this club."
            )


# ============================================================
# DELOITTE — PREMIER LEAGUE FINANCIAL LANDSCAPE
# ============================================================

st.markdown(
    "<div style='height:1.1rem'></div>",
    unsafe_allow_html=True,
)


with styles.panel():

    styles.section_label(
        "Premier League financial landscape"
    )

    st.caption(
        "2024/25 reported revenue, wage costs and financial "
        "position across Premier League clubs."
    )

    league_financials = financials_for_match[
        financials_for_match["season"] == "2024/25"
    ].copy()

    if not league_financials.empty:

        league_financials["club_short"] = (
            league_financials["club"]
            .apply(short_club_name)
        )

        styles.section_label(
            "Revenue vs. wage costs"
        )

        league_sorted = league_financials.sort_values(
            "revenue_gbp",
            ascending=True,
        )

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                y=league_sorted["club_short"],
                x=(
                    league_sorted["revenue_gbp"]
                    / 1_000_000
                ),
                orientation="h",
                name="Revenue",
                marker=dict(
                    color=GREEN,
                    opacity=0.9,
                ),
                hovertemplate=(
                    "<b>%{y}</b>"
                    "<br>Revenue: £%{x:.1f}M"
                    "<extra></extra>"
                ),
            )
        )

        fig.add_trace(
            go.Bar(
                y=league_sorted["club_short"],
                x=(
                    league_sorted["wage_cost_gbp"]
                    / 1_000_000
                ),
                orientation="h",
                name="Wage costs",
                marker=dict(
                    color=AMBER,
                    opacity=0.85,
                ),
                hovertemplate=(
                    "<b>%{y}</b>"
                    "<br>Wage costs: £%{x:.1f}M"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            height=600,
            barmode="group",
            margin=dict(l=5, r=20, t=5, b=5),
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT, size=11),
            xaxis=dict(
                title="£ millions",
                gridcolor=GRID,
                zeroline=False,
            ),
            yaxis=dict(
                title="",
                gridcolor=GRID,
            ),
            legend=dict(
                orientation="h",
                y=1.03,
                x=0,
            ),
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False},
        )

        pressure_left, pressure_right = st.columns(2)

        with pressure_left:

            styles.section_label(
                "Wage-to-revenue ratio"
            )

            wage_rank = league_financials.sort_values(
                "wage_to_revenue_pct",
                ascending=True,
            )

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    y=wage_rank["club_short"],
                    x=wage_rank[
                        "wage_to_revenue_pct"
                    ],
                    orientation="h",
                    marker=dict(
                        color=GREEN,
                        opacity=0.9,
                    ),
                    hovertemplate=(
                        "<b>%{y}</b>"
                        "<br>Wages / revenue: %{x:.1f}%"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

            fig.update_layout(
                height=500,
                margin=dict(l=5, r=10, t=5, b=5),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=10),
                xaxis=dict(
                    title="Wages as % of revenue",
                    gridcolor=GRID,
                    zeroline=False,
                ),
                yaxis=dict(
                    title="",
                    gridcolor=GRID,
                ),
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

        with pressure_right:

            styles.section_label(
                "Net funds / debt"
            )

            debt_rank = league_financials.sort_values(
                "net_funds_debt_gbp",
                ascending=True,
            )

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    y=debt_rank["club_short"],
                    x=(
                        debt_rank[
                            "net_funds_debt_gbp"
                        ]
                        / 1_000_000
                    ),
                    orientation="h",
                    marker=dict(
                        color=[
                            GREEN
                            if value >= 0
                            else AMBER
                            for value
                            in debt_rank[
                                "net_funds_debt_gbp"
                            ]
                        ],
                        opacity=0.9,
                    ),
                    hovertemplate=(
                        "<b>%{y}</b>"
                        "<br>Net funds / debt: £%{x:.1f}M"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

            fig.add_vline(
                x=0,
                line_color=GRID,
                line_dash="dot",
                line_width=1,
            )

            fig.update_layout(
                height=500,
                margin=dict(l=5, r=10, t=5, b=5),
                paper_bgcolor=PLOT_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT, size=10),
                xaxis=dict(
                    title="£ millions",
                    gridcolor=GRID,
                    zeroline=False,
                ),
                yaxis=dict(
                    title="",
                    gridcolor=GRID,
                ),
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

        highest_revenue = league_financials.loc[
            league_financials["revenue_gbp"].idxmax()
        ]

        highest_wages = league_financials.loc[
            league_financials["wage_cost_gbp"].idxmax()
        ]

        highest_wage_ratio = league_financials.loc[
            league_financials["wage_to_revenue_pct"].idxmax()
        ]

        strongest_operating = league_financials.loc[
            league_financials["operating_result_gbp"].idxmax()
        ]

        weakest_balance = league_financials.loc[
            league_financials["net_funds_debt_gbp"].idxmin()
        ]

        styles.insight_card(
            "Deloitte league insight",
            (
                f"{short_club_name(highest_revenue['club'])} "
                f"reported the highest revenue at "
                f"£{highest_revenue['revenue_gbp'] / 1_000_000:.1f}M. "
                f"{short_club_name(highest_wages['club'])} "
                f"had the highest wage bill at "
                f"£{highest_wages['wage_cost_gbp'] / 1_000_000:.1f}M. "
                f"{short_club_name(highest_wage_ratio['club'])} "
                f"had the highest wage-to-revenue ratio at "
                f"{highest_wage_ratio['wage_to_revenue_pct']:.1f}%. "
                f"{short_club_name(strongest_operating['club'])} "
                f"recorded the strongest operating result, while "
                f"{short_club_name(weakest_balance['club'])} "
                f"had the weakest net funds/debt position."
            ),
        )

    else:

        st.info(
            "No Deloitte financial data is available."
        )


# ============================================================
# METHODOLOGY
# ============================================================

with st.expander(
    "Methodology & data limitations"
):

    st.markdown(
        """
        **Transfer spending** is the sum of recorded transfer fees
        for players joining Premier League clubs.

        **Transfer income** is the sum of recorded transfer fees
        for players leaving Premier League clubs.

        **Net transfer spend** is transfer spending minus transfer
        income.

        **Top transfer flows** only include transactions where both
        the buying and selling clubs are Premier League clubs.

        **Median and average fees** use paid transfers only.

        **Free transfer percentage** includes transfers with no
        recorded positive transfer fee.

        Transfer fees come from the underlying Transfermarkt-derived
        dataset. Reported values may differ elsewhere because of
        add-ons, bonuses, exchange rates, or source methodology.

        Transfer activity should not be interpreted as complete club
        profitability. Wages, operating revenue, agent fees,
        amortisation, debt, and other financial items are not included.

        **Financial Condition** uses the supplied Deloitte Annual Review
        of Football Finance 2026 club-level data for 2024/25.

        Deloitte financial figures are reported in GBP and represent the
        relevant reported financial period, not transfer-market values.

        **Transfer Window** is a simplified analytical classification:
        June–September is treated as summer and January–February as winter.
        It is not intended to reproduce every season's exact official
        registration-window dates.
        """
    )