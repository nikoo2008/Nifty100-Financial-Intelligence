"""Cash-flow KPI calculations using the normalized Sprint 1 columns."""

from __future__ import annotations

import sqlite3
from pathlib import Path
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


def _label_cfo_quality(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "N/A"
    if score > 1.0:
        return "High Quality"
    if score >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def _label_capex(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if value < 3:
        return "Asset Light"
    if value <= 8:
        return "Moderate"
    return "Capital Intensive"


def build_cashflow_intelligence(
    pnl: pd.DataFrame,
    cashflow: pd.DataFrame,
    balancesheet: pd.DataFrame,
    companies: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build one latest-year cash-flow intelligence row per source company."""
    rows: list[dict[str, Any]] = []
    distress_rows: list[dict[str, Any]] = []
    for company_id in companies["id"].astype(str):
        pl = pnl[pnl.company_id.astype(str) == company_id].copy().sort_values("year")
        cf = cashflow[cashflow.company_id.astype(str) == company_id].copy().sort_values("year")
        bs = balancesheet[balancesheet.company_id.astype(str) == company_id].copy().sort_values("year")
        merged = pl[["year", "sales", "net_profit"]].merge(cf, on=["year"], how="left")
        for column in ["sales", "net_profit", "operating_activity", "investing_activity", "financing_activity"]:
            merged[column] = pd.to_numeric(merged[column], errors="coerce")
        merged["cfo_pat"] = merged.operating_activity / merged.net_profit.replace(0, pd.NA)
        score = merged.tail(5)["cfo_pat"].mean()
        latest = merged.dropna(subset=["year"]).tail(1)
        latest_row = latest.iloc[0] if not latest.empty else pd.Series(dtype=object)
        capex = None
        if not latest.empty and pd.notna(latest_row.sales) and latest_row.sales:
            capex = abs(float(latest_row.investing_activity or 0)) / float(latest_row.sales) * 100
        fcf = merged.operating_activity + merged.investing_activity
        fcf_cagr = None
        if len(fcf.dropna()) >= 2:
            start, end = float(fcf.dropna().iloc[0]), float(fcf.dropna().iloc[-1])
            years = max(int(merged.year.dropna().iloc[-1] - merged.year.dropna().iloc[0]), 1)
            if start > 0 and end > 0:
                fcf_cagr = ((end / start) ** (1 / years) - 1) * 100
        fcf_conversion = None if latest.empty or not latest_row.net_profit else float((latest_row.operating_activity + latest_row.investing_activity) / latest_row.net_profit * 100)
        distress = bool(not latest.empty and latest_row.operating_activity < 0 and latest_row.financing_activity > 0)
        debt = pd.to_numeric(bs.borrowings, errors="coerce")
        deleveraging = bool(len(debt.dropna()) >= 2 and debt.dropna().iloc[-1] < debt.dropna().iloc[-2] and not latest.empty and latest_row.financing_activity < 0)
        sector = "Financials" if any(word in f"{company_id} {companies.loc[companies.id.astype(str) == company_id, 'company_name'].iloc[0]}".lower() for word in ("bank", "finance", "insurance")) else "Diversified"
        row = {"company_id": company_id, "sector": sector, "cfo_quality_score": score, "cfo_quality_label": _label_cfo_quality(score), "capex_intensity_pct": capex, "capex_label": _label_capex(capex), "fcf_cagr_5yr": fcf_cagr, "fcf_conversion_pct": fcf_conversion, "distress_flag": distress, "deleveraging_flag": deleveraging, "capital_allocation_label": "Distress Signal" if distress else ("Deleveraging" if deleveraging else "Cash Compounder" if score and score > 1 else "Capital Intensive" if capex and capex > 8 else "Reinvestor")}
        rows.append(row)
        if distress:
            distress_rows.append({"company_id": company_id, "cfo_value": latest_row.operating_activity, "cff_value": latest_row.financing_activity, "latest_net_profit": latest_row.net_profit})
    return pd.DataFrame(rows), pd.DataFrame(distress_rows)


def write_cashflow_outputs(database_path: Path | str = Path("nifty100.db"), output_dir: Path | str = Path("output")) -> pd.DataFrame:
    """Load the local database and write Sprint 5 cash-flow artifacts."""
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        tables = {name: pd.read_sql_query(f"SELECT * FROM {name}", connection) for name in ["companies", "profitandloss", "cashflow", "balancesheet"]}
        ratio_frame = pd.read_sql_query("SELECT * FROM financial_ratios", connection)
    result, alerts = build_cashflow_intelligence(tables["profitandloss"], tables["cashflow"], tables["balancesheet"], tables["companies"])
    pattern = ratio_frame.sort_values("year").drop_duplicates("company_id", keep="last")[["company_id", "capital_allocation_pattern"]]
    result = result.drop(columns=["capital_allocation_label"]).merge(pattern, on="company_id", how="left").rename(columns={"capital_allocation_pattern": "capital_allocation_label"})
    result.to_excel(output_dir / "cashflow_intelligence.xlsx", index=False)
    alerts.to_csv(output_dir / "distress_alerts.csv", index=False)
    return result