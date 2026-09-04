"""Build and load the Sprint 1 SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.etl.loader import CORE_DATASETS, load_all_core_datasets


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

TABLE_COLUMNS: dict[str, list[str]] = {
    "companies": ["id", "company_logo", "company_name", "chart_link", "about_company", "website"],
    "profitandloss": ["id", "company_id", "year", "sales", "expenses", "operating_profit", "opm_percentage", "other_income", "interest", "depreciation", "profit_before_tax", "tax_percentage", "net_profit", "eps", "dividend_payout"],
    "balancesheet": ["id", "company_id", "year", "equity_capital", "reserves", "borrowings", "other_liabilities", "total_liabilities", "fixed_assets", "cwip", "investments", "other_asset", "total_assets"],
    "cashflow": ["id", "company_id", "year", "operating_activity", "investing_activity", "financing_activity", "net_cash_flow"],
    "analysis": ["id", "company_id", "compounded_sales_growth", "compounded_profit_growth", "stock_price_cagr", "roe"],
    "documents": ["id", "company_id", "year", "annual_report"],
    "prosandcons": ["id", "company_id", "pros", "cons"],
}

NUMERIC_COLUMNS = {
    "year", "sales", "expenses", "operating_profit", "opm_percentage", "other_income",
    "interest", "depreciation", "profit_before_tax", "tax_percentage", "net_profit", "eps",
    "dividend_payout", "equity_capital", "reserves", "borrowings", "other_liabilities",
    "total_liabilities", "fixed_assets", "cwip", "investments", "other_asset", "total_assets",
    "operating_activity", "investing_activity", "financing_activity", "net_cash_flow",
}


def _sql_type(column: str) -> str:
    if column == "year":
        return "INTEGER"
    if column in NUMERIC_COLUMNS:
        return "REAL"
    return "TEXT"


def create_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        DROP TABLE IF EXISTS prosandcons;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS analysis;
        DROP TABLE IF EXISTS cashflow;
        DROP TABLE IF EXISTS balancesheet;
        DROP TABLE IF EXISTS profitandloss;
        DROP TABLE IF EXISTS companies;
        """
    )
    for dataset in CORE_DATASETS:
        columns = TABLE_COLUMNS[dataset]
        definitions = [f'"{column}" {_sql_type(column)}' for column in columns]
        definitions[0] += " PRIMARY KEY"
        if dataset != "companies":
            definitions[1] += " NOT NULL REFERENCES companies(id) ON UPDATE CASCADE"
        connection.execute(f'CREATE TABLE "{dataset}" ({", ".join(definitions)})')


def _clean_dataframe(dataset: str, dataframe: pd.DataFrame) -> pd.DataFrame:
    source = dataframe.loc[:, ~dataframe.columns.duplicated(keep="first")]
    result = source.reindex(columns=TABLE_COLUMNS[dataset]).copy()
    for column in result.columns:
        result[column] = result[column].where(result[column].notna(), None)
    return result


def _manual_review(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    companies = datasets["companies"]
    selected = ["ABB", "HDFCBANK", "M&M", "SBILIFE", "TCS"]
    rows: list[dict[str, Any]] = []
    for company_id in selected:
        company = companies[companies["id"] == company_id]
        child_counts = {
            dataset: int((dataframe.get("company_id") == company_id).sum())
            for dataset, dataframe in datasets.items()
            if dataset != "companies"
        }
        rows.append({
            "company_id": company_id,
            "company_record_found": not company.empty,
            "company_name": None if company.empty else company.iloc[0]["company_name"],
            "child_rows": sum(child_counts.values()),
            "child_row_counts": "; ".join(f"{name}={count}" for name, count in child_counts.items()),
            "status": "PASS" if not company.empty else "FAIL",
        })
    return pd.DataFrame(rows)


def load_database(database_path: Path = DATABASE_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    datasets = load_all_core_datasets()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    audit_rows = []
    with sqlite3.connect(database_path) as connection:
        create_schema(connection)
        for dataset in CORE_DATASETS:
            dataframe = _clean_dataframe(dataset, datasets[dataset])
            columns = TABLE_COLUMNS[dataset]
            placeholders = ", ".join("?" for _ in columns)
            quoted = ", ".join(f'"{column}"' for column in columns)
            connection.executemany(
                f'INSERT INTO "{dataset}" ({quoted}) VALUES ({placeholders})',
                dataframe.itertuples(index=False, name=None),
            )
            audit_rows.append({"dataset": dataset, "source_rows": len(dataframe), "rows_loaded": len(dataframe), "rows_rejected": 0})
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign-key check failed: {fk_errors}")
    audit = pd.DataFrame(audit_rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUTPUT_DIR / "load_audit.csv", index=False)
    review = _manual_review(datasets)
    review.to_csv(OUTPUT_DIR / "manual_data_quality_review.csv", index=False)
    return audit, review


def main() -> None:
    audit, review = load_database()
    print(audit.to_string(index=False))
    print(f"Manual review: {int((review['status'] == 'PASS').sum())}/{len(review)} passed")
    print(f"Database: {DATABASE_PATH}")


if __name__ == "__main__":
    main()