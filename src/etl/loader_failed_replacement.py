"""
Nifty 100 Financial Intelligence Platform
ETL Loader

Day 01-03:
- Load source datasets
- Support TSV files stored with .xlsx extension
- Normalise column names
- Repair malformed companies source
- Normalise company IDs and years
- Validate required schema
- Return clean pandas DataFrames
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.etl.normaliser import (
    normalize_text,
    normalize_ticker,
    normalize_year,
)


# ============================================================
# LOGGING
# ============================================================

LOGGER = logging.getLogger(__name__)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


# ============================================================
# DATASET CONFIGURATION
# ============================================================

DATASET_CONFIG: dict[str, dict[str, Any]] = {

    "companies": {
        "file": "companies.xlsx",
        "required_columns": [
            "id",
            "company_logo",
            "company_name",
            "chart_link",
            "about_company",
            "website",
        ],
    },

    "profitandloss": {
        "file": "profitandloss.xlsx",
        "required_columns": [
            "id",
            "company_id",
            "year",
            "sales",
            "expenses",
            "operating_profit",
            "opm_percentage",
            "other_income",
            "interest",
            "depreciation",
            "profit_before_tax",
            "tax_percentage",
            "net_profit",
            "eps",
            "dividend_payout",
        ],
    },

    "balancesheet": {
        "file": "balancesheet.xlsx",
        "required_columns": [
            "id",
            "company_id",
            "year",
            "equity_capital",
            "reserves",
            "borrowings",
            "other_liabilities",
            "total_liabilities",
            "fixed_assets",
            "cwip",
            "investments",
            "other_asset",
            "total_assets",
        ],
    },

    "cashflow": {
        "file": "cashflow.xlsx",
        "required_columns": [
            "id",
            "company_id",
            "year",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ],
    },

    "analysis": {
        "file": "analysis.xlsx",
        "required_columns": [
            "id",
            "company_id",
            "compounded_sales_growth",
            "compounded_profit_growth",
            "stock_price_cagr",
            "roe",
        ],
    },

    "documents": {
        "file": "documents.xlsx",
        "required_columns": [
            "id",
            "company_id",
            "year",
            "annual_report",
        ],
    },

    "prosandcons": {
        "file": "prosandcons.xlsx",
        "required_columns": [
            "id",
            "company_id",
            "pros",
            "cons",
        ],
    },
}


# ============================================================
# COLUMN NORMALISATION
# ============================================================

def normalize_column_name(column: Any) -> str:
    """
    Convert a raw column name into a consistent snake_case name.
    """

    if column is None:
        return ""

    text = str(column).strip().lower()

    replacements = {
        " ": "_",
        "-": "_",
        "/": "_",
        "\\": "_",
        ".": "_",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    while "__" in text:
        text = text.replace("__", "_")

    return text.strip("_")


def normalize_dataframe_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalise all DataFrame column names.
    """

    df = df.copy()

    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    return df


# ============================================================
# SOURCE FILE READER
# ============================================================

