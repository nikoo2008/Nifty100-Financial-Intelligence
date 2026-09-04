"""
Unit tests for Nifty 100 ETL normalisation utilities.

Day 02 requirements:
- 20 normalize_year tests
- 20 normalize_ticker tests
"""

from src.etl.normaliser import normalize_ticker, normalize_year


# ============================================================
# normalize_year — 20 tests
# ============================================================


def test_year_integer():
    assert normalize_year(2024) == 2024


def test_year_string():
    assert normalize_year("2024") == 2024


def test_year_float():
    assert normalize_year(2024.0) == 2024


def test_year_month_year():
    assert normalize_year("Mar 2024") == 2024


def test_year_month_year_lowercase():
    assert normalize_year("mar 2024") == 2024


def test_year_fy_prefix():
    assert normalize_year("FY2024") == 2024


def test_year_fy_with_space():
    assert normalize_year("FY 2024") == 2024


def test_year_iso_date():
    assert normalize_year("2024-03-31") == 2024


def test_year_slash_date():
    assert normalize_year("31/03/2024") == 2024


def test_year_month_day_date():
    assert normalize_year("31-Mar-2024") == 2024


def test_year_two_digit_24():
    assert normalize_year("Mar-24") == 2024


def test_year_two_digit_23():
    assert normalize_year("FY23") == 2023


def test_year_whitespace():
    assert normalize_year(" 2024 ") == 2024


def test_year_embedded_text():
    assert normalize_year("Financial Year 2024") == 2024


def test_year_none():
    assert normalize_year(None) is None


def test_year_empty_string():
    assert normalize_year("") is None


def test_year_invalid_text():
    assert normalize_year("Not Available") is None


def test_year_out_of_range_low():
    assert normalize_year(1800) is None


def test_year_out_of_range_high():
    assert normalize_year(2200) is None


def test_year_boolean():
    assert normalize_year(True) is None


# ============================================================
# normalize_ticker — 20 tests
# ============================================================


def test_ticker_uppercase():
    assert normalize_ticker("hdfcbank") == "HDFCBANK"


def test_ticker_already_uppercase():
    assert normalize_ticker("HDFCBANK") == "HDFCBANK"


def test_ticker_mixed_case():
    assert normalize_ticker("HdFcBaNk") == "HDFCBANK"


def test_ticker_leading_space():
    assert normalize_ticker(" HDFCBANK") == "HDFCBANK"


def test_ticker_trailing_space():
    assert normalize_ticker("HDFCBANK ") == "HDFCBANK"


def test_ticker_both_spaces():
    assert normalize_ticker(" HDFCBANK ") == "HDFCBANK"


def test_ticker_internal_spaces():
    assert normalize_ticker("HDFC BANK") == "HDFCBANK"


def test_ticker_multiple_spaces():
    assert normalize_ticker("HDFC   BANK") == "HDFCBANK"


def test_ticker_hyphen():
    assert normalize_ticker("HDFC-BANK") == "HDFCBANK"


def test_ticker_underscore():
    assert normalize_ticker("HDFC_BANK") == "HDFCBANK"


def test_ticker_mixed_separators():
    assert normalize_ticker("HDFC-BANK_TEST") == "HDFCBANKTEST"


def test_ticker_none():
    assert normalize_ticker(None) is None


def test_ticker_empty():
    assert normalize_ticker("") is None


def test_ticker_whitespace_only():
    assert normalize_ticker("   ") is None


def test_ticker_numeric_string():
    assert normalize_ticker("12345") == "12345"


def test_ticker_numeric_value():
    assert normalize_ticker(12345) == "12345"


def test_ticker_float_nan():
    assert normalize_ticker(float("nan")) is None


def test_ticker_special_case():
    assert normalize_ticker(" infy ") == "INFY"


def test_ticker_sbilife():
    assert normalize_ticker("sbilife") == "SBILIFE"


def test_ticker_tcs():
    assert normalize_ticker("tcs") == "TCS"