"""
Nifty 100 Financial Intelligence Platform
==========================================

Robust ETL Loader

Responsibilities
----------------
1. Discover the seven core datasets.
2. Read genuine Excel files or text/TSV files incorrectly named .xlsx.
3. Detect title rows and actual headers.
4. Normalize column names.
5. Normalize company IDs.
6. Normalize year fields.
7. Repair malformed multiline company records.
8. Validate required columns.
9. Return clean DataFrames.

NOTE
----
Some supplied files have an .xlsx extension but are actually
tab-separated text files. This loader detects both formats.
"""

from __future__ import annotations

import csv
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from src.etl.normaliser import (
    normalize_ticker,
    normalize_year,
)


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
)

LOGGER = logging.getLogger(__name__)


# ============================================================
# CORE DATASETS
# ============================================================

CORE_DATASETS = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
]


# ============================================================
# DATASET CONFIGURATION
# ============================================================

DATASET_CONFIG: dict[str, dict[str, Any]] = {

    "companies": {
        "patterns": [
            "companies.xlsx",
        ],
        "required_columns": [
            "id",
            "company_logo",
            "company_name",
            "chart_link",
            "about_company",
            "website",
        ],
        "company_column": "id",
        "year_column": None,
    },

    "profitandloss": {
        "patterns": [
            "profitandloss.xlsx",
        ],
        "required_columns": [
            "id",
            "company_id",
            "year",
            "sales",
            "expenses",
            "operating_profit",
            "other_income",
            "depreciation",
            "interest",
            "profit_before_tax",
            "tax_percentage",
            "net_profit",
            "eps",
            "dividend_payout",
        ],
        "company_column": "company_id",
        "year_column": "year",
    },

    "balancesheet": {
        "patterns": [
            "balancesheet.xlsx",
        ],
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
        "company_column": "company_id",
        "year_column": "year",
    },

    "cashflow": {
        "patterns": [
            "cashflow.xlsx",
        ],
        "required_columns": [
            "id",
            "company_id",
            "year",
            "operating_activity",
"investing_activity",
"financing_activity",
            "net_cash_flow",
        ],
        "company_column": "company_id",
        "year_column": "year",
    },

    "analysis": {
        "patterns": [
            "analysis.xlsx",
        ],
        "required_columns": [
            "company_id",
        ],
        "company_column": "company_id",
        "year_column": None,
    },

    "documents": {
        "patterns": [
            "documents.xlsx",
        ],
        "required_columns": [
            "company_id",
        ],
        "company_column": "company_id",
        "year_column": "year",
    },

    "prosandcons": {
        "patterns": [
            "prosandcons.xlsx",
        ],
        "required_columns": [
            "company_id",
        ],
        "company_column": "company_id",
        "year_column": None,
    },
}


# ============================================================
# COMPANY ID ALIASES
# ============================================================

COMPANY_ID_ALIASES = {
    "M_M": "M&M",
    "MM": "M&M",
}


# ============================================================
# MISSING COMPANY METADATA
# ============================================================

# These company IDs exist in the financial datasets but are
# absent from the malformed companies source.

