# Soccernomics

Evidence-first analytics on the Premier League transfer market — spending, player valuations, and trading efficiency — built on real transfer and valuation data, not predictions.

**Live app:** _add your deployed Streamlit URL here_

## What this is

Not a prediction engine. Every finding in this project is either:
- **Measured** — a fact directly in the data (a transfer fee, a valuation, an age)
- **Descriptive** — an aggregate or trend computed from the data, reported with its sample size
- **Estimated** — clearly labeled as such where used, and kept to a minimum, because unlike physical systems (e.g. tyre degradation), transfer fees are negotiated outcomes with no reliable mechanistic model behind them

Every non-trivial claim in the app carries a confidence label (High / Moderate / Low) based on sample size, and Low-confidence findings are visually de-emphasized rather than presented with the same weight as well-supported ones.

## What it answers

- How does a Premier League player's market value change with age — and does that differ by position?
- Which transfers were the biggest bargains and overpays relative to market value at the time?
- Does a club's transfer strategy show a measurable shift after an ownership change? (Chelsea, post-2022, as a case study)
- Which clubs are actually the most efficient traders (buy-low, sell-high) by return on investment — not just by reputation?

## Key findings so far

1. **Market value peaks at age 26 across every position** — but the decline rate afterward is highly position-dependent. Attackers lose value fastest (~23% of peak retained by 32); goalkeepers are the outlier, retaining ~60% of peak value at the same age. *(High confidence, n=32,544+ valuation records)*
2. **Erling Haaland's 2022 move to Man City is the single biggest bargain** in the dataset by fee-vs-valuation (€60M fee vs €150M market value), a direct effect of his release clause. *(High confidence — single verified transfer record)*
3. **Chelsea's median transfer overpay rose from 28% to 39%** after the June 2022 ownership change, driven disproportionately by high-multiple deals for very young, low-valuation players — consistent with the publicly reported long-contract amortization strategy the Premier League later moved to restrict. *(Moderate confidence, n=93 across two eras)*
4. **Brentford, not Brighton, is the Premier League's most efficient trading club** by return on transfer fees (4.02x vs 0.56x) — despite Brighton's stronger reputation for "smart" recruitment. *(Low–Moderate confidence — modest sample sizes, n=12 and n=17)*

## Scope

**Premier League only, V1.** No club financial data (revenue, wages, debt, profit) is used or estimated anywhere — only transfer fees, market valuations, and player metadata, all sourced directly from the dataset. Other major leagues may be added later as a separate, clearly documented extension.

## Data source

[Football Data from Transfermarkt](https://www.kaggle.com/datasets/davidcariboo/player-scores) (David Cariboo, Kaggle) — `clubs`, `players`, `transfers`, `player_valuations` tables, covering 2002–2027.

## Tech stack

Python, Pandas, NumPy, Plotly, Streamlit. No database, external API, or production backend — CSVs loaded and aggregated via `utils.py`, styled via `styles.py`.

## Project structure

```
soccernomics/
├── app.py                          # Landing page
├── pages/
│   ├── 1_Overview.py               # KPIs, spending trend, top spenders, trading efficiency, spotlight
│   ├── 2_Transfers.py              # Searchable transfer table, overpay/bargain analysis
│   ├── 3_Player_Market_Value.py    # Age/position value curves, player search
│   └── 4_Insights.py               # Confidence-tagged findings ("Season Conclusions" style)
├── styles.py                       # Shared design tokens, CSS, card/badge components
├── utils.py                        # Data loading + PL-scoped aggregate query functions
├── notebooks/soccernomics_analysis.ipynb   # Full EDA behind the findings above
├── tests/test_utils.py             # Unit tests for the aggregate functions
└── data/raw/                       # clubs.csv, players.csv, transfers.csv, player_valuations.csv
```

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```