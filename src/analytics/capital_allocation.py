"""Capital-allocation completeness and year-over-year change reports."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics.ratios import classify_capital_allocation

ROOT = Path(__file__).resolve().parents[2]


def write_capital_allocation_outputs(database_path: Path = ROOT / "nifty100.db", output_dir: Path = ROOT / "output") -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as c:
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", c)
    ratios["capital_allocation_pattern"] = ratios.apply(classify_capital_allocation, axis=1)
    ratios[["company_id", "year", "capital_allocation_pattern"]].to_csv(output_dir / "capital_allocation_all_years.csv", index=False)
    latest = ratios.sort_values("year").drop_duplicates("company_id", keep="last")
    latest.groupby("capital_allocation_pattern").size().rename("company_count").reset_index().to_csv(output_dir / "capital_allocation_distribution.csv", index=False)
    ordered = ratios.sort_values(["company_id", "year"]).copy(); ordered["previous_pattern"] = ordered.groupby("company_id").capital_allocation_pattern.shift(1); changes = ordered[ordered.previous_pattern.notna() & (ordered.previous_pattern != ordered.capital_allocation_pattern)][["company_id", "year", "previous_pattern", "capital_allocation_pattern"]]
    changes.to_csv(output_dir / "pattern_changes.csv", index=False)
    return latest, changes


if __name__ == "__main__":
    latest, changes = write_capital_allocation_outputs(); print(f"Latest rows: {len(latest)}; changes: {len(changes)}")
