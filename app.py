"""
Soccernomics — Premier League Football Financial & Transfer Analytics Platform
"""

import streamlit as st
import styles
from utils import (
    load_clubs,
    load_transfers,
    load_club_financials,
    get_pl_club_ids,
    get_pl_transfers,
    format_eur_m,
)


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Soccernomics — Football Finance & Market Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject()
styles.render_sidebar()

clubs = load_clubs()
transfers = load_transfers()
financials = load_club_financials()
pl_club_ids = get_pl_club_ids(clubs)
pl_transfers = get_pl_transfers(transfers, pl_club_ids)


# ---------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------

st.markdown(
    """
    <div style="max-width:900px;padding-top:2rem;padding-bottom:1.5rem;">
        <div style="color:#2FBF71;font-family:'Space Grotesk', sans-serif;font-size:0.85rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.6rem;">
            FOOTBALL × FINANCIAL ECONOMICS × ANALYTICS
        </div>
        <div class="sc-title" style="font-size:3.5rem;line-height:1.05;margin-bottom:1rem;">
            Soccernomics
        </div>
        <div style="color:#8FA398;font-size:1.15rem;line-height:1.6;max-width:720px;">
            A data-first financial and economic analytics engine for the Premier League. 
            Evaluate transfer spending, contract amortisation, club Deloitte accounts, 
            PSR sustainability limits, and player performance ROI.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Macro Financial KPIs
# ---------------------------------------------------------

tot_transfer_volume = pl_transfers[pl_transfers["transfer_fee"].notna()]["transfer_fee"].sum()
tot_deloitte_revenue = financials["revenue_gbp"].sum() if not financials.empty else 0
tot_wages = financials["wage_cost_gbp"].sum() if not financials.empty else 0
avg_wage_ratio = (tot_wages / tot_deloitte_revenue * 100) if tot_deloitte_revenue > 0 else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    styles.kpi_card("Historical Transfer Volume", format_eur_m(tot_transfer_volume), "2002–2027 recorded moves")
with m2:
    styles.kpi_card("League Aggregate Revenue", f"£{tot_deloitte_revenue/1e9:.2f}B", "Deloitte reported accounts")
with m3:
    styles.kpi_card("Total League Wage Bill", f"£{tot_wages/1e9:.2f}B", "statutory staff expenses")
with m4:
    styles.kpi_card("Aggregate Wage Ratio", f"{avg_wage_ratio:.1f}%", "UEFA benchmark: ≤70%", delta_positive=avg_wage_ratio <= 70)

st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Interactive Module Cards
# ---------------------------------------------------------

styles.section_label("Platform Modules")

c1, c2, c3 = st.columns(3)
with c1:
    with styles.panel():
        st.markdown(
            """
            <div style="color:#2FBF71;font-size:0.75rem;font-weight:700;letter-spacing:1px;margin-bottom:4px;">MODULE 01 & 02</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:1.2rem;font-weight:700;color:#EAF2ED;margin-bottom:8px;">
                Transfers & Amortisation
            </div>
            <div style="color:#8FA398;font-size:0.85rem;line-height:1.45;margin-bottom:12px;">
                Search historical moves, analyze overpay/underpay differentials against Transfermarkt market value benchmarks, and simulate 5-year accounting amortisation schedules.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/2_Transfers.py", label="Open Transfer Analytics →", use_container_width=True)

with c2:
    with styles.panel():
        st.markdown(
            """
            <div style="color:#2FBF71;font-size:0.75rem;font-weight:700;letter-spacing:1px;margin-bottom:4px;">MODULE 03</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:1.2rem;font-weight:700;color:#EAF2ED;margin-bottom:8px;">
                Club Economics & PSR
            </div>
            <div style="color:#8FA398;font-size:0.85rem;line-height:1.45;margin-bottom:12px;">
                Examine statutory Deloitte financial statements for all 20 Premier League clubs. Test 3-year PSR loss limits (£105M cap) and allowable deductions.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/3_Club_Economics.py", label="Open Club Economics →", use_container_width=True)

with c3:
    with styles.panel():
        st.markdown(
            """
            <div style="color:#2FBF71;font-size:0.75rem;font-weight:700;letter-spacing:1px;margin-bottom:4px;">MODULE 04 & 05</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:1.2rem;font-weight:700;color:#EAF2ED;margin-bottom:8px;">
                Player Performance & Insights
            </div>
            <div style="color:#8FA398;font-size:0.85rem;line-height:1.45;margin-bottom:12px;">
                Evaluate Cost per Goal and Cost per Minute from match appearance records, view positional heatmaps, and read empirical case studies (Chelsea ownership shift, Brentford vs Brighton ROI).
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/4_Player_Analytics.py", label="Open Player Analytics →", use_container_width=True)

st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Methodology Disclosures
# ---------------------------------------------------------

with st.expander("Methodology & Data Governance"):
    st.markdown(
        """
        - **Data Integrity:** All findings are measured directly from Transfermarkt transfer records, official Deloitte published accounts, or raw match appearances.
        - **Confidence Framework:** Non-trivial statistical findings carry confidence tags based on sample size (High: n>500, Moderate: n 20-500, Low: n<20).
        - **Financial Accounting:** Player transfer fees are distinguished from operating revenue. Amortisation is calculated straight-line over contract length.
        """
    )

st.markdown(
    "<div style='height:1rem'></div><div style='text-align:center;color:#5C6E66;font-size:.75rem;'>"
    "Soccernomics · Football. Data. Economics."
    "</div>",
    unsafe_allow_html=True,
)
