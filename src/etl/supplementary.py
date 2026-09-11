"""Load the direct-header supplementary workbooks supplied with the project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.etl.loader import normalize_company_id, normalize_dataframe_columns
from src.etl.normaliser import normalize_year

ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = ROOT / "data" / "raw"

SUPPLEMENTARY_DATASETS = {
    "market_cap": "market_cap.xlsx",
    "stock_prices": "stock_prices.xlsx",
    "source_financial_ratios": "financial_ratios.xlsx",
    "sectors": "sectors.xlsx",
    "peer_groups": "peer_groups.xlsx",
}


def load_supplementary_dataset(dataset_name: str) -> pd.DataFrame:
    """Read a supplementary workbook using its direct header row."""
    if dataset_name not in SUPPLEMENTARY_DATASETS:
        raise KeyError(f"Unknown supplementary dataset: {dataset_name}")
    frame = pd.read_excel(RAW_DATA_DIR / SUPPLEMENTARY_DATASETS[dataset_name], header=0)
    frame = normalize_dataframe_columns(frame).dropna(how="all").reset_index(drop=True)
    if "company_id" in frame:
        frame["company_id"] = frame["company_id"].apply(normalize_company_id)
    if "year" in frame:
        frame["year"] = frame["year"].apply(normalize_year)
    if "date" in frame:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return frame


def load_all_supplementary_datasets() -> dict[str, pd.DataFrame]:
    return {
        name: load_supplementary_dataset(name)
        for name in SUPPLEMENTARY_DATASETS
    }