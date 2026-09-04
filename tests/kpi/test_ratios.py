"""Unit tests for Sprint 2 ratio, CAGR, and cash-flow KPIs."""

import pandas as pd

from src.analytics.cagr import calculate_cagr, cagr_for_periods
from src.analytics.cashflow_kpis import calculate_cashflow_kpis
from src.analytics.ratios import calculate_ratios, classify_capital_allocation, safe_ratio


def _pnl(**values):
    return pd.Series({"sales": 1000, "operating_profit": 200, "net_profit": 100, "interest": 20, **values})


def _bs(**values):
    return pd.Series({"equity_capital": 100, "reserves": 400, "borrowings": 100, "total_assets": 1000, **values})


def test_safe_ratio(): assert safe_ratio(10, 2) == (5.0, None)
def test_safe_ratio_zero(): assert safe_ratio(10, 0)[1] == "zero_denominator"
def test_cagr(): assert round(calculate_cagr(100, 121, 2)[0], 6) == 10.0
def test_cagr_non_positive_base(): assert calculate_cagr(0, 10, 2)[1] == "non_positive_base"
def test_cagr_non_positive_end(): assert calculate_cagr(10, 0, 2)[1] == "non_positive_end"
def test_cagr_zero_years(): assert calculate_cagr(10, 11, 0)[1] == "zero_years"
def test_cagr_invalid(): assert calculate_cagr("x", 11, 2)[1] == "invalid_value"
def test_cagr_missing(): assert calculate_cagr(None, 11, 2)[1] == "missing_value"
def test_cagr_history():
    history = pd.DataFrame({"year": [2021, 2022, 2023, 2024], "sales": [100, 110, 121, 133.1]})
    assert round(cagr_for_periods(history, "sales")["cagr_3y"] or 0, 6) == 10
def test_operating_margin(): assert calculate_ratios(_pnl(), _bs())["operating_margin_pct"] == 20
def test_net_margin(): assert calculate_ratios(_pnl(), _bs())["net_margin_pct"] == 10
def test_debt_to_equity(): assert calculate_ratios(_pnl(), _bs())["debt_to_equity"] == 0.2
def test_roe(): assert calculate_ratios(_pnl(), _bs())["return_on_equity_pct"] == 20
def test_roce(): assert round(calculate_ratios(_pnl(), _bs())["return_on_capital_employed_pct"], 6) == round(200 / 600 * 100, 6)
def test_financial_carveout(): assert calculate_ratios(_pnl(company_id="HDFCBANK"), _bs())["financial_carveout"] == "bank_financial"
def test_cashflow_kpis():
    result = calculate_cashflow_kpis(_pnl(), pd.Series({"operating_activity": 150, "investing_activity": -50, "financing_activity": -20}))
    assert result["free_cash_flow"] == 100 and result["cash_conversion"] == 1.5
def test_cashflow_zero_denominator():
    assert calculate_cashflow_kpis(_pnl(net_profit=0), pd.Series({"operating_activity": 10}))["cashflow_edge_case"] == "zero_denominator"
def test_pattern_financial(): assert classify_capital_allocation(pd.Series({"financial_carveout": "bank_financial"})) == "financial_institution"
def test_pattern_insufficient(): assert classify_capital_allocation(pd.Series({"financial_carveout": "standard", "operating_margin_pct": None, "return_on_equity_pct": None})) == "insufficient_data"
def test_pattern_efficient():
    row = pd.Series({"financial_carveout": "standard", "operating_margin_pct": 20, "return_on_equity_pct": 20, "net_margin_pct": 10, "interest_coverage": 10, "free_cash_flow": 10, "cash_conversion": 0.5, "dividend_payout": 10, "debt_to_equity": 0.2, "asset_turnover": 2})
    assert classify_capital_allocation(row) == "deleveraging"