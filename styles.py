"""
Soccernomics — shared visual language.
"""

import streamlit as st


# =========================================================
# DESIGN TOKENS
# =========================================================

BG = "#0E1613"
SURFACE = "#16211D"
SURFACE_2 = "#1B2822"
BORDER = "#26362F"

GREEN = "#2FBF71"
GREEN_MUTED = "#4F9F73"

AMBER = "#E8B75D"
RED = "#E06B6B"
BLUE = "#6EA8FE"

TEXT = "#EAF2ED"
TEXT_2 = "#D7E4DE"
MUTED = "#8FA398"


# =========================================================
# GLOBAL CSS
# =========================================================

CSS = """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap'
);


/* GLOBAL */

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif;
}


/* MAIN CONTENT */

.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}


/* HEADER */

.sc-eyebrow {
    font-family: 'Space Grotesk', sans-serif;
    color: #2FBF71;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.sc-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 2.6rem;
    line-height: 1.05;
    color: #EAF2ED;
    letter-spacing: -0.035em;
    margin-bottom: 0.2rem;
}

.sc-tagline {
    color: #8FA398;
    font-size: 1rem;
    line-height: 1.5;
    margin-bottom: 1.6rem;
}


/* SECTION LABEL */

.sc-section-label {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 1.08rem;
    color: #EAF2ED;
    margin: 0.4rem 0 0.75rem 0;
}


/* STREAMLIT CARDS */

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #16211D;
    border: 1px solid #26362F;
    border-radius: 12px;
}


/* KPI */

.sc-kpi-label {
    color: #8FA398;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    margin-bottom: 0.35rem;
}

.sc-kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 1.65rem;
    color: #EAF2ED;
    line-height: 1.1;
}

.sc-kpi-sub {
    color: #8FA398;
    font-size: 0.78rem;
    margin-top: 0.45rem;
}

.sc-kpi-up {
    color: #2FBF71;
}

.sc-kpi-down {
    color: #E06B6B;
}


/* TAKEAWAYS */

.sc-takeaway {
    display: flex;
    gap: 0.7rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid #26362F;
    color: #D7E4DE;
    font-size: 0.88rem;
    line-height: 1.45;
}

.sc-takeaway:last-child {
    border-bottom: none;
}

.sc-takeaway-mark {
    color: #2FBF71;
    font-weight: 700;
}


/* SPOTLIGHT */

.sc-spotlight-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 1.45rem;
    color: #EAF2ED;
}

.sc-spotlight-sub {
    color: #8FA398;
    font-size: 0.82rem;
    margin-top: 0.15rem;
    margin-bottom: 1rem;
}

.sc-spotlight-quote {
    font-style: italic;
    color: #D7E4DE;
    border-left: 2px solid #E8B75D;
    padding-left: 0.8rem;
    margin-top: 0.8rem;
    font-size: 0.86rem;
    line-height: 1.5;
}


/* INSIGHT CARDS */

.sc-insight-title {
    font-family: 'Space Grotesk', sans-serif;
    color: #EAF2ED;
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.35;
}

.sc-insight-text {
    color: #8FA398;
    font-size: 0.82rem;
    line-height: 1.45;
    margin-top: 0.3rem;
}


/* CONFIDENCE */

.sc-confidence {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    margin-bottom: 0.45rem;
}

.sc-confidence-high {
    color: #2FBF71;
    background: rgba(47,191,113,0.12);
    border: 1px solid rgba(47,191,113,0.25);
}

.sc-confidence-moderate {
    color: #E8B75D;
    background: rgba(232,183,93,0.10);
    border: 1px solid rgba(232,183,93,0.22);
}

.sc-confidence-low {
    color: #8FA398;
    background: rgba(143,163,152,0.08);
    border: 1px solid rgba(143,163,152,0.18);
}


/* SMALL TEXT */

.sc-meta {
    color: #8FA398;
    font-size: 0.74rem;
}

.sc-n {
    color: #8FA398;
    font-size: 0.72rem;
}


/* DIVIDER */

.sc-divider {
    height: 1px;
    background: #26362F;
    margin: 1.5rem 0;
}


/* EXPANDER */

div[data-testid="stExpander"] {
    border-color: #26362F;
    border-radius: 10px;
}

</style>
"""


# =========================================================
# INJECT CSS
# =========================================================

def inject():
    st.markdown(
        CSS,
        unsafe_allow_html=True
    )


# =========================================================
# HEADERS
# =========================================================

def header(title, tagline=None):

    st.markdown(
        f'<div class="sc-title">{title}</div>',
        unsafe_allow_html=True
    )

    if tagline:

        st.markdown(
            f'<div class="sc-tagline">{tagline}</div>',
            unsafe_allow_html=True
        )


