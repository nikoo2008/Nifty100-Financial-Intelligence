"""Sector API routes."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.common import ROOT, companies_frame, json_records, latest_ratios

router = APIRouter(tags=["sectors"])


@router.get("/sectors")
def sectors():
    """Return sector counts and latest KPI medians."""
    frame = latest_ratios().merge(
        companies_frame()[["id", "broad_sector"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )
    result = frame.groupby("broad_sector", as_index=False).agg(
        company_count=("company_id", "count"),
        median_roe=("return_on_equity_pct", "median"),
        median_de=("debt_to_equity", "median"),
    )
    valuation_path = ROOT / "output" / "valuation_summary.xlsx"
    if valuation_path.exists():
        valuation = pd.read_excel(valuation_path)
        pe = valuation.groupby("sector")["P/E"].median().rename("median_pe")
        result = result.merge(pe, left_on="broad_sector", right_index=True, how="left")
    else:
        result["median_pe"] = None
    return json_records(result)


@router.get("/sectors/{sector}/companies")
def sector_companies(sector: str):
    """Return latest KPIs for companies in a sector."""
    frame = latest_ratios().merge(
        companies_frame()[["id", "company_name", "broad_sector"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )
    requested_sector = {
        "it": "information technology",
    }.get(sector.casefold(), sector.casefold())
    if not (frame.broad_sector.str.casefold() == requested_sector).any():
        raise HTTPException(404, "Unknown sector")
    return json_records(frame[frame.broad_sector.str.casefold() == requested_sector])
