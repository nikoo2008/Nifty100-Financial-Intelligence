"""Annual report document API route."""

import requests
from fastapi import APIRouter, HTTPException

from src.api.common import json_records, read_table

router = APIRouter(tags=["documents"])


@router.get("/companies/{ticker}/documents")
def documents(ticker: str):
    """Return annual report links and URL validity flags."""
    frame = read_table(
        "documents", "WHERE company_id = ? ORDER BY year DESC", (ticker,)
    )
    if frame.empty:
        raise HTTPException(404, "Documents not found")
    frame["is_url_valid"] = frame.annual_report.fillna("").map(
        lambda url: bool(url) and _valid_url(str(url))
    )
    return json_records(frame)


def _valid_url(url: str) -> bool:
    """Check an annual report URL with a short network timeout."""
    try:
        return requests.head(url, timeout=3, allow_redirects=True).status_code < 400
    except requests.RequestException:
        return False