def page_header(
    eyebrow,
    title,
    description
):

    st.markdown(
        f'<div class="sc-eyebrow">{eyebrow}</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="sc-title">{title}</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="sc-tagline">{description}</div>',
        unsafe_allow_html=True
    )


# =========================================================
# SECTION LABEL
# =========================================================

def section_label(text):

    st.markdown(
        f'<div class="sc-section-label">{text}</div>',
        unsafe_allow_html=True
    )


# =========================================================
# CARD
# =========================================================

def card():

    return st.container(
        border=True
    )


# =========================================================
# KPI CARD
# =========================================================

def kpi_card(
    label,
    value,
    delta=None,
    delta_positive=True
):

    with card():

        st.markdown(
            f'<div class="sc-kpi-label">{label}</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="sc-kpi-value">{value}</div>',
            unsafe_allow_html=True
        )

        if delta:

            css_class = (
                "sc-kpi-up"
                if delta_positive
                else "sc-kpi-down"
            )

            arrow = (
                "↑"
                if delta_positive
                else "↓"
            )

            st.markdown(
                f"""
                <div class="sc-kpi-sub {css_class}">
                    {arrow} {delta}
                </div>
                """,
                unsafe_allow_html=True
            )


# =========================================================
# TAKEAWAY
# =========================================================

def takeaway(text):

    st.markdown(
        f"""
        <div class="sc-takeaway">
            <span class="sc-takeaway-mark">•</span>
            <span>{text}</span>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# SPOTLIGHT
# =========================================================

def spotlight_header(
    name,
    subtitle
):

    st.markdown(
        f"""
        <div class="sc-spotlight-name">
            {name}
        </div>

        <div class="sc-spotlight-sub">
            {subtitle}
        </div>
        """,
        unsafe_allow_html=True
    )


def spotlight_quote(text):

    st.markdown(
        f"""
        <div class="sc-spotlight-quote">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# INSIGHT CARD
# =========================================================

def insight_card(
    title,
    text=None,
    confidence=None,
    n=None
):

    with card():

        if confidence:
            confidence_badge(
                confidence
            )

        st.markdown(
            f"""
            <div class="sc-insight-title">
                {title}
            </div>
            """,
            unsafe_allow_html=True
        )

        if text:

            st.markdown(
                f"""
                <div class="sc-insight-text">
                    {text}
                </div>
                """,
                unsafe_allow_html=True
            )

        if n is not None:

            st.markdown(
                f"""
                <div class="sc-n">
                    n={n:,}
                </div>
                """,
                unsafe_allow_html=True
            )


# =========================================================
# CONFIDENCE BADGE
# =========================================================

def confidence_badge(level):

    level = str(level).lower()

    if level == "high":

        css = "sc-confidence-high"
        label = "HIGH CONFIDENCE"

    elif level == "moderate":

        css = "sc-confidence-moderate"
        label = "MODERATE CONFIDENCE"

    else:

        css = "sc-confidence-low"
        label = "LOW CONFIDENCE"

    st.markdown(
        f"""
        <span class="sc-confidence {css}">
            {label}
        </span>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# DIVIDER
# =========================================================

def divider():

    st.markdown(
        '<div class="sc-divider"></div>',
        unsafe_allow_html=True
    )


# =========================================================
# EURO FORMATTING
# =========================================================

def format_eur_m(value):

    if value is None:
        return "—"

    try:

        if pd_is_nan(value):
            return "—"

    except Exception:
        pass

    m = value / 1_000_000

    if abs(m) >= 1000:

        return f"€{m / 1000:.2f}B"

    return f"€{m:.1f}M"


def format_eur(value):

    if value is None:
        return "—"

    try:

        if pd_is_nan(value):
            return "—"

    except Exception:
        pass

    if abs(value) >= 1_000_000:

        return format_eur_m(value)

    return f"€{value:,.0f}"


# =========================================================
# NUMBER FORMATTING
# =========================================================

def format_number(value):

    if value is None:
        return "—"

    try:

        if pd_is_nan(value):
            return "—"

    except Exception:
        pass

    return f"{int(value):,}"


# =========================================================
# PERCENTAGE
# =========================================================

def format_pct(
    value,
    decimals=1
):

    if value is None:
        return "—"

    try:

        if pd_is_nan(value):
            return "—"

    except Exception:
        pass

    return f"{value:.{decimals}f}%"


# =========================================================
# SMALL NaN HELPER
# =========================================================

def pd_is_nan(value):

    try:

        return value != value

    except Exception:

        return False