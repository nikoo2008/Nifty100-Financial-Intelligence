"""CAGR calculations with explicit, auditable edge-case flags."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


EDGE_CASE_FLAGS = (
    "missing_value",
    "invalid_value",
    "non_positive_base",
    "non_positive_end",
    "insufficient_history",
    "zero_years",
)


def _number(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        number = float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def calculate_cagr(start_value: Any, end_value: Any, years: int | float) -> tuple[float | None, str | None]:
    """Return CAGR as a percentage and one reason when it is undefined."""
    start = _number(start_value)
    end = _number(end_value)
    if start is None or end is None:
        return None, "missing_value" if start_value is None or end_value is None else "invalid_value"
    if start <= 0:
        return None, "non_positive_base"
    if end <= 0:
        return None, "non_positive_end"
    try:
        period = float(years)
    except (TypeError, ValueError):
        return None, "insufficient_history"
    if not math.isfinite(period) or period < 1:
        return None, "zero_years"
    return ((end / start) ** (1.0 / period) - 1.0) * 100.0, None


def cagr_for_periods(
    history: pd.DataFrame,
    value_column: str,
    periods: tuple[int, ...] = (3, 5, 10),
) -> dict[str, float | None | str]:
    """Calculate period CAGRs from annual records, preserving missing history."""
    result: dict[str, float | None | str] = {}
    if history.empty or "year" not in history or value_column not in history:
        return {f"cagr_{period}y": None for period in periods} | {"cagr_edge_case": "insufficient_history"}
    frame = history[["year", value_column]].copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna().sort_values("year").drop_duplicates("year", keep="last")
    result["cagr_edge_case"] = None
    latest_year = int(frame["year"].max()) if not frame.empty else None
    latest = None if frame.empty else frame.iloc[-1][value_column]
    for period in periods:
        start = frame[frame["year"] == latest_year - period][value_column] if latest_year is not None else pd.Series(dtype=float)
        value, reason = calculate_cagr(None if start.empty else start.iloc[-1], latest, period)
        result[f"cagr_{period}y"] = value
        if reason and result["cagr_edge_case"] is None:
            result["cagr_edge_case"] = reason
    if all(result[f"cagr_{period}y"] is None for period in periods) and result["cagr_edge_case"] is None:
        result["cagr_edge_case"] = "insufficient_history"
    return result


__all__ = ["EDGE_CASE_FLAGS", "calculate_cagr", "cagr_for_periods"]