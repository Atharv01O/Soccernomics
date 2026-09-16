"""
Soccernomics
Football Transfer & Market Analytics
"""

import streamlit as st

from styles import inject


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Soccernomics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Global styling
# ---------------------------------------------------------

inject()


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-family:'Space Grotesk', sans-serif;
            font-size:1.6rem;
            font-weight:700;
            color:#EAF2ED;
            margin-bottom:0.2rem;
        ">
            ⚽ Soccernomics
        </div>

        <div style="
            color:#8FA398;
            font-size:0.82rem;
            margin-bottom:1.5rem;
        ">
            Football. Data. Economics.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            border-top:1px solid #223029;
            margin-bottom:1rem;
        "></div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Explore")

    st.markdown(
        """
        **Overview**  
        The football transfer market at a glance.

        **Transfers**  
        Who bought whom — and for how much?

        **Player Market Value**  
        How player valuations move over time.

        **Season Conclusions**  
        What the numbers actually tell us.
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.caption("Data")

    st.markdown(
        """
        **Scope:** Premier League  
        **Coverage:** 2002–2027  
        **Source:** Transfermarkt-derived data
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.caption(
        "Built with Python · Pandas · Plotly · Streamlit"
    )


# ---------------------------------------------------------
# Landing page
# ---------------------------------------------------------

st.markdown(
    """
    <div style="
        max-width:900px;
        padding-top:4rem;
        padding-bottom:2rem;
    ">

        <div style="
            color:#2FBF71;
            font-family:'Space Grotesk', sans-serif;
            font-size:0.85rem;
            font-weight:600;
            letter-spacing:0.12em;
            text-transform:uppercase;
            margin-bottom:0.8rem;
        ">
            FOOTBALL × DATA × ECONOMICS
        </div>

        <div class="sc-title" style="
            font-size:4rem;
            line-height:1;
            margin-bottom:1rem;
        ">
            Soccernomics
        </div>

        <div style="
            color:#8FA398;
            font-size:1.2rem;
            line-height:1.6;
            max-width:700px;
        ">
            A data-driven look at the money behind football —
            from transfer fees and player valuations to club
            spending and market trends.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Quick navigation cards
# ---------------------------------------------------------

st.markdown(
    '<div class="sc-section-label">Explore the analysis</div>',
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class="sc-kpi-card">
            <div class="sc-kpi-label">01 · MARKET</div>
            <div class="sc-kpi-value" style="font-size:1.25rem;">
                Overview
            </div>
            <div style="
                color:#8FA398;
                font-size:0.82rem;
                margin-top:0.5rem;
            ">
                Spending, revenue and market trends.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="sc-kpi-card">
            <div class="sc-kpi-label">02 · TRANSFERS</div>
            <div class="sc-kpi-value" style="font-size:1.25rem;">
                Transfers
            </div>
            <div style="
                color:#8FA398;
                font-size:0.82rem;
                margin-top:0.5rem;
            ">
                Follow the money between clubs.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="sc-kpi-card">
            <div class="sc-kpi-label">03 · PLAYERS</div>
            <div class="sc-kpi-value" style="font-size:1.25rem;">
                Market Value
            </div>
            <div style="
                color:#8FA398;
                font-size:0.82rem;
                margin-top:0.5rem;
            ">
                Explore player valuation trends.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <div class="sc-kpi-card">
            <div class="sc-kpi-label">04 · ANALYSIS</div>
            <div class="sc-kpi-value" style="font-size:1.25rem;">
                Conclusions
            </div>
            <div style="
                color:#8FA398;
                font-size:0.82rem;
                margin-top:0.5rem;
            ">
                Findings backed by the data.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Methodology
# ---------------------------------------------------------

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("Methodology & limitations"):

    st.markdown(
        """
        **Scope**

        Version 1 focuses on Premier League clubs and
        transfer-market activity.

        **Data**

        Transfer and player-market-value data comes from
        a Transfermarkt-derived dataset.

        **What the transfer fee means**

        A transfer fee represents the reported transaction
        value. It should not be interpreted as the player's
        intrinsic or "true" value.

        **Financial data**

        This version does not include audited club financials,
        wages, debt or profit figures.

        **Historical coverage**

        The dataset provides more than two decades of
        transfer-market history, allowing comparisons from
        approximately 2002 through 2027.

        **Interpretation**

        The charts describe patterns in the available data.
        They do not establish causal relationships.
        """
    )