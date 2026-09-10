"""
Nifty 100 Financial Intelligence Platform
ETL Normalisation Utilities

Day 02:
- Year normalisation
- Ticker/company ID normalisation
- Text normalisation
- Numeric value normalisation
"""

from __future__ import annotations

import math
import re
from typing import Any


def normalize_year(value: Any) -> int | None:
    """
    Convert common year/date representations into a four-digit year.

    Examples
    --------
    2024 -> 2024
    "2024" -> 2024
    "Mar 2024" -> 2024
    "Mar-24" -> 2024
    "2024-03-31" -> 2024
    "FY2024" -> 2024

    Invalid or missing values return None.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    # Handle pandas/numpy NaN without requiring pandas here.
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass

    # Integer-like values.
    if isinstance(value, int):
        return value if 1900 <= value <= 2100 else None

    if isinstance(value, float) and value.is_integer():
        year = int(value)
        return year if 1900 <= year <= 2100 else None

    text = str(value).strip()

    if not text:
        return None

    # Direct four-digit year.
    match = re.search(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)", text)

    if match:
        return int(match.group(1))

    # Two-digit financial year such as "Mar-24".
    match = re.search(r"(?<!\d)(\d{2})(?!\d)", text)

    if match:
        year = int(match.group(1))

        if 0 <= year <= 30:
            return 2000 + year

        if 31 <= year <= 99:
            return 1900 + year

    return None


def normalize_ticker(value: Any) -> str | None:
    """
    Normalise a company ticker/company ID.

    Rules:
    - Missing values become None.
    - Leading/trailing whitespace is removed.
    - Internal repeated whitespace is removed.
    - Values are converted to uppercase.
    - Common separators are standardised.
    """

    if value is None:
        return None

    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return None

    # Remove surrounding spaces and normalise whitespace.
    text = re.sub(r"\s+", "", text)

    # Standardise common separators.
    text = text.replace("-", "").replace("_", "")

    return text.upper()


def normalize_text(value: Any) -> str | None:
    """
    Normalise general text fields.

    Missing values return None.
    """

    if value is None:
        return None

    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return None

    return re.sub(r"\s+", " ", text)


def normalize_numeric(value: Any) -> float | None:
    """
    Convert a value into a numeric float.

    Handles:
    - commas
    - percentage symbols
    - currency symbols
    - whitespace

    Invalid values return None.
    """

    if value is None:
        return None

    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    # Remove common formatting characters.
    text = text.replace(",", "")
    text = text.replace("₹", "")
    text = text.replace("$", "")
    text = text.replace("%", "")
    text = text.strip()

    # Handle accounting negatives: (123.45)
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1].strip()

    try:
        return float(text)
    except ValueError:
        return None


def normalize_percentage(value: Any) -> float | None:
    """
    Normalise percentage values.

    Example:
        "23.5%" -> 23.5
        23.5 -> 23.5
    """

    return normalize_numeric(value)


def normalize_url(value: Any) -> str | None:
    """
    Normalise URL text without altering the actual destination.
    """

    text = normalize_text(value)

    if text is None:
        return None

    return text


__all__ = [
    "normalize_numeric",
    "normalize_percentage",
    "normalize_text",
    "normalize_ticker",
    "normalize_url",
    "normalize_year",
]