MISSING_COMPANIES: dict[str, dict[str, str]] = {

    "AGTL": {
        "company_name": "Adani Green Energy Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "ULTRACEMCO": {
        "company_name": "UltraTech Cement Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "UNIONBANK": {
        "company_name": "Union Bank of India",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "UNITDSPR": {
        "company_name": "United Spirits Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "VBL": {
        "company_name": "Varun Beverages Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "VEDL": {
        "company_name": "Vedanta Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "WIPRO": {
        "company_name": "Wipro Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "ZOMATO": {
        "company_name": "Zomato Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },

    "ZYDUSLIFE": {
        "company_name": "Zydus Lifesciences Ltd",
        "company_logo": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    },
}


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_column_name(
    column: object,
) -> str:
    """
    Convert a column name into snake_case.
    """

    if column is None:
        return ""

    text = str(column).strip()

    replacements = {
        "P&L": "profit_and_loss",
        "P & L": "profit_and_loss",
        "ROE": "roe",
        "ROCE": "roce",
        "EPS": "eps",
        "TTM": "ttm",
        "CAGR": "cagr",
        "URL": "url",
        "ID": "id",
        "FY": "fy",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    text = re.sub(
        r"_+",
        "_",
        text,
    )

    return text.strip("_")


def normalize_dataframe_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize all DataFrame column names.
    """

    result = dataframe.copy()

    result.columns = [
        normalize_column_name(column)
        for column in result.columns
    ]

    return result


# ============================================================
# COMPANY ID NORMALIZATION
# ============================================================

def normalize_company_id(
    value: object,
) -> str | None:
    """
    Normalize company IDs while preserving special tickers.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return None

    # Preserve M&M correctly.
    if text.upper() in {
        "M&M",
        "M & M",
        "M&M.",
        "M_M",
        "MM",
    }:
        return "M&M"

    normalized = normalize_ticker(
        text
    )

    if normalized is None:
        return None

    return COMPANY_ID_ALIASES.get(
        normalized,
        normalized,
    )


# ============================================================
# FILE TYPE DETECTION
# ============================================================

def is_real_excel_file(
    file_path: Path,
) -> bool:
    """
    Return True if the file is a genuine XLSX workbook.
    """

    try:

        if not zipfile.is_zipfile(
            file_path
        ):
            return False

        with zipfile.ZipFile(
            file_path
        ) as archive:

            names = archive.namelist()

            return (
                "[Content_Types].xml"
                in names
            )

    except (
        OSError,
        zipfile.BadZipFile,
    ):
        return False


# ============================================================
# TEXT SOURCE HELPERS
# ============================================================

def read_source_lines(
    file_path: Path,
) -> list[str]:
    """
    Read a text source using UTF-8 with fallback.
    """

    try:

        return (
            file_path
            .read_text(
                encoding="utf-8-sig",
                errors="strict",
            )
            .splitlines()
        )

    except UnicodeDecodeError:

        return (
            file_path
            .read_text(
                encoding="cp1252",
                errors="replace",
            )
            .splitlines()
        )


def detect_delimiter(
    lines: list[str],
) -> str:
    """
    Detect the most likely delimiter.
    """

    sample = [
        line
        for line in lines
        if line.strip()
    ][:20]

    if not sample:
        return "\t"

    candidates = [
        "\t",
        ",",
        ";",
        "|",
    ]

    scores: dict[str, int] = {}

    for delimiter in candidates:

        score = sum(
            line.count(delimiter)
            for line in sample
        )

        scores[delimiter] = score

    best = max(
        scores,
        key=scores.get,
    )

    return best


def find_header_row(
    lines: list[str],
    delimiter: str,
    dataset_name: str,
) -> int:
    """
    Locate the actual dataset header row.
    """

    required_columns = set(
        DATASET_CONFIG[
            dataset_name
        ]["required_columns"]
    )

    for index, line in enumerate(lines):

        stripped = line.strip()

        if not stripped:
            continue

        if delimiter not in stripped:
            continue

        columns = [
            normalize_column_name(
                value
            )
            for value in stripped.split(
                delimiter
            )
        ]

        column_set = set(
            columns
        )

        # Exact schema match is best.
        required_matches = len(
            required_columns
            & column_set
        )

        if required_matches >= min(
            2,
            len(required_columns),
        ):
            return index

        # Companies dataset begins with "id" and has
        # several metadata columns.
        if (
            dataset_name == "companies"
            and "id" in column_set
            and "company_name" in column_set
        ):
            return index

        # Supplementary datasets may only have company_id.
        if (
            "company_id"
            in column_set
            and len(columns) >= 2
        ):
            return index

    raise ValueError(
        f"Could not detect a valid header row "
        f"for dataset '{dataset_name}'."
    )


def read_text_source(
    file_path: Path,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Read a text/TSV source even when named .xlsx.
    """

    lines = read_source_lines(
        file_path
    )

    if not lines:
        return pd.DataFrame()

    delimiter = detect_delimiter(
        lines
    )

    header_row = find_header_row(
        lines,
        delimiter,
        dataset_name,
    )

    header = [
        normalize_column_name(
            value
        )
        for value in lines[
            header_row
        ].split(delimiter)
    ]

    data_rows: list[list[str]] = []

    for line in lines[
        header_row + 1:
    ]:

        if not line.strip():
            continue

        row = line.split(
            delimiter
        )

        data_rows.append(
            row
        )

    max_columns = max(
        len(header),
        max(
            (
                len(row)
                for row in data_rows
            ),
            default=0,
        ),
    )

    if len(header) < max_columns:

        header.extend(
            [
                f"extra_column_{index}"
                for index in range(
                    len(header),
                    max_columns,
                )
            ]
        )

    padded_rows = []

    for row in data_rows:

        if len(row) < len(header):

            row = row + [
                ""
            ] * (
                len(header)
                - len(row)
            )

        elif len(row) > len(header):

            row = row[:len(header)]

        padded_rows.append(
            row
        )

    dataframe = pd.DataFrame(
        padded_rows,
        columns=header,
    )

    return dataframe


# ============================================================
# SOURCE FILE READING
# ============================================================

def read_source_file(
    file_path: Path,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Read either a genuine Excel workbook or a text/TSV
    file incorrectly named .xlsx.
    """

    if not file_path.exists():

        raise FileNotFoundError(
            f"Source file not found: "
            f"{file_path}"
        )

    if is_real_excel_file(
        file_path
    ):

        LOGGER.info(
            "Reading Excel file: %s",
            file_path.name,
        )

        return pd.read_excel(
            file_path,
            dtype=object,
        )

    LOGGER.info(
        "Reading text/TSV source: %s",
        file_path.name,
    )

    return read_text_source(
        file_path,
        dataset_name,
    )


# ============================================================
# COMPANY DATA REPAIR HELPERS
# ============================================================

def is_probable_ticker(
    value: object,
) -> bool:
    """
    Check whether a value resembles a company ticker.
    """

    if value is None:
        return False

    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return False

    if text.upper() == "M&M":
        return True

    if len(text) > 20:
        return False

    if not re.fullmatch(
        r"[A-Za-z0-9&._-]+",
        text,
    ):
        return False

    return any(
        character.isalpha()
        for character in text
    )


def is_url(
    value: object,
) -> bool:
    """
    Check whether a value looks like a URL.
    """

    if value is None:
        return False

    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass

    text = str(value).strip().lower()

    return text.startswith(
        (
            "http://",
            "https://",
            "www.",
        )
    )


def append_text(
    existing: object,
    addition: object,
) -> str:
    """
    Safely append text.
    """

    left = ""

    if existing is not None:

        try:
            if not pd.isna(existing):
                left = str(existing).strip()
        except (TypeError, ValueError):
            left = str(existing).strip()

    right = ""

    if addition is not None:

        try:
            if not pd.isna(addition):
                right = str(addition).strip()
        except (TypeError, ValueError):
            right = str(addition).strip()

    if not left:
        return right

    if not right:
        return left

    return (
        left
        + " "
        + right
    )


def empty_company_record() -> dict[str, str]:
    """
    Return an empty companies record.
    """

    return {
        "id": "",
        "company_logo": "",
        "company_name": "",
        "chart_link": "",
        "about_company": "",
        "website": "",
    }


# ============================================================
# COMPANY DATAFRAME REPAIR
# ============================================================

def repair_companies_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Repair malformed multiline rows in companies.xlsx.

    Some company records are split across multiple physical
    lines. A continuation row usually starts with an empty ID
    column or contains a non-ticker fragment in the ID column.

    This function reconstructs those rows and removes garbage
    continuation records.
    """

    required_columns = [
        "id",
        "company_logo",
        "company_name",
        "chart_link",
        "about_company",
        "website",
    ]

    result = dataframe.copy()

    for column in required_columns:

        if column not in result.columns:
            result[column] = ""

    result = result[
        required_columns
    ].copy()

    repaired_records: list[
        dict[str, str]
    ] = []

    current: dict[str, str] | None = None

    for _, row in result.iterrows():

        raw_id = row.get(
            "id",
            "",
        )

        raw_values = {
            column: row.get(
                column,
                "",
            )
            for column in required_columns
        }

        if is_probable_ticker(
            raw_id
        ):

            if current is not None:

                repaired_records.append(
                    current
                )

            current = empty_company_record()

            for column in required_columns:

                value = raw_values[
                    column
                ]

                if value is None:
                    value = ""

                try:
                    if pd.isna(value):
                        value = ""
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

                current[column] = str(
                    value
                ).strip()

            continue

        # Continuation row.
        if current is None:
            continue

        fragment_id = ""

        if raw_id is not None:

            try:
                if not pd.isna(raw_id):
                    fragment_id = str(
                        raw_id
                    ).strip()
            except (
                TypeError,
                ValueError,
            ):
                fragment_id = str(
                    raw_id
                ).strip()

        if fragment_id:
            current[
                "about_company"
            ] = append_text(
                current[
                    "about_company"
                ],
                fragment_id,
            )

        for column in required_columns[1:]:

            value = raw_values[
                column
            ]

            if value is None:
                continue

            try:
                if pd.isna(value):
                    continue
            except (
                TypeError,
                ValueError,
            ):
                pass

            text = str(
                value
            ).strip()

            if not text:
                continue

            if is_url(text):

                if not current[
                    "website"
                ]:
                    current[
                        "website"
                    ] = text

                elif not current[
                    "chart_link"
                ]:
                    current[
                        "chart_link"
                    ] = text

                else:
                    current[
                        "about_company"
                    ] = append_text(
                        current[
                            "about_company"
                        ],
                        text,
                    )

            else:

                current[
                    "about_company"
                ] = append_text(
                    current[
                        "about_company"
                    ],
                    text,
                )

    if current is not None:

        repaired_records.append(
            current
        )

    repaired = pd.DataFrame(
        repaired_records,
        columns=required_columns,
    )

    # Normalize IDs.
    repaired["id"] = repaired[
        "id"
    ].apply(
        normalize_company_id
    )

    repaired = repaired[
        repaired["id"].notna()
    ].copy()

    # Remove obvious malformed continuation IDs.
    repaired = repaired[
        repaired["id"].apply(
            is_probable_ticker
        )
    ].copy()

    # Remove duplicate company IDs.
    repaired = repaired.drop_duplicates(
        subset=["id"],
        keep="first",
    )

    repaired = repaired.reset_index(
        drop=True
    )

    return repaired


# ============================================================
# ADD MISSING COMPANY RECORDS
# ============================================================

def add_missing_company_records(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add company records that are referenced by the financial
    datasets but absent from companies.xlsx.
    """

    result = dataframe.copy()

    existing_ids = set(
        result["id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    new_records = []

    for company_id, metadata in (
        MISSING_COMPANIES.items()
    ):

        if company_id in existing_ids:
            continue

        record = {
            "id": company_id,
            "company_logo": metadata[
                "company_logo"
            ],
            "company_name": metadata[
                "company_name"
            ],
            "chart_link": metadata[
                "chart_link"
            ],
            "about_company": metadata[
                "about_company"
            ],
            "website": metadata[
                "website"
            ],
        }

        new_records.append(
            record
        )

    if new_records:

        result = pd.concat(
            [
                result,
                pd.DataFrame(
                    new_records
                ),
            ],
            ignore_index=True,
        )

    return result


# ============================================================
# FILE DISCOVERY
# ============================================================

def find_dataset_file(
    dataset_name: str,
) -> Path:
    """
    Locate the source file for a dataset.
    """

    if dataset_name not in DATASET_CONFIG:

        raise KeyError(
            f"Unknown dataset: "
            f"{dataset_name}"
        )

    patterns = DATASET_CONFIG[
        dataset_name
    ]["patterns"]

    for pattern in patterns:

        matches = sorted(
            RAW_DATA_DIR.glob(
                pattern
            )
        )

        if matches:
            return matches[0]

    raise FileNotFoundError(
        f"Could not find source file for "
        f"dataset '{dataset_name}' in "
        f"{RAW_DATA_DIR}"
    )


# ============================================================
# COLUMN VALIDATION
# ============================================================

def validate_columns(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> None:
    """
    Ensure all required columns exist.
    """

    required = set(
        DATASET_CONFIG[
            dataset_name
        ]["required_columns"]
    )

    actual = set(
        dataframe.columns
    )

    missing = sorted(
        required - actual
    )

    if missing:

        raise ValueError(
            f"Dataset '{dataset_name}' is "
            f"missing required columns: "
            f"{missing}. "
            f"Actual columns: "
            f"{list(dataframe.columns)}"
        )


# ============================================================
# DATASET NORMALIZATION
# ============================================================

def normalize_dataset(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Apply dataset-specific normalization.
    """

    result = dataframe.copy()

    config = DATASET_CONFIG[
        dataset_name
    ]

    company_column = config[
        "company_column"
    ]

    year_column = config[
        "year_column"
    ]

    # --------------------------------------------------------
    # Company ID
    # --------------------------------------------------------

    if (
        company_column
        and company_column
        in result.columns
    ):

        result[
            company_column
        ] = result[
            company_column
        ].apply(
            normalize_company_id
        )

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    if (
        year_column
        and year_column
        in result.columns
    ):

        result[
            year_column
        ] = result[
            year_column
        ].apply(
            normalize_year
        )

    # --------------------------------------------------------
    # Convert common empty text values to missing values
    # --------------------------------------------------------

    result = result.replace(
        {
            "": None,
            " ": None,
            "nan": None,
            "None": None,
            "NULL": None,
            "null": None,
            "N/A": None,
            "NA": None,
        }
    )

    # --------------------------------------------------------
    # Remove completely empty rows
    # --------------------------------------------------------

    result = (
        result
        .dropna(
            how="all"
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# LOAD ONE DATASET
# ============================================================

def load_excel(
    path: Path,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Load one dataset.
    """

    LOGGER.info(
        "Loading dataset '%s' from %s",
        dataset_name,
        path,
    )

    dataframe = read_source_file(
        path,
        dataset_name,
    )

    dataframe = normalize_dataframe_columns(
        dataframe
    )

    # Companies requires special repair BEFORE validation.
    if dataset_name == "companies":

        dataframe = repair_companies_dataframe(
            dataframe
        )

        dataframe = add_missing_company_records(
            dataframe
        )

    validate_columns(
        dataframe,
        dataset_name,
    )

    dataframe = normalize_dataset(
        dataframe,
        dataset_name,
    )

    # Final companies cleanup.
    if dataset_name == "companies":

        dataframe = dataframe.drop_duplicates(
            subset=["id"],
            keep="first",
        )

        dataframe = dataframe.reset_index(
            drop=True
        )

    LOGGER.info(
        "Dataset '%s' ready: %d rows, %d columns",
        dataset_name,
        len(dataframe),
        len(dataframe.columns),
    )

    return dataframe


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def load_dataset(
    dataset_name: str,
) -> pd.DataFrame:
    """
    Load a single named dataset.
    """

    path = find_dataset_file(
        dataset_name
    )

    return load_excel(
        path,
        dataset_name,
    )


# ============================================================
# LOAD ALL CORE DATASETS
# ============================================================

def load_all_core_datasets() -> dict[
    str,
    pd.DataFrame,
]:
    """
    Load all seven core datasets.
    """

    datasets: dict[
        str,
        pd.DataFrame,
    ] = {}

    for dataset_name in CORE_DATASETS:

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
    datasets: dict[
        str,
        pd.DataFrame,
    ],
) -> pd.DataFrame:
    """
    Create a dataset summary.
    """

    rows = []

    for dataset_name, dataframe in (
        datasets.items()
    ):

        rows.append(
            {
                "dataset": dataset_name,
                "rows": len(
                    dataframe
                ),
                "columns": len(
                    dataframe.columns
                ),
                "missing_cells": int(
                    dataframe
                    .isna()
                    .sum()
                    .sum()
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
    """
    Execute the ETL loader.
    """

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    print()
    print("=" * 60)
    print("NIFTY 100 DATASET LOADING")
    print("=" * 60)
    print()

    datasets = load_all_core_datasets()

    summary = create_dataset_summary(
        datasets
    )

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


if __name__ == "__main__":
    main()