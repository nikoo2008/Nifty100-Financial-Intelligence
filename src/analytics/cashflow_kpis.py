"""Cash-flow KPI calculations using the normalized Sprint 1 columns."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _number(value: Any) -> float | None:
    try:
        return None if value is None or pd.isna(value) else float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _ratio(numerator: Any, denominator: Any) -> tuple[float | None, str | None]:
    top, bottom = _number(numerator), _number(denominator)
    if top is None or bottom is None:
        return None, "missing_value"
    if bottom == 0:
        return None, "zero_denominator"
    return top / bottom, None


def calculate_cashflow_kpis(pnl: pd.Series, cashflow: pd.Series | None = None) -> dict[str, float | None | str]:
    """Return cash conversion, FCF, and cash-flow margin KPIs for one year."""
    flow = cashflow if cashflow is not None else pd.Series(dtype=object)
    operating = _number(flow.get("operating_activity"))
    investing = _number(flow.get("investing_activity"))
    financing = _number(flow.get("financing_activity"))
    net_profit = _number(pnl.get("net_profit"))
    sales = _number(pnl.get("sales"))
    free_cash_flow = None if operating is None or investing is None else operating + investing
    cash_conversion, conversion_flag = _ratio(operating, net_profit)
    ocf_margin, margin_flag = _ratio(operating, sales)
    return {
        "operating_cash_flow": operating,
        "free_cash_flow": free_cash_flow,
        "financing_cash_flow": financing,
        "cash_conversion": cash_conversion,
        "operating_cash_flow_margin_pct": None if ocf_margin is None else ocf_margin * 100.0,
        "cashflow_edge_case": conversion_flag or margin_flag,
    }


__all__ = ["calculate_cashflow_kpis"]