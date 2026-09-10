"""Screener API route."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.common import companies_frame, json_records, latest_ratios

router = APIRouter(tags=["screener"])


@router.get("/screener")
def screener(
    min_roe: float | None = None,
    max_de: float | None = None,
    min_fcf: float | None = None,
    sector: str | None = None,
    min_rev_cagr_5yr: float | None = None,
    min_pat_cagr_5yr: float | None = None,
    max_pe: float | None = None,
):
    """Filter latest company KPIs and return ranked results."""
    for value in [min_roe, max_de, min_fcf, min_rev_cagr_5yr, min_pat_cagr_5yr, max_pe]:
        if value is not None and not -1_000_000 <= value <= 1_000_000:
            raise HTTPException(400, "Invalid parameter value")
    frame = latest_ratios().merge(
        companies_frame()[["id", "company_name", "broad_sector"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )
    if sector:
        frame = frame[frame.broad_sector.str.casefold() == sector.casefold()]
    filters = [
        ("return_on_equity_pct", min_roe, ">="),
        ("debt_to_equity", max_de, "<="),
        ("free_cash_flow", min_fcf, ">="),
        ("cagr_5y", min_rev_cagr_5yr, ">="),
    ]
    for column, value, operator in filters:
        if value is not None:
            frame = (
                frame[pd.to_numeric(frame[column], errors="coerce") >= value]
                if operator == ">="
                else frame[pd.to_numeric(frame[column], errors="coerce") <= value]
            )
    frame["quality_score"] = (
        pd.to_numeric(frame.return_on_equity_pct, errors="coerce").rank(pct=True) * 100
    )
    return json_records(frame.sort_values("quality_score", ascending=False))