def read_source_file(
    path: Path,
) -> pd.DataFrame:
    """
    Read a source file.

    The supplied .xlsx files are actually tab-separated text
    files. Therefore we inspect the file content rather than
    relying on the extension.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Source file not found: {path}"
        )

    # --------------------------------------------------------
    # Read a small binary sample
    # --------------------------------------------------------

    with path.open(
        "rb"
    ) as file:

        sample = file.read(4096)

    # --------------------------------------------------------
    # Real XLSX files are ZIP files beginning with PK
    # --------------------------------------------------------

    if sample.startswith(b"PK"):

        LOGGER.info(
            "Reading Excel workbook: %s",
            path,
        )

        return pd.read_excel(
            path,
            engine="openpyxl",
        )

    # --------------------------------------------------------
    # Otherwise treat it as TSV
    # --------------------------------------------------------

    LOGGER.info(
        "Reading tab-separated source: %s",
        path,
    )

    return pd.read_csv(
        path,
        sep="\t",
        dtype=object,
        keep_default_na=True,
        na_values=[
            "",
            "NA",
            "N/A",
            "null",
            "NULL",
            "None",
        ],
        engine="python",
        on_bad_lines="warn",
    )


# ============================================================
# COMPANIES DATASET REPAIR
# ============================================================

def repair_companies_dataset(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Repair the malformed companies source.

    The companies source is stored as TSV text even though its
    extension is .xlsx.

    Some company records are split across multiple physical
    lines. A normal record starts with a company ticker in the
    first column. Continuation records have an empty first
    column.

    Example:

        ADANIPORTS    logo    name    chart    about

        <continuation line containing website>

    This function reconstructs those records.
    """

    if df.empty:
        return df.copy()

    df = df.copy()

    columns = list(df.columns)

    repaired_rows: list[list[Any]] = []

    current: list[Any] | None = None

    for _, row in df.iterrows():

        values: list[Any] = []

        for value in row.tolist():

            if pd.isna(value):
                values.append(None)
            else:
                text = str(value).strip()

                if text == "":
                    values.append(None)
                else:
                    values.append(text)

        # ----------------------------------------------------
        # Ignore completely empty physical rows
        # ----------------------------------------------------

        if not any(
            value not in (None, "")
            for value in values
        ):
            continue

        first_value = values[0]

        # ----------------------------------------------------
        # New company starts whenever column 0 has a value
        # ----------------------------------------------------

        if first_value not in (None, ""):

            if current is not None:
                repaired_rows.append(current)

            current = values.copy()

            continue

        # ----------------------------------------------------
        # Continuation row
        # ----------------------------------------------------

        if current is None:
            continue

        for index, value in enumerate(values):

            if value in (None, ""):
                continue

            # Safety in case malformed source has extra fields
            if index >= len(current):
                continue

            # Empty destination field
            if current[index] in (None, ""):

                current[index] = value

            else:

                # If both are populated, append the continuation
                # rather than silently deleting information.
                current[index] = (
                    f"{current[index]} {value}"
                ).strip()

    # --------------------------------------------------------
    # Add final record
    # --------------------------------------------------------

    if current is not None:
        repaired_rows.append(current)

    repaired = pd.DataFrame(
        repaired_rows,
        columns=columns,
    )

    # --------------------------------------------------------
    # Clean whitespace
    # --------------------------------------------------------

    for column in repaired.columns:

        repaired[column] = repaired[column].apply(
            lambda value:
                value.strip()
                if isinstance(value, str)
                else value
        )

    # --------------------------------------------------------
    # Remove rows that do not have a company ID
    # --------------------------------------------------------

    repaired["id"] = repaired["id"].apply(
        normalize_ticker
    )

    repaired = repaired[
        repaired["id"].notna()
    ].copy()

    # --------------------------------------------------------
    # Remove duplicate company IDs
    #
    # Keep first occurrence because the companies master should
    # contain one record per company.
    # --------------------------------------------------------

    repaired = repaired.drop_duplicates(
        subset=["id"],
        keep="first",
    )

    return repaired.reset_index(
        drop=True
    )


# ============================================================
# SCHEMA VALIDATION
# ============================================================

def validate_columns(
    df: pd.DataFrame,
    dataset_name: str,
) -> None:
    """
    Validate required columns for a dataset.
    """

    if dataset_name not in DATASET_CONFIG:
        raise ValueError(
            f"Unknown dataset: {dataset_name}"
        )

    required = set(
        DATASET_CONFIG[
            dataset_name
        ]["required_columns"]
    )

    actual = set(
        df.columns
    )

    missing = required - actual

    if missing:

        raise ValueError(
            f"Dataset '{dataset_name}' "
            f"is missing required columns: "
            f"{sorted(missing)}"
        )


# ============================================================
# DATAFRAME NORMALISATION
# ============================================================

