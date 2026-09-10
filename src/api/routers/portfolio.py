"""Portfolio statistics API route."""

import pandas as pd
from fastapi import APIRouter

from src.api.common import ROOT, json_records

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio/stats")
def portfolio_stats():
    """Return portfolio percentile statistics."""
    path = ROOT / "output" / "portfolio_stats.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    return json_records(frame.reset_index(names="metric"))
