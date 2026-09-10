"""Peer comparison API routes."""

from fastapi import APIRouter, HTTPException

from src.api.common import json_records, read_table

router = APIRouter(tags=["peers"])


@router.get("/peers/{group_name}")
def peers(group_name: str):
    """Return percentile metrics for a peer group."""
    frame = read_table("peer_percentiles", "WHERE peer_group = ?", (group_name,))
    if frame.empty:
        raise HTTPException(404, "Peer group not found")
    return json_records(frame)


@router.get("/companies/{ticker}/peers/compare")
def compare_peers(ticker: str):
    """Return eight-axis benchmark radar data."""
    peers_frame = read_table("peer_percentiles", "WHERE company_id = ?", (ticker,))
    if peers_frame.empty:
        raise HTTPException(404, "Peer data not found")
    row = peers_frame.iloc[0]
    group = row.peer_group
    group_frame = read_table("peer_percentiles", "WHERE peer_group = ?", (group,))
    axes = [
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "debt_to_equity",
        "interest_coverage",
        "operating_margin_pct",
        "net_margin_pct",
        "asset_turnover",
        "cash_conversion",
    ]
    return {
        "company_id": ticker,
        "peer_group": group,
        "axes": axes,
        "company": [row.get(axis) for axis in axes],
        "peer_average": [group_frame[axis].mean() for axis in axes],
        "benchmark_company": ticker,
    }
