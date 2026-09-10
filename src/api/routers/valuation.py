"""Valuation API route."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.common import ROOT, json_records

router = APIRouter(tags=["valuation"])


@router.get("/market-cap/{ticker}")
def market_cap(ticker: str):
    """Return available historical valuation multiples for a ticker."""
    path = ROOT / "output" / "valuation_summary.xlsx"
    if not path.exists():
        raise HTTPException(404, "Valuation data unavailable")
    frame = pd.read_excel(path)
    result = frame[frame.company_id.astype(str).str.upper() == ticker.upper()]
    if result.empty:
        raise HTTPException(404, "Ticker not found")
    return json_records(result)
