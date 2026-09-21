"""
Unit tests for Soccernomics utility functions.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    calculate_contract_amortisation,
    disposal_profit_loss,
    calculate_value_gap_and_premium,
    player_peak_vs_current,
    calculate_club_psr_status,
    load_club_financial_statement,
    format_eur_m,
)


def test_calculate_contract_amortisation():
    res = calculate_contract_amortisation(fee_eur=100_000_000, contract_years=5, weekly_wage_gbp=200_000, gbp_to_eur=1.0)
    assert res["annual_amortisation_eur"] == 20_000_000
    assert res["annual_wage_eur"] == 200_000 * 52
    assert res["annual_pl_hit_eur"] == 20_000_000 + (200_000 * 52)
    
    sched = res["schedule"]
    assert len(sched) == 6  # Year 0 to 5
    assert sched.iloc[0]["book_value_eur"] == 100_000_000
    assert sched.iloc[5]["book_value_eur"] == 0.0


def test_disposal_profit_loss():
    # £100M fee, 5 year contract -> £20M/yr amortisation. Sold in Year 3 at £70M
    # Book value at Year 3 = 100 * (1 - 3/5) = 40M. Gain = 70M - 40M = 30M profit.
    disp = disposal_profit_loss(fee_eur=100_000_000, contract_years=5, sale_year=3, sale_fee_eur=70_000_000)
    assert disp["book_value_at_sale"] == 40_000_000
    assert disp["accounting_gain_loss"] == 30_000_000
    assert disp["is_profit"] is True

    # Sold at £30M in Year 3 -> Loss of 10M
    disp_loss = disposal_profit_loss(fee_eur=100_000_000, contract_years=5, sale_year=3, sale_fee_eur=30_000_000)
    assert disp_loss["accounting_gain_loss"] == -10_000_000
    assert disp_loss["is_profit"] is False


def test_calculate_value_gap_and_premium():
    df = pd.DataFrame([
        {"transfer_fee": 60_000_000, "market_value_in_eur": 150_000_000},  # Haaland bargain
        {"transfer_fee": 120_000_000, "market_value_in_eur": 60_000_000},  # Overpay
        {"transfer_fee": 50_000_000, "market_value_in_eur": 50_000_000},   # Fair value
    ])
    res = calculate_value_gap_and_premium(df)
    assert res.iloc[0]["value_gap"] == 90_000_000
    assert res.iloc[0]["pricing_tier"] == "Discount (<-15%)"
    assert res.iloc[1]["pricing_tier"] == "Premium (>15%)"
    assert res.iloc[2]["pricing_tier"] == "Fair Value (±15%)"


def test_player_peak_vs_current():
    peak = player_peak_vs_current(current_val=80_000_000, peak_val=100_000_000)
    assert peak["is_at_peak"] is False
    assert peak["pct_delta"] == -20.0
    assert "20.0% below peak" in peak["status"]

    at_peak = player_peak_vs_current(current_val=150_000_000, peak_val=150_000_000)
    assert at_peak["is_at_peak"] is True
    assert at_peak["status"] == "At Career Peak"


def test_calculate_club_psr_status():
    fin_row = {
        "wage_to_revenue_pct": 65.0,
        "operating_result_gbp": 20_000_000,
        "net_debt_gbp": 50_000_000,
        "season": "2024/25"
    }
    status = calculate_club_psr_status(fin_row)
    assert status["psr_status"] == "PSR Compliant"

    risky_row = {
        "wage_to_revenue_pct": 89.0,
        "operating_result_gbp": -80_000_000,
        "net_debt_gbp": 500_000_000,
        "season": "2024/25"
    }
    risky_status = calculate_club_psr_status(risky_row)
    assert risky_status["psr_status"] == "At Risk of Breach"


def test_format_eur_m():
    assert format_eur_m(150_000_000) == "€150.0M"
    assert format_eur_m(500_000) == "€500.0K"
    assert format_eur_m(None) == "€0"


