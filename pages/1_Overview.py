# ============================================================
# SOCCERNOMICS — OVERVIEW
# ============================================================

import sys
import os

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import styles

from utils import (
    load_clubs,
    load_players,
    load_transfers,
    get_pl_club_ids,
    get_pl_transfers,
    season_spending_trend,
    top_spending_clubs,
    trading_efficiency_by_club,
    player_spotlight,
    format_eur_m,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Soccernomics — Overview",
    page_icon="⚽",
    layout="wide",
)

styles.inject()


# ============================================================
# COLORS
# ============================================================

GREEN = "#2FBF71"
AMBER = "#E8B75D"
TEXT = "#EAF2ED"
MUTED = "#8FA398"
GRID = "#223029"
BACKGROUND = "rgba(0,0,0,0)"


# ============================================================
# LOAD DATA
# ============================================================

clubs = load_clubs()
players = load_players()
transfers = load_transfers()

pl_club_ids = get_pl_club_ids(
    clubs
)

pl_transfers = get_pl_transfers(
    transfers,
    pl_club_ids
)


# ============================================================
# MARKET TREND
# ============================================================

trend = season_spending_trend(
    pl_transfers,
    pl_club_ids
)


# ============================================================
# COMPLETED SEASONS
# ============================================================

available_seasons = [
    str(x)
    for x in trend.index
    if pd.notna(x)
    and len(str(x)) == 5
    and str(x)[2] == "/"
]

completed_seasons = [
    season
    for season in available_seasons
    if season != "26/27"
]

if not completed_seasons:

    completed_seasons = available_seasons