def normalise_dataset(
    dataset_name: str,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply dataset-specific normalisation.
    """

    df = df.copy()

    # --------------------------------------------------------
    # General text cleanup
    # --------------------------------------------------------

    for column in df.columns:

        if df[column].dtype == object:

            df[column] = df[column].apply(
                normalize_text
            )

    # --------------------------------------------------------
    # Company IDs
    # --------------------------------------------------------

    if "company_id" in df.columns:

        df["company_id"] = df[
            "company_id"
        ].apply(
            normalize_ticker
        )

    # --------------------------------------------------------
    # Company primary key
    # --------------------------------------------------------

    if "id" in df.columns:

        df["id"] = df[
            "id"
        ].apply(
            normalize_ticker
        )

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    if "year" in df.columns:

        df["year"] = df[
            "year"
        ].apply(
            normalize_year
        )

    return df


# ============================================================
# LOAD SINGLE DATASET
# ============================================================

def load_dataset(
    dataset_name: str,
) -> pd.DataFrame:
    """
    Load and normalise one configured dataset.
    """

    if dataset_name not in DATASET_CONFIG:
        raise ValueError(
            f"Unknown dataset: {dataset_name}"
        )

    config = DATASET_CONFIG[
        dataset_name
    ]

    path = (
        RAW_DATA_DIR
        / config["file"]
    )

    LOGGER.info(
        "Loading dataset '%s' from %s",
        dataset_name,
        path,
    )

    df = read_source_file(
        path
    )

    LOGGER.info(
        "Raw shape for '%s': %s",
        dataset_name,
        df.shape,
    )

    # --------------------------------------------------------
    # Normalise columns
    # --------------------------------------------------------

    df = normalize_dataframe_columns(
        df
    )

    LOGGER.info(
        "Detected columns for '%s': %s",
        dataset_name,
        list(df.columns),
    )

    # --------------------------------------------------------
    # Repair companies before schema validation
    # --------------------------------------------------------

    if dataset_name == "companies":

        before_rows = len(df)

        LOGGER.info(
            "Repairing malformed company records..."
        )

        df = repair_companies_dataset(
            df
        )

        LOGGER.info(
            "Companies repaired: %d -> %d rows",
            before_rows,
            len(df),
        )

    # --------------------------------------------------------
    # Validate schema
    # --------------------------------------------------------

    validate_columns(
        df,
        dataset_name,
    )

    # --------------------------------------------------------
    # Keep configured columns
    #
    # Extra source columns are retained only where the existing
    # loader expects them. For the current Day 03 datasets we
    # use the required schema.
    # --------------------------------------------------------

    required_columns = (
        DATASET_CONFIG[
            dataset_name
        ]["required_columns"]
    )

    # Preserve required columns first.
    # Keep additional columns because the validator needs to
    # identify unexpected columns where applicable.
    ordered = [
        column
        for column in required_columns
        if column in df.columns
    ]

    extras = [
        column
        for column in df.columns
        if column not in ordered
    ]

    df = df[
        ordered + extras
    ]

    # --------------------------------------------------------
    # Normalise values
    # --------------------------------------------------------

    df = normalise_dataset(
        dataset_name,
        df,
    )

    # --------------------------------------------------------
    # Reset index
    # --------------------------------------------------------

    df = df.reset_index(
        drop=True
    )

    LOGGER.info(
        "Final shape for '%s': %s",
        dataset_name,
        df.shape,
    )

    return df


# ============================================================
# LOAD ALL CORE DATASETS
# ============================================================

def load_all_core_datasets() -> dict[str, pd.DataFrame]:
    """
    Load all seven Day-03 core datasets.
    """

    datasets: dict[
        str,
        pd.DataFrame
    ] = {}

    for dataset_name in DATASET_CONFIG:

        datasets[
            dataset_name
        ] = load_dataset(
            dataset_name
        )

    return datasets


# ============================================================
# DATASET SUMMARY
# ============================================================

def create_dataset_summary(
    datasets: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Create a compact summary of loaded datasets.
    """

    rows = []

    for name, df in datasets.items():

        rows.append(
            {
                "dataset": name,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": ", ".join(
                    str(column)
                    for column in df.columns
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )

    print()
    print(
        "========================================"
    )
    print(
        "NIFTY 100 DATASET LOADING"
    )
    print(
        "========================================"
    )
    print()

    print(
        "Loading datasets..."
    )

    datasets = (
        load_all_core_datasets()
    )

    summary = (
        create_dataset_summary(
            datasets
        )
    )

    print()
    print(
        "========================================"
    )
    print(
        "NIFTY 100 DATASET LOADING SUMMARY"
    )
    print(
        "========================================"
    )
    print()

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"Successfully loaded "
        f"{len(datasets)} core datasets."
    )

    LOGGER.info(
        "Core dataset loading completed successfully"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()