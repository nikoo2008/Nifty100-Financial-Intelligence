"""
Day 03 - Data Quality Validator Tests
"""

import pandas as pd

from src.etl.validator import (
    validate_all_datasets,
    validate_dataset,
)

# ============================================================
# TEST 1 — EMPTY DATASET
# ============================================================


def test_empty_dataset_is_detected():

    df = pd.DataFrame()

    failures = validate_dataset(
        "companies",
        df,
    )

    rules = {failure["rule"] for failure in failures}

    assert "NON_EMPTY_DATASET" in rules


# ============================================================
# TEST 2 — MISSING REQUIRED COLUMN
# ============================================================


def test_missing_required_column_is_detected():

    df = pd.DataFrame(
        {
            "id": ["RELIANCE"],
            "company_name": ["Reliance Industries"],
        }
    )

    failures = validate_dataset(
        "companies",
        df,
    )

    rules = {failure["rule"] for failure in failures}

    assert "REQUIRED_COLUMN" in rules


# ============================================================
# TEST 3 — DUPLICATE ID
# ============================================================


def test_duplicate_id_is_detected():

    df = pd.DataFrame(
        {
            "id": [
                "RELIANCE",
                "RELIANCE",
            ],
            "company_logo": [
                "logo1",
                "logo2",
            ],
            "company_name": [
                "Reliance Industries",
                "Reliance Industries",
            ],
            "chart_link": [
                "https://example.com/1",
                "https://example.com/2",
            ],
            "about_company": [
                "Company",
                "Company",
            ],
            "website": [
                "https://example.com",
                "https://example.com",
            ],
        }
    )

    failures = validate_dataset(
        "companies",
        df,
    )

    rules = {failure["rule"] for failure in failures}

    assert "ID_UNIQUE" in rules


# ============================================================
# TEST 4 — INVALID YEAR
# ============================================================


def test_invalid_year_is_detected():

    df = pd.DataFrame(
        {
            "id": ["1"],
            "company_id": ["RELIANCE"],
            "year": [1800],
        }
    )

    failures = validate_dataset(
        "profitandloss",
        df,
    )

    rules = {failure["rule"] for failure in failures}

    assert "YEAR_RANGE" in rules


# ============================================================
# TEST 5 — NON-NUMERIC VALUE
# ============================================================


def test_non_numeric_value_is_detected():

    df = pd.DataFrame(
        {
            "id": ["1"],
            "company_id": ["RELIANCE"],
            "year": [2024],
            "sales": ["INVALID"],
        }
    )

    failures = validate_dataset(
        "profitandloss",
        df,
    )

    rules = {failure["rule"] for failure in failures}

    assert "NUMERIC_VALUE" in rules


# ============================================================
# TEST 6 — PERCENTAGE OUT OF RANGE
# ============================================================


def test_percentage_out_of_range_is_detected():

    df = pd.DataFrame(
        {
            "id": ["1"],
            "company_id": ["RELIANCE"],
            "year": [2024],
            "sales": [1000],
            "expenses": [500],
            "operating_profit": [500],
            "opm_percentage": [150],
            "other_income": [10],
            "interest": [20],
            "depreciation": [30],
            "profit_before_tax": [460],
            "tax_percentage": [20],
            "net_profit": [368],
            "eps": [10],
            "dividend_payout": [20],
        }
    )

    failures = validate_dataset(
        "profitandloss",
        df,
    )

    rules = {failure["rule"] for failure in failures}

    assert "PERCENTAGE_RANGE" in rules


# ============================================================
# TEST 7 — FOREIGN KEY
# ============================================================


def test_company_foreign_key_is_detected():

    companies = pd.DataFrame(
        {
            "id": ["RELIANCE"],
            "company_name": ["Reliance Industries"],
        }
    )

    profitandloss = pd.DataFrame(
        {
            "id": ["1"],
            "company_id": ["UNKNOWN"],
            "year": [2024],
        }
    )

    datasets = {
        "companies": companies,
        "profitandloss": profitandloss,
    }

    failures = validate_all_datasets(datasets)

    rules = set(failures["rule"].tolist())

    assert "COMPANY_ID_FOREIGN_KEY" in rules


# ============================================================
# TEST 8 — VALID COMPANY DATA
# ============================================================


def test_valid_dataset_has_no_critical_failures():

    df = pd.DataFrame(
        {
            "id": ["RELIANCE"],
            "company_logo": ["logo"],
            "company_name": ["Reliance Industries"],
            "chart_link": ["https://example.com/chart"],
            "about_company": ["Company description"],
            "website": ["https://example.com"],
        }
    )

    failures = validate_dataset(
        "companies",
        df,
    )

    critical_failures = [
        failure for failure in failures if failure["severity"] == "CRITICAL"
    ]

    assert critical_failures == []
