"""Shared read-only API database helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"


def read_table(
    table: str, where: str = "", params: tuple[Any, ...] = ()
) -> pd.DataFrame:
    """Read a validated SQLite table into a DataFrame."""
    allowed = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "peer_percentiles",
        "documents",
        "prosandcons",
    }
    if table not in allowed:
        raise ValueError("Unsupported table")
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            f'SELECT * FROM "{table}" {where}', connection, params=params
        )


def json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-safe records."""
    if frame.empty:
        return []
    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")


def sector_for(name: Any, ticker: Any) -> str:
    """Derive the project broad sector from source company metadata."""
    text = f"{name} {ticker}".lower()
    groups = {
        "Financials": ("bank", "finance", "insurance"),
        "IT": ("tech", "software", "infosys", "tcs", "wipro", "hcl"),
        "FMCG": ("consumer", "beverage", "foods", "paint", "dabur", "marico"),
        "Energy": ("energy", "oil", "gas", "power", "petroleum"),
        "Healthcare": ("pharma", "hospital", "health", "cipla", "sun pharma"),
        "Automobiles": ("motor", "auto", "mahindra", "eicher"),
        "Metals": ("steel", "metal", "vedanta", "jsw"),
        "Telecom": ("telecom", "bharti", "airtel"),
        "Cement": ("cement", "ultratech"),
        "Industrials": ("industrial", "defence", "larsen", "abb"),
    }
    return next(
        (
            sector
            for sector, terms in groups.items()
            if any(term in text for term in terms)
        ),
        "Diversified",
    )


def companies_frame() -> pd.DataFrame:
    """Return companies enriched with broad sectors."""
    frame = read_table("companies")
    frame["broad_sector"] = [
        sector_for(n, t) for n, t in zip(frame.company_name, frame.id)
    ]
    frame["sub_sector"] = frame.broad_sector
    return frame


def latest_ratios() -> pd.DataFrame:
    """Return one latest ratio row per company."""
    return (
        read_table("financial_ratios")
        .sort_values("year")
        .drop_duplicates("company_id", keep="last")
    )


def filtered_years(
    frame: pd.DataFrame, from_year: str | None, to_year: str | None
) -> pd.DataFrame:
    """Filter financial history by optional YYYY-MM or year strings."""
    result = frame.copy()
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    if from_year:
        result = result[result.year >= int(str(from_year)[:4])]
    if to_year:
        result = result[result.year <= int(str(to_year)[:4])]
    return result
