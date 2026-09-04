"""Build and load the Sprint 1 SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.ratios import build_financial_ratios
from src.analytics.peer import build_peer_percentiles
from src.screener.engine import generate_screener_outputs
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
        DROP TABLE IF EXISTS financial_ratios;
        DROP TABLE IF EXISTS peer_percentiles;
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
    connection.execute(
        """CREATE TABLE financial_ratios (
            ratio_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL REFERENCES companies(id) ON UPDATE CASCADE,
            year INTEGER,
            operating_margin_pct REAL, net_margin_pct REAL, debt_to_equity REAL,
            return_on_equity_pct REAL, return_on_capital_employed_pct REAL,
            return_on_assets_pct REAL, asset_turnover REAL, fixed_asset_turnover REAL,
            liabilities_to_assets REAL, interest_coverage REAL,
            operating_cash_flow REAL, free_cash_flow REAL, financing_cash_flow REAL,
            cash_conversion REAL, operating_cash_flow_margin_pct REAL,
            dividend_payout REAL, financial_carveout TEXT, carveout_note TEXT,
            source_roe_pct REAL, roe_source_difference_pct REAL, roe_source_crosscheck TEXT,
            source_roce_pct REAL, roce_source_difference_pct REAL, roce_source_crosscheck TEXT,
            cagr_3y REAL, cagr_5y REAL, cagr_10y REAL, cagr_edge_case TEXT,
            cashflow_edge_case TEXT, ratio_edge_case TEXT, capital_allocation_pattern TEXT
        )"""
    )
    connection.execute("""CREATE TABLE peer_percentiles (
        peer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL REFERENCES companies(id) ON UPDATE CASCADE,
        peer_group TEXT NOT NULL,
        return_on_equity_pct REAL, return_on_equity_pct_percentile REAL,
        return_on_capital_employed_pct REAL, return_on_capital_employed_pct_percentile REAL,
        debt_to_equity REAL, debt_to_equity_percentile REAL,
        interest_coverage REAL, interest_coverage_percentile REAL,
        operating_margin_pct REAL, operating_margin_pct_percentile REAL,
        net_margin_pct REAL, net_margin_pct_percentile REAL,
        asset_turnover REAL, asset_turnover_percentile REAL,
        cash_conversion REAL, cash_conversion_percentile REAL,
        cagr_5y REAL, cagr_5y_percentile REAL,
        cagr_10y REAL, cagr_10y_percentile REAL
    )""")


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
        ratios = build_financial_ratios(datasets)
        ratio_columns = [column[1] for column in connection.execute("PRAGMA table_info(financial_ratios)").fetchall() if column[1] != "ratio_id"]
        ratio_frame = ratios.reindex(columns=ratio_columns).where(ratios.notna(), None)
        connection.executemany(
            f'INSERT INTO financial_ratios ({", ".join(ratio_columns)}) VALUES ({", ".join("?" for _ in ratio_columns)})',
            ratio_frame.itertuples(index=False, name=None),
        )
        audit_rows.append({"dataset": "financial_ratios", "source_rows": len(ratios), "rows_loaded": len(ratios), "rows_rejected": 0})
        percentiles = build_peer_percentiles(ratios, datasets["companies"])
        peer_columns = [column[1] for column in connection.execute("PRAGMA table_info(peer_percentiles)").fetchall() if column[1] != "peer_id"]
        peer_frame = percentiles.reindex(columns=peer_columns).where(percentiles.notna(), None)
        connection.executemany(
            f'INSERT INTO peer_percentiles ({", ".join(peer_columns)}) VALUES ({", ".join("?" for _ in peer_columns)})',
            peer_frame.itertuples(index=False, name=None),
        )
        audit_rows.append({"dataset": "peer_percentiles", "source_rows": len(percentiles), "rows_loaded": len(percentiles), "rows_rejected": 0})
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign-key check failed: {fk_errors}")
    audit = pd.DataFrame(audit_rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUTPUT_DIR / "load_audit.csv", index=False)
    review = _manual_review(datasets)
    review.to_csv(OUTPUT_DIR / "manual_data_quality_review.csv", index=False)
    latest_patterns = ratios.sort_values(["company_id", "year"], na_position="first").drop_duplicates("company_id", keep="last")
    latest_patterns[["company_id", "capital_allocation_pattern"]].to_csv(OUTPUT_DIR / "capital_allocation.csv", index=False)
    generate_screener_outputs(ratios, datasets["companies"])
    return audit, review


def main() -> None:
    audit, review = load_database()
    print(audit.to_string(index=False))
    print(f"Manual review: {int((review['status'] == 'PASS').sum())}/{len(review)} passed")
    print(f"Database: {DATABASE_PATH}")


if __name__ == "__main__":
    main()