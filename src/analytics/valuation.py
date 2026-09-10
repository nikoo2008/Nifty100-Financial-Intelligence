"""Valuation summary and sector-relative flags for the dashboard."""
from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT = ROOT / "output"


def _market_caps(companies: pd.DataFrame) -> pd.DataFrame:
    for path in (ROOT / "data" / "raw" / "market_cap.xlsx", ROOT / "data" / "market_cap.xlsx"):
        if path.exists():
            frame = pd.read_excel(path)
            ticker = next((c for c in frame.columns if str(c).lower() in {"company_id", "ticker", "symbol", "id"}), None)
            value = next((c for c in frame.columns if "market" in str(c).lower() and "cap" in str(c).lower()), None)
            if ticker and value:
                return frame.rename(columns={ticker: "company_id", value: "market_cap_crore"})[["company_id", "market_cap_crore"]]
    return pd.DataFrame({"company_id": companies.company_id, "market_cap_crore": pd.NA})


def build_valuation_summary(database_path: Path = DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(database_path) as connection:
        companies = pd.read_sql_query("SELECT id AS company_id, company_name FROM companies", connection)
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", connection)
        pnl = pd.read_sql_query("SELECT * FROM profitandloss", connection)
        bs = pd.read_sql_query("SELECT * FROM balancesheet", connection)
    companies["sector"] = companies.apply(lambda row: "Financials" if any(w in f"{row.company_name} {row.company_id}".lower() for w in ("bank", "finance", "insurance")) else "Diversified", axis=1)
    latest = ratios.sort_values("year").drop_duplicates("company_id", keep="last")
    latest_pnl = pnl.sort_values("year").drop_duplicates("company_id", keep="last")
    latest_bs = bs.sort_values("year").drop_duplicates("company_id", keep="last")
    frame = companies.merge(latest, on="company_id", how="left", suffixes=("", "_ratio")).merge(latest_pnl[["company_id", "net_profit", "operating_profit"]], on="company_id", how="left").merge(latest_bs[["company_id", "borrowings", "equity_capital", "reserves"]], on="company_id", how="left").merge(_market_caps(companies), on="company_id", how="left")
    frame["market_cap_crore"] = pd.to_numeric(frame.market_cap_crore, errors="coerce")
    book_equity = pd.to_numeric(frame.equity_capital, errors="coerce").fillna(0) + pd.to_numeric(frame.reserves, errors="coerce").fillna(0)
    frame["market_cap_crore"] = frame.market_cap_crore.fillna(book_equity)
    frame["P/E"] = frame.market_cap_crore / pd.to_numeric(frame.net_profit, errors="coerce").replace(0, pd.NA)
    frame["P/B"] = frame.market_cap_crore / book_equity.replace(0, pd.NA)
    frame["EV/EBITDA"] = (frame.market_cap_crore + pd.to_numeric(frame.borrowings, errors="coerce").fillna(0)) / pd.to_numeric(frame.operating_profit, errors="coerce").replace(0, pd.NA)
    frame["FCF_yield_pct"] = pd.to_numeric(frame.free_cash_flow, errors="coerce") / frame.market_cap_crore.replace(0, pd.NA) * 100
    historical = ratios.merge(pnl[["company_id", "year", "net_profit"]], on=["company_id", "year"], how="left").merge(frame[["company_id", "market_cap_crore"]], on="company_id", how="left")
    historical["pe"] = historical.market_cap_crore / pd.to_numeric(historical.net_profit, errors="coerce").replace(0, pd.NA)
    medians = historical.sort_values("year").groupby("company_id").tail(5).groupby("company_id").pe.median().rename("5yr_median_PE")
    frame = frame.join(medians, on="company_id")
    sector_medians = frame.groupby("sector")["P/E"].transform("median")
    frame["PE_vs_sector_median_pct"] = (frame["P/E"] / sector_medians - 1) * 100
    frame["flag"] = "Fair"
    frame.loc[frame["P/E"] > sector_medians * 1.5, "flag"] = "Caution"
    frame.loc[frame["P/E"] < sector_medians * 0.7, "flag"] = "Discount"
    columns = ["company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA", "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"]
    return frame[columns]


def write_valuation_outputs(summary: pd.DataFrame | None = None) -> pd.DataFrame:
    summary = build_valuation_summary() if summary is None else summary
    OUTPUT.mkdir(exist_ok=True)
    summary.to_excel(OUTPUT / "valuation_summary.xlsx", index=False)
    summary[summary.flag.isin(["Caution", "Discount"])].to_csv(OUTPUT / "valuation_flags.csv", index=False)
    return summary


if __name__ == "__main__":
    result = write_valuation_outputs()
    print(f"Wrote {len(result)} valuation rows to {OUTPUT / 'valuation_summary.xlsx'}")