if not completed_seasons:

    st.error(
        "No completed seasons were found."
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div style="
        color:#2FBF71;
        font-family:'Space Grotesk',sans-serif;
        font-size:0.78rem;
        font-weight:700;
        letter-spacing:0.16em;
        margin-bottom:0.4rem;
    ">
        FOOTBALL × DATA × ECONOMICS
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="
        font-family:'Space Grotesk',sans-serif;
        font-size:3rem;
        font-weight:700;
        line-height:1;
        color:#EAF2ED;
        margin-bottom:0.5rem;
    ">
        Soccernomics
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="
        color:#8FA398;
        font-size:1.05rem;
        max-width:850px;
        margin-bottom:1.2rem;
    ">
        A data-driven view of Premier League transfer spending,
        player valuations, and the economics of the football market.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SEASON SELECTOR
# ============================================================

default_index = (
    completed_seasons.index("25/26")
    if "25/26" in completed_seasons
    else len(completed_seasons) - 1
)

season_col, description_col = st.columns(
    [1, 4]
)

with season_col:

    selected_season = st.selectbox(
        "Season",
        completed_seasons,
        index=default_index,
    )

with description_col:

    st.markdown(
        f"""
        <div style="
            color:#8FA398;
            font-size:0.85rem;
            padding-top:1.8rem;
        ">
            Exploring the Premier League transfer market in
            <strong style="color:#EAF2ED">
                {selected_season}
            </strong>.
            Select another season to compare completed markets.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SELECTED SEASON NUMBERS
# ============================================================

cur_spend = float(
    trend.loc[
        selected_season,
        "spending"
    ]
)

cur_income = float(
    trend.loc[
        selected_season,
        "revenue"
    ]
)

net_spend = (
    cur_spend
    -
    cur_income
)


# ============================================================
# PREVIOUS SEASON
# ============================================================

season_index = completed_seasons.index(
    selected_season
)

if season_index > 0:

    previous_season = (
        completed_seasons[
            season_index - 1
        ]
    )

    previous_spend = float(
        trend.loc[
            previous_season,
            "spending"
        ]
    )

    previous_income = float(
        trend.loc[
            previous_season,
            "revenue"
        ]
    )

else:

    previous_season = None
    previous_spend = None
    previous_income = None


# ============================================================
# YEAR-OVER-YEAR CHANGES
# ============================================================

if (
    previous_spend is not None
    and previous_spend != 0
):

    spend_delta = (
        (
            cur_spend
            -
            previous_spend
        )
        /
        previous_spend
        *
        100
    )

else:

    spend_delta = None


if (
    previous_income is not None
    and previous_income != 0
):

    income_delta = (
        (
            cur_income
            -
            previous_income
        )
        /
        previous_income
        *
        100
    )

else:

    income_delta = None


# ============================================================
# SELECTED SEASON TRANSFERS
# ============================================================

season_transfers = pl_transfers[
    pl_transfers[
        "transfer_season"
    ]
    == selected_season
].copy()


# ============================================================
# PAID INCOMING TRANSFERS
# ============================================================

paid_transfers = season_transfers[
    season_transfers[
        "to_club_id"
    ].isin(pl_club_ids)
    &
    season_transfers[
        "transfer_fee"
    ].notna()
].copy()


paid_transfer_count = len(
    paid_transfers
)

buying_club_count = (
    paid_transfers[
        "to_club_id"
    ].nunique()
    if not paid_transfers.empty
    else 0
)


# ============================================================
# LARGEST TRANSFER
# ============================================================

if not paid_transfers.empty:

    highest_transfer = paid_transfers.loc[
        paid_transfers[
            "transfer_fee"
        ].idxmax()
    ]

    highest_fee = float(
        highest_transfer[
            "transfer_fee"
        ]
    )

    highest_player = (
        highest_transfer[
            "player_name"
        ]
    )

else:

    highest_fee = 0
    highest_player = "—"


# ============================================================
# KPI ROW
# ============================================================

st.markdown(
    "<div style='height:0.6rem'></div>",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(
    4
)

with k1:

    st.metric(
        "Transfer spending",
        format_eur_m(
            cur_spend
        ),
        (
            f"{spend_delta:+.0f}% vs {previous_season}"
            if spend_delta is not None
            else None
        ),
    )

with k2:

    st.metric(
        "Transfer income",
        format_eur_m(
            cur_income
        ),
        (
            f"{income_delta:+.0f}% vs {previous_season}"
            if income_delta is not None
            else None
        ),
    )

with k3:

    st.metric(
        "Net transfer spend",
        format_eur_m(
            net_spend
        ),
    )

    st.caption(
        "Spending − transfer income"
    )

with k4:

    st.metric(
        "Largest transfer",
        format_eur_m(
            highest_fee
        ),
    )

    st.caption(
        highest_player
    )


# ============================================================
# SECONDARY FACTS
# ============================================================

st.markdown(
    "<div style='height:0.6rem'></div>",
    unsafe_allow_html=True,
)

secondary_1, secondary_2 = st.columns(
    2
)

with secondary_1:

    st.markdown(
        f"""
        <div style="
            background:#16211D;
            border:1px solid #223029;
            border-radius:10px;
            padding:0.9rem 1.1rem;
        ">
            <div style="
                color:#8FA398;
                font-size:0.75rem;
                font-weight:600;
                letter-spacing:0.08em;
            ">
                PAID TRANSFERS
            </div>

            <div style="
                color:#EAF2ED;
                font-family:'Space Grotesk',sans-serif;
                font-size:1.6rem;
                font-weight:700;
                margin-top:0.15rem;
            ">
                {paid_transfer_count}
            </div>

            <div style="
                color:#8FA398;
                font-size:0.78rem;
            ">
                Incoming transfers with a recorded fee
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with secondary_2:

    st.markdown(
        f"""
        <div style="
            background:#16211D;
            border:1px solid #223029;
            border-radius:10px;
            padding:0.9rem 1.1rem;
        ">
            <div style="
                color:#8FA398;
                font-size:0.75rem;
                font-weight:600;
                letter-spacing:0.08em;
            ">
                BUYING CLUBS
            </div>

            <div style="
                color:#EAF2ED;
                font-family:'Space Grotesk',sans-serif;
                font-size:1.6rem;
                font-weight:700;
                margin-top:0.15rem;
            ">
                {buying_club_count}
            </div>

            <div style="
                color:#8FA398;
                font-size:0.78rem;
            ">
                Premier League clubs with recorded spending
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MARKET HISTORY
# ============================================================

st.markdown(
    "<div style='height:1.6rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### Premier League transfer market"
)

st.caption(
    "Spending vs transfer income across completed seasons."
)


trend_plot = trend.reset_index().copy()

trend_plot = trend_plot[
    trend_plot[
        "transfer_season"
    ]
    .astype(str)
    .isin(completed_seasons)
]


fig = go.Figure()


fig.add_trace(
    go.Scatter(
        x=trend_plot[
            "transfer_season"
        ],

        y=trend_plot[
            "spending"
        ] / 1e9,

        mode="lines+markers",

        name="Spending",

        line=dict(
            color=GREEN,
            width=2.5,
        ),

        marker=dict(
            size=6,
        ),

        hovertemplate=(
            "<b>%{x}</b><br>"
            "Spending: €%{y:.2f}B"
            "<extra></extra>"
        ),
    )
)


fig.add_trace(
    go.Scatter(
        x=trend_plot[
            "transfer_season"
        ],

        y=trend_plot[
            "revenue"
        ] / 1e9,

        mode="lines+markers",

        name="Transfer income",

        line=dict(
            color=AMBER,
            width=2.5,
        ),

        marker=dict(
            size=6,
        ),

        hovertemplate=(
            "<b>%{x}</b><br>"
            "Transfer income: €%{y:.2f}B"
            "<extra></extra>"
        ),
    )
)


selected_row = trend_plot[
    trend_plot[
        "transfer_season"
    ]
    == selected_season
]


if not selected_row.empty:

    selected_value = (
        selected_row.iloc[0][
            "spending"
        ]
        /
        1e9
    )

    fig.add_trace(
        go.Scatter(
            x=[
                selected_season
            ],

            y=[
                selected_value
            ],

            mode="markers",

            marker=dict(
                color=TEXT,
                size=11,
                line=dict(
                    color=GREEN,
                    width=3,
                ),
            ),

            showlegend=False,

            hovertemplate=(
                f"<b>{selected_season}</b><br>"
                f"Spending: €{selected_value:.2f}B"
                "<extra></extra>"
            ),
        )
    )


fig.update_layout(
    plot_bgcolor=BACKGROUND,
    paper_bgcolor=BACKGROUND,

    font=dict(
        color=TEXT
    ),

    height=390,

    margin=dict(
        l=20,
        r=20,
        t=30,
        b=20,
    ),

    hovermode="x unified",

    xaxis=dict(
        gridcolor=GRID,
        title=None,
    ),

    yaxis=dict(
        gridcolor=GRID,
        zeroline=False,
        title="€ Billion",
    ),

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
)


st.plotly_chart(
    fig,
    width="stretch",
    config={
        "displayModeBar": False
    },
)


# ============================================================
# BIGGEST SPENDERS
# ============================================================

st.markdown(
    "<div style='height:0.8rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    f"### Biggest spenders · {selected_season}"
)

st.caption(
    "Top Premier League clubs by recorded incoming transfer fees."
)


top_spenders = top_spending_clubs(
    pl_transfers,
    pl_club_ids,
    season=selected_season,
    top_n=10,
)


if not top_spenders.empty:

    spenders_plot = (
        top_spenders
        .sort_values()
    )

    fig2 = go.Figure(
        go.Bar(
            x=(
                spenders_plot.values
                /
                1e6
            ),

            y=spenders_plot.index,

            orientation="h",

            marker_color=GREEN,

            hovertemplate=(
                "<b>%{y}</b><br>"
                "Spending: €%{x:.1f}M"
                "<extra></extra>"
            ),
        )
    )

    fig2.update_layout(
        plot_bgcolor=BACKGROUND,
        paper_bgcolor=BACKGROUND,

        font=dict(
            color=TEXT
        ),

        height=400,

        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),

        xaxis=dict(
            gridcolor=GRID,
            title="€ Million",
        ),

        yaxis=dict(
            gridcolor=GRID,
        ),
    )

    st.plotly_chart(
        fig2,
        width="stretch",
        config={
            "displayModeBar": False
        },
    )


# ============================================================
# CLUB INSPECTOR
# ============================================================

if not top_spenders.empty:

    st.markdown(
        "#### Inspect a club"
    )

    selected_club = st.selectbox(
        "Club",
        list(top_spenders.index),
        label_visibility="collapsed",
    )


    club_incoming = season_transfers[
        (
            season_transfers[
                "to_club_name"
            ]
            == selected_club
        )
        &
        season_transfers[
            "transfer_fee"
        ].notna()
    ]


    club_spending = (
        club_incoming[
            "transfer_fee"
        ].sum()
        if not club_incoming.empty
        else 0
    )


    club_outgoing = pl_transfers[
        (
            pl_transfers[
                "from_club_name"
            ]
            == selected_club
        )
        &
        (
            pl_transfers[
                "transfer_season"
            ]
            == selected_season
        )
        &
        pl_transfers[
            "transfer_fee"
        ].notna()
    ]


    club_income = (
        club_outgoing[
            "transfer_fee"
        ].sum()
        if not club_outgoing.empty
        else 0
    )


    club_net = (
        club_spending
        -
        club_income
    )


    club_share = (
        club_spending
        /
        cur_spend
        *
        100
        if cur_spend
        else 0
    )


    club_k1, club_k2, club_k3, club_k4 = st.columns(
        4
    )


    with club_k1:

        st.metric(
            "Spent",
            format_eur_m(
                club_spending
            ),
        )


    with club_k2:

        st.metric(
            "Transfer income",
            format_eur_m(
                club_income
            ),
        )


    with club_k3:

        st.metric(
            "Net transfer spend",
            format_eur_m(
                club_net
            ),
        )


    with club_k4:

        st.metric(
            "Share of PL spending",
            f"{club_share:.1f}%",
        )


# ============================================================
# LARGEST TRANSFER FEES
# ============================================================

st.markdown(
    "<div style='height:1.6rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### Largest transfer fees"
)

st.caption(
    f"Highest recorded incoming transfer fees in {selected_season}."
)


# IMPORTANT:
# We already have paid_transfers filtered to the selected
# season, so there is no reason to call top_expensive_transfers().
#
# This avoids compatibility problems with older utils.py files.

season_largest = (
    paid_transfers
    .nlargest(
        5,
        "transfer_fee"
    )
    .copy()
)


if not season_largest.empty:

    display_transfers = season_largest[
        [
            "player_name",
            "transfer_date",
            "from_club_name",
            "to_club_name",
            "transfer_fee",
        ]
    ].copy()


    display_transfers[
        "Year"
    ] = (
        display_transfers[
            "transfer_date"
        ].dt.year
    )


    display_transfers[
        "Fee"
    ] = (
        display_transfers[
            "transfer_fee"
        ].apply(
            format_eur_m
        )
    )


    display_transfers = display_transfers[
        [
            "player_name",
            "Year",
            "from_club_name",
            "to_club_name",
            "Fee",
        ]
    ]


    display_transfers.columns = [
        "Player",
        "Year",
        "From",
        "To",
        "Fee",
    ]


    st.dataframe(
        display_transfers,
        hide_index=True,
        width="stretch",
    )


# ============================================================
# FEE VS MARKET VALUE
# ============================================================

st.markdown(
    "<div style='height:1.6rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### Transfer fee vs recorded market value"
)

st.caption(
    "Where the negotiated transfer fee sits relative to the recorded player valuation."
)


scatter_data = pl_transfers[
    pl_transfers[
        "transfer_fee"
    ].notna()
    &
    pl_transfers[
        "market_value_in_eur"
    ].notna()
].copy()


scatter_data = scatter_data[
    (
        scatter_data[
            "transfer_fee"
        ] >= 0
    )
    &
    (
        scatter_data[
            "market_value_in_eur"
        ] >= 0
    )
]


if not scatter_data.empty:

    fig3 = go.Figure()


    fig3.add_trace(
        go.Scatter(
            x=(
                scatter_data[
                    "market_value_in_eur"
                ]
                /
                1e6
            ),

            y=(
                scatter_data[
                    "transfer_fee"
                ]
                /
                1e6
            ),

            mode="markers",

            name="Transfers",

            marker=dict(
                color=GREEN,
                size=7,
                opacity=0.55,
            ),

            customdata=scatter_data[
                [
                    "player_name",
                    "from_club_name",
                    "to_club_name",
                    "transfer_season",
                ]
            ].values,

            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Season: %{customdata[3]}<br>"
                "From: %{customdata[1]}<br>"
                "To: %{customdata[2]}<br>"
                "Market value: €%{x:.1f}M<br>"
                "Transfer fee: €%{y:.1f}M"
                "<extra></extra>"
            ),
        )
    )


    max_value = max(
        scatter_data[
            "transfer_fee"
        ].max(),

        scatter_data[
            "market_value_in_eur"
        ].max(),
    ) / 1e6


    fig3.add_trace(
        go.Scatter(
            x=[
                0,
                max_value
            ],

            y=[
                0,
                max_value
            ],

            mode="lines",

            name="Fee = value",

            line=dict(
                color=AMBER,
                width=2,
                dash="dash",
            ),

            hoverinfo="skip",
        )
    )


    fig3.update_layout(
        plot_bgcolor=BACKGROUND,
        paper_bgcolor=BACKGROUND,

        font=dict(
            color=TEXT
        ),

        height=520,

        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),

        xaxis=dict(
            gridcolor=GRID,
            title="Recorded market value (€M)",
        ),

        yaxis=dict(
            gridcolor=GRID,
            title="Transfer fee (€M)",
        ),
    )


    st.plotly_chart(
        fig3,
        width="stretch",
        config={
            "displayModeBar": False
        },
    )


    st.caption(
        f"N={len(scatter_data):,} transfers with both "
        "recorded fee and market value."
    )


# ============================================================
# TRANSFER RETURN
# ============================================================

st.markdown(
    "<div style='height:1.6rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### Transfer return"
)

st.caption(
    "Tracked buy → sell pairs showing transfer proceeds generated per €1 invested."
)


trading = trading_efficiency_by_club(
    transfers,
    pl_club_ids,
    min_trades=6,
).head(5)


if not trading.empty:

    col_return, col_club, col_trades = st.columns(
        [1, 3, 1]
    )


    with col_return:

        st.caption(
            "RETURN"
        )


    with col_club:

        st.caption(
            "CLUB"
        )


    with col_trades:

        st.caption(
            "TRACKED TRADES"
        )


    for club, row in trading.iterrows():

        r1, r2, r3 = st.columns(
            [1, 3, 1]
        )


        with r1:

            st.markdown(
                f"""
                <div style="
                    color:#2FBF71;
                    font-family:'Space Grotesk',sans-serif;
                    font-size:1.05rem;
                    font-weight:700;
                ">
                    {row["profit_per_euro_invested"]:.2f}x
                </div>
                """,
                unsafe_allow_html=True,
            )


        with r2:

            st.write(
                club
            )


        with r3:

            st.caption(
                f'n={int(row["n_trades"])}'
            )


    with st.expander(
        "How is transfer return calculated?"
    ):

        st.markdown(
            """
            **Transfer return = sale proceeds ÷ acquisition fee**

            The calculation tracks players who were bought by a
            Premier League club and later sold in the transfer data.

            Example:

            **€40M sale ÷ €10M acquisition = 4.0x**

            A 4.0x return means the club generated €4 in recorded
            transfer proceeds for every €1 of recorded acquisition fee.

            This is **not club profitability**. Wages, bonuses,
            agent fees, operating costs, amortisation and other
            financial factors are excluded.

            Clubs need at least **6 tracked buy → sell transactions**
            to appear in the ranking.
            """
        )


else:

    st.info(
        "Not enough tracked buy → sell transactions "
        "to calculate this ranking."
    )


# ============================================================
# TRANSFER SPOTLIGHT
# ============================================================

st.markdown(
    "<div style='height:1.8rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### Transfer spotlight"
)

st.caption(
    "The largest recorded incoming transfer of the selected season."
)


spotlight = player_spotlight(
    pl_transfers,
    players,
    selected_season,
)


if spotlight:

    image_col, information_col = st.columns(
        [0.8, 2.2]
    )


    with image_col:

        if spotlight[
            "image_url"
        ]:

            try:

                st.image(
                    spotlight[
                        "image_url"
                    ],
                    width=180,
                )

            except Exception:

                st.write(
                    "Player image unavailable."
                )

        else:

            st.markdown(
                """
                <div style="
                    width:180px;
                    height:180px;
                    background:#16211D;
                    border:1px solid #223029;
                    border-radius:10px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    color:#8FA398;
                ">
                    No image
                </div>
                """,
                unsafe_allow_html=True,
            )


    with information_col:

        st.markdown(
            f"""
            <div style="
                font-family:'Space Grotesk',sans-serif;
                font-size:1.7rem;
                font-weight:700;
                color:#EAF2ED;
            ">
                {spotlight["name"]}
            </div>
            """,
            unsafe_allow_html=True,
        )


        st.caption(
            f'{spotlight["from_club"]} → '
            f'{spotlight["to_club"]} · '
            f'{selected_season}'
        )


        p1, p2 = st.columns(
            2
        )


        with p1:

            st.metric(
                "Transfer fee",
                format_eur_m(
                    spotlight[
                        "transfer_fee"
                    ]
                ),
            )


        with p2:

            market_value = spotlight[
                "market_value_in_eur"
            ]

            if (
                market_value is not None
                and not pd.isna(
                    market_value
                )
            ):

                st.metric(
                    "Recorded market value",
                    format_eur_m(
                        market_value
                    ),
                )

            else:

                st.metric(
                    "Recorded market value",
                    "N/A",
                )


        fee = float(
            spotlight[
                "transfer_fee"
            ]
        )


        market_value = spotlight[
            "market_value_in_eur"
        ]


        if (
            market_value is not None
            and not pd.isna(
                market_value
            )
            and float(
                market_value
            ) > 0
        ):

            market_value = float(
                market_value
            )

            difference_pct = (
                fee
                -
                market_value
            ) / market_value * 100


            if difference_pct > 0:

                st.info(
                    f"The recorded transfer fee was "
                    f"**{difference_pct:.1f}% above** "
                    f"the recorded market value."
                )

            elif difference_pct < 0:

                st.info(
                    f"The recorded transfer fee was "
                    f"**{abs(difference_pct):.1f}% below** "
                    f"the recorded market value."
                )

            else:

                st.info(
                    "The recorded transfer fee matched "
                    "the recorded market value."
                )


# ============================================================
# WHAT THE DATA SAYS
# ============================================================

st.markdown(
    "<div style='height:1.8rem'></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "### What the data says"
)


# ============================================================
# CONCENTRATION
# ============================================================

if not top_spenders.empty:

    top_three_spend = (
        top_spenders
        .sort_values(
            ascending=False
        )
        .head(3)
        .sum()
    )

    concentration = (
        top_three_spend
        /
        cur_spend
        *
        100
        if cur_spend
        else 0
    )

else:

    concentration = 0


# ============================================================
# TAKEAWAYS
# ============================================================

st.markdown(
    f"""
    **01**

    The three biggest spenders accounted for approximately
    **{concentration:.0f}%** of recorded Premier League spending
    in **{selected_season}**.
    """
)


st.markdown(
    f"""
    **02**

    The market recorded **{format_eur_m(cur_spend)}** in spending
    against **{format_eur_m(cur_income)}** in transfer income.
    """
)


if not trading.empty:

    leader_name = trading.index[0]

    leader_return = (
        trading.iloc[0][
            "profit_per_euro_invested"
        ]
    )

    leader_trades = int(
        trading.iloc[0][
            "n_trades"
        ]
    )

else:

    leader_name = "—"
    leader_return = 0
    leader_trades = 0


st.markdown(
    f"""
    **03**

    **{leader_name}** leads the tracked transfer-return ranking
    at **{leader_return:.2f}x**, based on **{leader_trades}**
    tracked buy → sell transactions.
    """
)


# ============================================================
# DATA & METHODOLOGY
# ============================================================

st.markdown(
    "<div style='height:1.5rem'></div>",
    unsafe_allow_html=True,
)


with st.expander(
    "Data & methodology"
):

    st.markdown(
        """
        ### Coverage

        Premier League clubs across the available transfer dataset.
        The Overview uses completed seasons and excludes 26/27 because
        that season is incomplete.

        ### Transfer spending

        Sum of recorded incoming transfer fees for Premier League
        clubs during the selected season.

        ### Transfer income

        Sum of recorded outgoing transfer fees for Premier League
        clubs during the selected season.

        ### Net transfer spend

        **Transfer spending − transfer income**

        This is a transfer-market measure, not a measure of overall
        club profitability.

        ### Market value

        Recorded player market value associated with the transfer
        data. It is a valuation measure, not an objective estimate
        of a player's intrinsic worth.

        ### Transfer return

        **Sale proceeds ÷ acquisition fee**

        The ranking tracks players bought by a Premier League club
        and subsequently sold according to the transfer records.

        A minimum of six tracked buy → sell transactions is required
        for a club to appear.

        ### Important limitation

        Transfer fees do not represent the complete cost of acquiring
        or selling a player. Wages, bonuses, agent fees, signing costs,
        taxes, amortisation and other club financials are outside the
        scope of this project.

        **Soccernomics is a transfer-market analysis, not a complete
        football-club financial statement.**
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    "<div style='height:2rem'></div>",
    unsafe_allow_html=True,
)

st.caption(
    "Soccernomics · Football × Data × Economics"
)