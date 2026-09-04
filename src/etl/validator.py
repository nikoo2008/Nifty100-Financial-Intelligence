"""
Nifty 100 Financial Intelligence Platform
Day 03 - Data Quality / Schema Validation

Validates the seven core Nifty 100 datasets and produces:

    reports/validation_failures.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORTS_DIR = PROJECT_ROOT / "reports"

FAILURE_REPORT = (
    REPORTS_DIR / "validation_failures.csv"
)


# ============================================================
# FAILURE REPORT SCHEMA
# ============================================================

FAILURE_COLUMNS = [
    "dataset",
    "rule",
    "severity",
    "row",
    "column",
    "value",
    "message",
]


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS: dict[str, list[str]] = {

    "companies": [
        "id",
        "company_logo",
        "company_name",
        "chart_link",
        "about_company",
        "website",
    ],

    "profitandloss": [
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

    "balancesheet": [
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

    "cashflow": [
        "id",
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ],

    "analysis": [
        "id",
        "company_id",
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ],

    "documents": [
        "id",
        "company_id",
        "year",
        "annual_report",
    ],

    "prosandcons": [
        "id",
        "company_id",
        "pros",
        "cons",
    ],
}


# ============================================================
# NUMERIC COLUMNS
# ============================================================

NUMERIC_COLUMNS: dict[str, list[str]] = {

    "profitandloss": [
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

    "balancesheet": [
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

    "cashflow": [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ],

    "analysis": [
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ],
}


# ============================================================
# PERCENTAGE COLUMNS
# ============================================================

PERCENTAGE_COLUMNS: dict[str, list[str]] = {

    "profitandloss": [
        "opm_percentage",
        "tax_percentage",
        "dividend_payout",
    ],

    "analysis": [
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ],
}


# ============================================================
# HELPER: ADD FAILURE
# ============================================================

def _add_failure(
    failures: list[dict[str, Any]],
    dataset: str,
    rule: str,
    severity: str,
    row: Any = "",
    column: str = "",
    value: Any = "",
    message: str = "",
) -> None:

    failures.append(
        {
            "dataset": dataset,
            "rule": rule,
            "severity": severity,
            "row": row,
            "column": column,
            "value": value,
            "message": message,
        }
    )


# ============================================================
# HELPER: MISSING VALUE
# ============================================================

def _is_missing(value: Any) -> bool:

    if value is None:
        return True

    try:
        result = pd.isna(value)

        if isinstance(result, bool):
            return result

        return False

    except (TypeError, ValueError):
        return False


# ============================================================
# HELPER: NUMERIC CONVERSION
# ============================================================

def _to_numeric(
    value: Any,
) -> float | None:

    if _is_missing(value):
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):

        try:

            number = float(value)

            if pd.isna(number):
                return None

            return number

        except (TypeError, ValueError):

            return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace(",", "")
    text = text.replace("%", "")
    text = text.replace("₹", "")
    text = text.replace("$", "")

    # Accounting format:
    # (123.45) -> -123.45

    if (
        text.startswith("(")
        and text.endswith(")")
    ):
        text = "-" + text[1:-1].strip()

    try:

        return float(text)

    except ValueError:

        return None


# ============================================================
# RULE 1
# REQUIRED COLUMNS
# ============================================================

def validate_required_columns(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    required = set(
        REQUIRED_COLUMNS.get(
            dataset,
            [],
        )
    )

    actual = set(df.columns)

    missing = sorted(
        required - actual
    )

    for column in missing:

        _add_failure(
            failures,
            dataset,
            "REQUIRED_COLUMN",
            "CRITICAL",
            column=column,
            message=(
                f"Required column '{column}' "
                "is missing."
            ),
        )


# ============================================================
# RULE 2
# DATASET MUST NOT BE EMPTY
# ============================================================

def validate_not_empty(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if df.empty:

        _add_failure(
            failures,
            dataset,
            "NON_EMPTY_DATASET",
            "CRITICAL",
            message=(
                "Dataset contains zero rows."
            ),
        )


# ============================================================
# RULE 3
# ID MUST NOT BE NULL
# ============================================================

def validate_id(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if "id" not in df.columns:
        return

    for index, value in df["id"].items():

        if (
            _is_missing(value)
            or not str(value).strip()
        ):

            _add_failure(
                failures,
                dataset,
                "ID_NOT_NULL",
                "CRITICAL",
                row=index,
                column="id",
                value=value,
                message=(
                    "ID cannot be null or empty."
                ),
            )


# ============================================================
# RULE 4
# ID MUST BE UNIQUE
# ============================================================

def validate_unique_id(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:
    """
    Check uniqueness only for valid IDs.

    Null/empty IDs are handled by ID_NOT_NULL
    and are not reported again as duplicates.
    """

    if "id" not in df.columns:
        return

    valid_ids = df[
        df["id"].notna()
        & df["id"].astype(str).str.strip().ne("")
    ]

    duplicated = valid_ids[
        valid_ids["id"].duplicated(
            keep=False
        )
    ]

    for index, value in duplicated["id"].items():

        _add_failure(
            failures,
            dataset,
            "ID_UNIQUE",
            "ERROR",
            row=index,
            column="id",
            value=value,
            message=(
                f"Duplicate non-null ID detected: "
                f"{value}"
            ),
        )


# ============================================================
# RULE 5
# COMPANY ID MUST NOT BE NULL
# ============================================================

def validate_company_id_not_null(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if "company_id" not in df.columns:
        return

    for index, value in df[
        "company_id"
    ].items():

        if (
            _is_missing(value)
            or not str(value).strip()
        ):

            _add_failure(
                failures,
                dataset,
                "COMPANY_ID_NOT_NULL",
                "CRITICAL",
                row=index,
                column="company_id",
                value=value,
                message=(
                    "company_id cannot be "
                    "null or empty."
                ),
            )


# ============================================================
# RULE 6
# YEAR MUST NOT BE NULL
# ============================================================

def validate_year_not_null(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if "year" not in df.columns:
        return

    for index, value in df[
        "year"
    ].items():

        if _is_missing(value):

            _add_failure(
                failures,
                dataset,
                "YEAR_NOT_NULL",
                "ERROR",
                row=index,
                column="year",
                value=value,
                message=(
                    "Year cannot be null."
                ),
            )


# ============================================================
# RULE 7
# YEAR RANGE
# ============================================================

def validate_year_range(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if "year" not in df.columns:
        return

    for index, value in df[
        "year"
    ].items():

        if _is_missing(value):
            continue

        numeric = _to_numeric(value)

        if numeric is None:

            _add_failure(
                failures,
                dataset,
                "YEAR_VALID",
                "ERROR",
                row=index,
                column="year",
                value=value,
                message=(
                    "Year is not a valid number."
                ),
            )

            continue

        year = int(numeric)

        if not 1900 <= year <= 2100:

            _add_failure(
                failures,
                dataset,
                "YEAR_RANGE",
                "ERROR",
                row=index,
                column="year",
                value=value,
                message=(
                    f"Year {year} is outside "
                    "the valid range 1900-2100."
                ),
            )


# ============================================================
# RULE 8
# NUMERIC VALUES
# ============================================================

def validate_numeric_columns(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    columns = NUMERIC_COLUMNS.get(
        dataset,
        [],
    )

    for column in columns:

        if column not in df.columns:
            continue

        for index, value in df[
            column
        ].items():

            if _is_missing(value):
                continue

            numeric = _to_numeric(value)

            if numeric is None:

                _add_failure(
                    failures,
                    dataset,
                    "NUMERIC_VALUE",
                    "ERROR",
                    row=index,
                    column=column,
                    value=value,
                    message=(
                        "Value must be numeric."
                    ),
                )


# ============================================================
# RULE 9
# PERCENTAGE RANGE
# ============================================================

def validate_percentage_range(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:
    """
    Validate percentage fields.

    Rule:
        Valid percentage range = -100 to +100.

    This keeps the validator consistent with the
    Day-03 unit test specification.
    """

    columns = PERCENTAGE_COLUMNS.get(
        dataset,
        [],
    )

    for column in columns:

        if column not in df.columns:
            continue

        for index, value in df[
            column
        ].items():

            if _is_missing(value):
                continue

            numeric = _to_numeric(value)

            if numeric is None:
                continue

            if abs(numeric) > 100:

                _add_failure(
                    failures,
                    dataset,
                    "PERCENTAGE_RANGE",
                    "ERROR",
                    row=index,
                    column=column,
                    value=value,
                    message=(
                        "Percentage value must "
                        "be between -100 and 100."
                    ),
                )


# ============================================================
# RULE 10
# COMPANY/YEAR DUPLICATES
# ============================================================

def validate_company_year_duplicates(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if "company_id" not in df.columns:
        return

    if "year" not in df.columns:
        return

    valid = df[
        df["company_id"].notna()
        & df["year"].notna()
    ].copy()

    if valid.empty:
        return

    duplicated = valid[
        valid.duplicated(
            subset=[
                "company_id",
                "year",
            ],
            keep=False,
        )
    ]

    for index, row in duplicated.iterrows():

        _add_failure(
            failures,
            dataset,
            "COMPANY_YEAR_UNIQUE",
            "ERROR",
            row=index,
            column="company_id,year",
            value=(
                f"{row['company_id']},"
                f"{row['year']}"
            ),
            message=(
                "Duplicate company/year "
                "record detected."
            ),
        )


# ============================================================
# RULE 11
# EPS MUST BE NUMERIC
# ============================================================

def validate_eps(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:
    """
    Negative EPS is valid.

    Companies can legitimately report
    negative EPS when they make losses.
    """

    if dataset != "profitandloss":
        return

    if "eps" not in df.columns:
        return

    for index, value in df[
        "eps"
    ].items():

        if _is_missing(value):
            continue

        numeric = _to_numeric(value)

        if numeric is None:

            _add_failure(
                failures,
                dataset,
                "EPS_NUMERIC",
                "ERROR",
                row=index,
                column="eps",
                value=value,
                message=(
                    "EPS must be numeric."
                ),
            )


# ============================================================
# RULE 12
# BALANCE SHEET CONSISTENCY
# ============================================================

def validate_balance_sheet(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    if dataset != "balancesheet":
        return

    required = {
        "total_assets",
        "total_liabilities",
    }

    if not required.issubset(
        df.columns
    ):
        return

    for index, row in df.iterrows():

        assets = _to_numeric(
            row["total_assets"]
        )

        liabilities = _to_numeric(
            row["total_liabilities"]
        )

        if (
            assets is None
            or liabilities is None
        ):
            continue

        if abs(
            assets - liabilities
        ) > 0.01:

            _add_failure(
                failures,
                dataset,
                "BALANCE_SHEET_BALANCED",
                "WARNING",
                row=index,
                column=(
                    "total_assets,"
                    "total_liabilities"
                ),
                value=(
                    f"{assets},"
                    f"{liabilities}"
                ),
                message=(
                    "Total assets and total "
                    "liabilities do not match."
                ),
            )


# ============================================================
# RULE 13
# URL FORMAT
# ============================================================

def validate_urls(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    url_columns = [
        "website",
        "chart_link",
        "annual_report",
    ]

    for column in url_columns:

        if column not in df.columns:
            continue

        for index, value in df[
            column
        ].items():

            if _is_missing(value):
                continue

            text = str(value).strip()

            if not text:
                continue

            if not (
                text.startswith(
                    "http://"
                )
                or text.startswith(
                    "https://"
                )
            ):

                _add_failure(
                    failures,
                    dataset,
                    "URL_FORMAT",
                    "WARNING",
                    row=index,
                    column=column,
                    value=value,
                    message=(
                        "URL should start with "
                        "http:// or https://."
                    ),
                )


# ============================================================
# RULE 14
# REQUIRED TEXT
# ============================================================

def validate_text_fields(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    required_text_columns = {

        "companies": [
            "company_name",
        ],

        "prosandcons": [
            "pros",
            "cons",
        ],
    }

    columns = (
        required_text_columns.get(
            dataset,
            [],
        )
    )

    for column in columns:

        if column not in df.columns:
            continue

        for index, value in df[
            column
        ].items():

            if (
                _is_missing(value)
                or not str(value).strip()
            ):

                _add_failure(
                    failures,
                    dataset,
                    "TEXT_NOT_EMPTY",
                    "WARNING",
                    row=index,
                    column=column,
                    value=value,
                    message=(
                        f"Text field '{column}' "
                        "is empty."
                    ),
                )


# ============================================================
# RULE 15
# COMPANY FOREIGN KEY
# ============================================================

def validate_company_references(
    datasets: dict[str, pd.DataFrame],
    failures: list[dict[str, Any]],
) -> None:

    if "companies" not in datasets:
        return

    companies = datasets[
        "companies"
    ]

    if "id" not in companies.columns:
        return

    valid_ids = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    child_datasets = [
        name
        for name, df in datasets.items()
        if (
            name != "companies"
            and "company_id" in df.columns
        )
    ]

    for dataset in child_datasets:

        df = datasets[dataset]

        for index, value in df[
            "company_id"
        ].items():

            if (
                _is_missing(value)
                or not str(value).strip()
            ):
                continue

            company_id = (
                str(value)
                .strip()
                .upper()
            )

            if company_id not in valid_ids:

                _add_failure(
                    failures,
                    dataset,
                    "COMPANY_ID_FOREIGN_KEY",
                    "CRITICAL",
                    row=index,
                    column="company_id",
                    value=value,
                    message=(
                        f"company_id '{value}' "
                        "does not exist in "
                        "companies.id."
                    ),
                )


# ============================================================
# RULE 16
# UNEXPECTED COLUMNS
# ============================================================

def validate_unexpected_columns(
    dataset: str,
    df: pd.DataFrame,
    failures: list[dict[str, Any]],
) -> None:

    expected = set(
        REQUIRED_COLUMNS.get(
            dataset,
            [],
        )
    )

    if not expected:
        return

    unexpected = sorted(
        set(df.columns) - expected
    )

    for column in unexpected:

        _add_failure(
            failures,
            dataset,
            "UNEXPECTED_COLUMN",
            "WARNING",
            column=column,
            message=(
                f"Unexpected column detected: "
                f"'{column}'."
            ),
        )


# ============================================================
# DATASET VALIDATION
# ============================================================

def validate_dataset(
    dataset: str,
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Validate one dataset.
    """

    failures: list[
        dict[str, Any]
    ] = []

    validate_required_columns(
        dataset,
        df,
        failures,
    )

    validate_not_empty(
        dataset,
        df,
        failures,
    )

    validate_id(
        dataset,
        df,
        failures,
    )

    validate_unique_id(
        dataset,
        df,
        failures,
    )

    validate_company_id_not_null(
        dataset,
        df,
        failures,
    )

    validate_year_not_null(
        dataset,
        df,
        failures,
    )

    validate_year_range(
        dataset,
        df,
        failures,
    )

    validate_numeric_columns(
        dataset,
        df,
        failures,
    )

    validate_percentage_range(
        dataset,
        df,
        failures,
    )

    validate_company_year_duplicates(
        dataset,
        df,
        failures,
    )

    validate_eps(
        dataset,
        df,
        failures,
    )

    validate_balance_sheet(
        dataset,
        df,
        failures,
    )

    validate_urls(
        dataset,
        df,
        failures,
    )

    validate_text_fields(
        dataset,
        df,
        failures,
    )

    validate_unexpected_columns(
        dataset,
        df,
        failures,
    )

    return failures


