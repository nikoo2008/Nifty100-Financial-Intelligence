"""Reusable financial ratio engine for the normalized Nifty100 data."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.cagr import cagr_for_periods
from src.analytics.cashflow_kpis import calculate_cashflow_kpis

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDGE_LOG = PROJECT_ROOT / "output" / "ratio_edge_cases.log"
PERIODS = (3, 5, 10)
FINANCIAL_TICKERS = {
    "BAJFINANCE",
    "BAJAJFINSV",
    "HDFCBANK",
    "ICICIBANK",
    "INDUSINDBK",
    "KOTAKBANK",
    "SBILIFE",
    "SBIN",
}


def _source_percent(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    match = (
        pd.Series([str(value)]).str.extract(r"(-?\d+(?:\.\d+)?)%", expand=False).iloc[0]
    )
    return None if pd.isna(match) else float(match)


def is_financial_company(company_id: Any, company_name: Any = None) -> bool:
    text = str(company_id or "").upper()
    name = str(company_name or "").lower()
    return text in FINANCIAL_TICKERS or any(
        word in name for word in ("bank", "finance", "financial", "life insurance")
    )


def safe_ratio(numerator: Any, denominator: Any) -> tuple[float | None, str | None]:
    try:
        top, bottom = float(numerator), float(denominator)
    except (TypeError, ValueError):
        return None, "missing_value"
    if not math.isfinite(top) or not math.isfinite(bottom):
        return None, "invalid_value"
    if bottom == 0:
        return None, "zero_denominator"
    return top / bottom, None


def _value(row: pd.Series, column: str) -> float | None:
    try:
        value = row.get(column)
        return (
            None
            if value is None or pd.isna(value)
            else float(str(value).replace(",", "").strip())
        )
    except (TypeError, ValueError):
        return None


def calculate_ratios(
    pnl: pd.Series,
    balance: pd.Series | None = None,
    cashflow: pd.Series | None = None,
    company_name: Any = None,
) -> dict[str, Any]:
    """Calculate all ratios supported by the available source columns."""
    bs = balance if balance is not None else pd.Series(dtype=object)
    sales, operating_profit, net_profit = (
        _value(pnl, "sales"),
        _value(pnl, "operating_profit"),
        _value(pnl, "net_profit"),
    )
    equity = (_value(bs, "equity_capital") or 0) + (_value(bs, "reserves") or 0)
    borrowings, assets, interest = (
        _value(bs, "borrowings"),
        _value(bs, "total_assets"),
        _value(pnl, "interest"),
    )
    ebit = operating_profit
    ratios: dict[str, Any] = {}
    calculations = {
        "operating_margin_pct": (operating_profit, sales, 100.0),
        "net_margin_pct": (net_profit, sales, 100.0),
        "debt_to_equity": (borrowings, equity, 1.0),
        "return_on_equity_pct": (net_profit, equity, 100.0),
        "return_on_capital_employed_pct": (ebit, equity + (borrowings or 0), 100.0),
        "return_on_assets_pct": (net_profit, assets, 100.0),
        "asset_turnover": (sales, assets, 1.0),
        "fixed_asset_turnover": (sales, _value(bs, "fixed_assets"), 1.0),
        "liabilities_to_assets": (_value(bs, "total_liabilities"), assets, 1.0),
        "interest_coverage": (ebit, interest, 1.0),
    }
    flags: list[str] = []
    for name, (top, bottom, multiplier) in calculations.items():
        value, flag = safe_ratio(top, bottom)
        ratios[name] = None if value is None else value * multiplier
        if flag:
            flags.append(f"{name}:{flag}")
    financial_carveout = is_financial_company(pnl.get("company_id"), company_name)
    if financial_carveout:
        ratios["return_on_capital_employed_pct"] = None
        ratios["financial_carveout"] = "bank_financial"
        ratios["carveout_note"] = (
            "ROCE omitted: debt is operating funding for financial institutions."
        )
    else:
        ratios["financial_carveout"] = "standard"
        ratios["carveout_note"] = None
    ratios.update(calculate_cashflow_kpis(pnl, cashflow))
    if ratios.get("cashflow_edge_case"):
        flags.append(f"cashflow:{ratios['cashflow_edge_case']}")
    ratios["ratio_edge_case"] = ";".join(flags) or None
    return ratios


def classify_capital_allocation(row: pd.Series) -> str:
    """Classify a company using only calculated KPI evidence (eight stable labels)."""
    if row.get("financial_carveout") == "bank_financial":
        return "financial_institution"
    if pd.isna(row.get("operating_margin_pct")) or pd.isna(
        row.get("return_on_equity_pct")
    ):
        return "insufficient_data"
    if (
        row.get("net_margin_pct", 0) < 0
        or row.get("interest_coverage", 0) is not None
        and row.get("interest_coverage", 0) < 1
    ):
        return "distressed"
    if (row.get("free_cash_flow") or 0) < 0 and (row.get("cagr_5y") or 0) > 10:
        return "growth_investor"
    if (row.get("free_cash_flow") or 0) > 0 and (row.get("cash_conversion") or 0) > 1:
        return "cash_compounder"
    if (row.get("dividend_payout") or 0) > 25:
        return "capital_returner"
    if (row.get("debt_to_equity") or 0) < 0.25:
        return "deleveraging"
    if (row.get("asset_turnover") or 0) > 1:
        return "capital_efficient"
    return "capital_intensive"


def build_financial_ratios(
    datasets: dict[str, pd.DataFrame], edge_log: Path = EDGE_LOG
) -> pd.DataFrame:
    """Build annual ratio rows from the actual normalized dataset columns."""
    pnl = datasets["profitandloss"].copy()
    bs = datasets["balancesheet"].copy()
    cf = datasets["cashflow"].copy()
    for frame in (pnl, bs, cf):
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    bs = bs.sort_values("id").drop_duplicates(["company_id", "year"], keep="last")
    cf = cf.sort_values("id").drop_duplicates(["company_id", "year"], keep="last")
    rows: list[dict[str, Any]] = []
    edge_lines: list[str] = []
    company_names = (
        datasets.get("companies", pd.DataFrame())
        .set_index("id")["company_name"]
        .to_dict()
        if "companies" in datasets
        else {}
    )
    analysis = datasets.get("analysis", pd.DataFrame())
    for _, p_row in pnl.iterrows():
        key = (p_row.get("company_id"), p_row.get("year"))
        b_match = bs[(bs.company_id == key[0]) & (bs.year == key[1])]
        c_match = cf[(cf.company_id == key[0]) & (cf.year == key[1])]
        metrics = calculate_ratios(
            p_row,
            None if b_match.empty else b_match.iloc[-1],
            None if c_match.empty else c_match.iloc[-1],
            company_names.get(key[0]),
        )
        metrics["dividend_payout"] = _value(p_row, "dividend_payout")
        source = analysis[analysis.company_id == key[0]]
        source_roe = (
            None if source.empty else _source_percent(source.iloc[-1].get("roe"))
        )
        metrics["source_roe_pct"] = source_roe
        metrics["roe_source_difference_pct"] = (
            None
            if source_roe is None or metrics["return_on_equity_pct"] is None
            else metrics["return_on_equity_pct"] - source_roe
        )
        metrics["roe_source_crosscheck"] = (
            "matched"
            if metrics["roe_source_difference_pct"] is not None
            and abs(metrics["roe_source_difference_pct"]) <= 5
            else ("review" if source_roe is not None else "unavailable")
        )
        source_roce = (
            None if source.empty else _source_percent(source.iloc[-1].get("roce"))
        )
        metrics["source_roce_pct"] = source_roce
        metrics["roce_source_difference_pct"] = (
            None
            if source_roce is None or metrics["return_on_capital_employed_pct"] is None
            else metrics["return_on_capital_employed_pct"] - source_roce
        )
        metrics["roce_source_crosscheck"] = (
            "matched"
            if metrics["roce_source_difference_pct"] is not None
            and abs(metrics["roce_source_difference_pct"]) <= 5
            else ("review" if source_roce is not None else "unavailable")
        )
        cagr = cagr_for_periods(pnl[pnl.company_id == key[0]], "sales", PERIODS)
        row = {
            "company_id": key[0],
            "year": None if pd.isna(key[1]) else int(key[1]),
            **metrics,
            **cagr,
        }
        row["capital_allocation_pattern"] = None
        rows.append(row)
        if metrics.get("ratio_edge_case") or cagr.get("cagr_edge_case"):
            edge_lines.append(
                f"{key[0]} {key[1]} ratio={metrics.get('ratio_edge_case')} cagr={cagr.get('cagr_edge_case')}"
            )
    edge_log.parent.mkdir(parents=True, exist_ok=True)
    edge_log.write_text(
        "\n".join(edge_lines) + ("\n" if edge_lines else ""), encoding="utf-8"
    )
    result = pd.DataFrame(rows)
    latest = result.sort_values(
        ["company_id", "year"], na_position="first"
    ).drop_duplicates("company_id", keep="last")
    patterns = (
        latest.set_index("company_id")
        .apply(classify_capital_allocation, axis=1)
        .to_dict()
    )
    result["capital_allocation_pattern"] = result["company_id"].map(patterns)
    return result


__all__ = ["build_financial_ratios", "calculate_ratios", "safe_ratio"]


def main() -> None:
    from src.etl.loader import load_all_core_datasets

    result = build_financial_ratios(load_all_core_datasets())
    print(result.describe(include="all").transpose().to_string())


if __name__ == "__main__":
    main()
