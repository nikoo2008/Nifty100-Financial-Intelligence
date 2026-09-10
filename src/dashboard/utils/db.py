"""Cached, read-only access to the dashboard data source."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def _read(query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(query, connection, params=params)


def _sector(name: Any, ticker: Any) -> str:
    text = f"{name} {ticker}".lower()
    groups = {
        "Financials": ("bank", "finance", "insurance", "financial"),
        "IT": ("tech", "software", "infosys", "tcs", "wipro", "hcl"),
        "FMCG": (
            "consumer",
            "foods",
            "beverage",
            "paint",
            "hindustan",
            "dabur",
            "marico",
        ),
        "Energy": ("energy", "oil", "gas", "power", "petroleum"),
        "Healthcare": (
            "pharma",
            "hospital",
            "health",
            "dr reddy",
            "cipla",
            "sun pharma",
        ),
        "Automobiles": ("motor", "auto", "tata motors", "mahindra", "eicher"),
        "Metals": ("steel", "metal", "vedanta", "jsw"),
        "Telecom": ("telecom", "bharti", "airtel"),
        "Cement": ("cement", "ultratech"),
        "Industrials": ("engineer", "industrial", "defence", "larsen", "abb"),
    }
    for group, terms in groups.items():
        if any(term in text for term in terms):
            return group
    return "Diversified"


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    frame = _read("SELECT * FROM companies ORDER BY company_name")
    if not frame.empty:
        frame["sector"] = [_sector(n, t) for n, t in zip(frame.company_name, frame.id)]
        frame["broad_sector"] = frame["sector"]
    return frame


@st.cache_data(ttl=600)
def get_ratios(ticker: str | None = None, year: int | None = None) -> pd.DataFrame:
    query = "SELECT * FROM financial_ratios"
    clauses: list[str] = []
    params: list[Any] = []
    if ticker:
        clauses.append("company_id = ?")
        params.append(ticker)
    if year is not None:
        clauses.append("year = ?")
        params.append(year)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    return _read(query + " ORDER BY company_id, year", tuple(params))


@st.cache_data(ttl=600)
def get_pl(ticker: str | None = None) -> pd.DataFrame:
    return _read(
        "SELECT * FROM profitandloss"
        + (" WHERE company_id = ?" if ticker else "")
        + " ORDER BY year",
        (ticker,) if ticker else (),
    )


@st.cache_data(ttl=600)
def get_bs(ticker: str | None = None) -> pd.DataFrame:
    return _read(
        "SELECT * FROM balancesheet"
        + (" WHERE company_id = ?" if ticker else "")
        + " ORDER BY year",
        (ticker,) if ticker else (),
    )


@st.cache_data(ttl=600)
def get_cf(ticker: str | None = None) -> pd.DataFrame:
    return _read(
        "SELECT * FROM cashflow"
        + (" WHERE company_id = ?" if ticker else "")
        + " ORDER BY year",
        (ticker,) if ticker else (),
    )


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    companies = get_companies()
    return (
        companies.groupby("sector", as_index=False)
        .size()
        .rename(columns={"size": "company_count"})
        if not companies.empty
        else pd.DataFrame(columns=["sector", "company_count"])
    )


@st.cache_data(ttl=600)
def get_peers(group_name: str | None = None) -> pd.DataFrame:
    query = "SELECT * FROM peer_percentiles"
    params: tuple[Any, ...] = ()
    if group_name:
        query += " WHERE peer_group = ?"
        params = (group_name,)
    return _read(query, params)


@st.cache_data(ttl=600)
def get_valuation(ticker: str | None = None) -> pd.DataFrame:
    path = ROOT / "output" / "valuation_summary.xlsx"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_excel(path)
    return (
        frame[frame.company_id == ticker] if ticker and "company_id" in frame else frame
    )


def latest(frame: pd.DataFrame, ticker: str | None = None) -> pd.DataFrame:
    if frame.empty:
        return frame
    if ticker:
        frame = frame[frame.company_id == ticker]
    return frame.sort_values("year").drop_duplicates("company_id", keep="last")


def metric_value(value: Any, suffix: str = "") -> str:
    return "N/A" if value is None or pd.isna(value) else f"{float(value):,.2f}{suffix}"