# ============================================================
# ALL DATASETS
# ============================================================

def validate_all_datasets(
    datasets: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Validate all seven datasets.
    """

    failures: list[
        dict[str, Any]
    ] = []

    for dataset, df in datasets.items():

        failures.extend(
            validate_dataset(
                dataset,
                df,
            )
        )

    validate_company_references(
        datasets,
        failures,
    )

    return pd.DataFrame(
        failures,
        columns=FAILURE_COLUMNS,
    )


# ============================================================
# SAVE REPORT
# ============================================================

def save_validation_report(
    failures: pd.DataFrame,
    output_path: Path = FAILURE_REPORT,
) -> Path:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    failures.to_csv(
        output_path,
        index=False,
    )

    return output_path


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    from src.etl.loader import (
        load_all_core_datasets,
    )

    print()
    print("=" * 60)
    print(
        "NIFTY 100 - DAY 03 "
        "DATA QUALITY VALIDATION"
    )
    print("=" * 60)
    print()

    print("Loading datasets...")

    datasets = (
        load_all_core_datasets()
    )

    print(
        f"Loaded {len(datasets)} datasets."
    )

    print()
    print("Running validation...")

    failures = (
        validate_all_datasets(
            datasets
        )
    )

    save_validation_report(
        failures
    )

    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    if failures.empty:

        print("STATUS   : PASSED")
        print("FAILURES : 0")

    else:

        print(
            "STATUS   : ISSUES FOUND"
        )

        print(
            f"FAILURES : {len(failures)}"
        )

        print()

        summary = (
            failures
            .groupby(
                [
                    "dataset",
                    "rule",
                    "severity",
                ]
            )
            .size()
            .sort_values(
                ascending=False
            )
        )

        print(
            summary.to_string()
        )

    print()
    print(
        "Report saved to:"
    )
    print(
        FAILURE_REPORT
    )
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()