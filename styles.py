"""
Soccernomics — shared visual language.

Design tokens (deliberately chosen, not framework defaults):
  Background   #0E1613  dark charcoal, green-tinted rather than neutral black
  Surface      #16211D  card background
  Border       #223029  subtle hairline
  Accent       #2FBF71  pitch green — primary
  Accent warm  #E8B75D  amber — used only for the spotlight card, sparingly
  Text         #EAF2ED  near-white, green-tinted
  Text muted   #8FA398

Headline type: Space Grotesk (distinct geometric character, not a default choice)
Body type:     Inter (quiet, legible workhorse — headline carries the personality)
"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

.sc-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 2.4rem;
    color: #EAF2ED;
    letter-spacing: -0.02em;
    margin-bottom: 0.1rem;
}

.sc-tagline {
    color: #8FA398;
    font-size: 1.02rem;
    margin-bottom: 1.6rem;
}

.sc-section-label {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 1.05rem;
    color: #EAF2ED;
    margin: 0.2rem 0 0.7rem 0;
}

.sc-kpi-card {
    background: #16211D;
    border: 1px solid #223029;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    height: 100%;
}

.sc-kpi-label {
    color: #8FA398;
    font-size: 0.88rem;
    margin-bottom: 0.35rem;
}

.sc-kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 1.7rem;
    color: #EAF2ED;
    line-height: 1.15;
}

.sc-kpi-delta-up { color: #2FBF71; font-size: 0.85rem; margin-top: 0.25rem; }
.sc-kpi-delta-down { color: #E06B6B; font-size: 0.85rem; margin-top: 0.25rem; }
.sc-kpi-caption { color: #8FA398; font-size: 0.85rem; margin-top: 0.25rem; }

.sc-panel {
    background: #16211D;
    border: 1px solid #223029;
    border-radius: 10px;
    padding: 1.2rem 1.3rem;
    height: 100%;
}

/* Streamlit's native bordered container (st.container(border=True)) is the ONLY reliable
   way to wrap mixed content (markdown + charts + dataframes) in one visual box — raw HTML
   <div> tags opened and closed across separate st.markdown() calls do NOT nest, because
   Streamlit puts each call in its own isolated wrapper. Restyling the native container
   here instead of relying on .sc-panel keeps every panel visually consistent. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #16211D;
    border: 1px solid #223029 !important;
    border-radius: 10px;
}

.sc-takeaway {
    display: flex;
    gap: 0.6rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #223029;
    font-size: 0.92rem;
    color: #D7E4DE;
}
.sc-takeaway:last-child { border-bottom: none; }
.sc-takeaway-mark { color: #2FBF71; font-weight: 700; }

.sc-spotlight-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 1.25rem;
    color: #EAF2ED;
    margin-bottom: 0.1rem;
}
.sc-spotlight-sub { color: #8FA398; font-size: 0.88rem; margin-bottom: 0.8rem; }
.sc-spotlight-quote {
    font-style: italic;
    color: #D7E4DE;
    border-left: 2px solid #E8B75D;
    padding-left: 0.8rem;
    margin-top: 0.6rem;
    font-size: 0.92rem;
}

/* CONFIDENCE */
.sc-confidence {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 500;
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
    color: #B9C6C0;
    background: rgba(143,163,152,0.08);
    border: 1px dashed rgba(143,163,152,0.30);
}

/* INSIGHT CARD — Low confidence is visually de-emphasized, not just badge-colored */
.sc-insight-card {
    background: #16211D;
    border: 1px solid #223029;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem;
}
.sc-insight-card-muted {
    opacity: 0.72;
    border: 1px dashed #223029;
    background: transparent;
    padding: 0.9rem 1.1rem;
}
.sc-insight-card-muted .sc-insight-title {
    font-size: 0.9rem;
    font-weight: 500;
}
.sc-insight-title {
    font-family: 'Space Grotesk', sans-serif;
    color: #EAF2ED;
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.35;
}
.sc-insight-text {
    color: #8FA398;
    font-size: 0.85rem;
    line-height: 1.45;
    margin-top: 0.3rem;
}
.sc-n {
    color: #5C6E66;
    font-size: 0.75rem;
    margin-top: 0.4rem;
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def header(title, tagline):
    st.markdown(f'<div class="sc-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sc-tagline">{tagline}</div>', unsafe_allow_html=True)


def section_label(text):
    st.markdown(f'<div class="sc-section-label">{text}</div>', unsafe_allow_html=True)


def kpi_card(label, value, delta=None, delta_positive=True, caption=None):
    """delta renders as a colored up/down arrow — use only for an actual
    period-over-period comparison. Use `caption` instead for plain subtext
    (a season label, a ratio, "% of revenue") that isn't a trend indicator;
    it renders in neutral muted text with no arrow, so it can't be misread
    as "this number went up" when it's just informational."""
    delta_html = ""
    if delta:
        cls = "sc-kpi-delta-up" if delta_positive else "sc-kpi-delta-down"
        arrow = "\u2191" if delta_positive else "\u2193"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'
    elif caption:
        delta_html = f'<div class="sc-kpi-caption">{caption}</div>'
    st.markdown(
        f"""
        <div class="sc-kpi-card">
            <div class="sc-kpi-label">{label}</div>
            <div class="sc-kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


import contextlib


@contextlib.contextmanager
def panel():
    """Use as `with styles.panel():` — wraps mixed content (markdown, charts, dataframes)
    in one real bordered box. Do not use panel_start()/panel_end() for new code; they don't
    actually nest content and produce an empty box followed by unstyled content."""
    with st.container(border=True):
        yield


def panel_start():
    st.markdown('<div class="sc-panel">', unsafe_allow_html=True)


def panel_end():
    st.markdown("</div>", unsafe_allow_html=True)


def format_eur_m(value):
    """€1,234,567 -> '€1.23M'; scales to B above 1000M."""
    m = value / 1_000_000
    if abs(m) >= 1000:
        return f"€{m/1000:.2f}B"
    return f"€{m:.1f}M"


def _confidence_style(level):
    level = str(level).lower()
    if level == "high":
        return "sc-confidence-high", "High confidence"
    if level == "moderate":
        return "sc-confidence-moderate", "Moderate confidence"
    return "sc-confidence-low", "Low confidence — small sample"


def confidence_badge(level):
    css_class, label = _confidence_style(level)
    st.markdown(f'<span class="sc-confidence {css_class}">{label}</span>', unsafe_allow_html=True)


def insight_card(title, text=None, confidence=None, n=None):
    """A takeaway card. Low confidence is visually de-emphasized (muted, dashed, smaller),
    not just badge-colored — a deliberate fix over designs that treat all confidence levels
    with equal visual weight."""
    wrapper_class = "sc-insight-card"
    if confidence and str(confidence).lower() == "low":
        wrapper_class += " sc-insight-card-muted"

    badge_html = ""
    if confidence:
        css_class, label = _confidence_style(confidence)
        badge_html = f'<span class="sc-confidence {css_class}">{label}</span>'

    text_html = f'<div class="sc-insight-text">{text}</div>' if text else ""
    n_html = f'<div class="sc-n">n={n:,}</div>' if n is not None else ""

    st.markdown(
        f"""
        <div class="{wrapper_class}">
            {badge_html}
            <div class="sc-insight-title">{title}</div>
            {text_html}
            {n_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def club_badge(initials, color, size=34):
    return (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:8px;background:{color}22;'
        f'border:1px solid {color}55;color:{color};font-family:\'Space Grotesk\',sans-serif;'
        f'font-weight:700;font-size:{size*0.38}px;flex-shrink:0;">{initials}</span>'
    )