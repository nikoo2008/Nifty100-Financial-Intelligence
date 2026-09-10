import pandas as pd

from src.analytics.peer import build_peer_percentiles
from src.screener.engine import PRESETS, apply_screen, composite_quality_score


def sample():
    return pd.DataFrame(
        [
            {
                "company_id": "A",
                "year": 2024,
                "return_on_equity_pct": 10,
                "return_on_capital_employed_pct": 8,
                "debt_to_equity": 0.2,
                "interest_coverage": 5,
                "operating_margin_pct": 15,
                "net_margin_pct": 10,
                "asset_turnover": 1,
                "cash_conversion": 1,
                "cagr_5y": 10,
                "cagr_10y": 8,
            },
            {
                "company_id": "B",
                "year": 2024,
                "return_on_equity_pct": 20,
                "return_on_capital_employed_pct": 18,
                "debt_to_equity": 0.8,
                "interest_coverage": 3,
                "operating_margin_pct": 20,
                "net_margin_pct": 12,
                "asset_turnover": 2,
                "cash_conversion": 1.2,
                "cagr_5y": 12,
                "cagr_10y": 10,
            },
        ]
    )


def test_six_presets():
    assert len(PRESETS["presets"]) == 6


def test_custom_screen():
    assert len(apply_screen(sample(), {"min_roe": 15})) == 1


def test_max_threshold():
    assert len(apply_screen(sample(), {"max_debt_to_equity": 0.5})) == 1


def test_composite_score():
    assert composite_quality_score(sample())["quality_score"].notna().all()


def test_peer_rows():
    assert (
        len(
            build_peer_percentiles(
                sample(),
                pd.DataFrame({"id": ["A", "B"], "company_name": ["Alpha", "Beta"]}),
            )
        )
        == 2
    )


def test_peer_inverse_de():
    result = build_peer_percentiles(
        sample(), pd.DataFrame({"id": ["A", "B"], "company_name": ["Alpha", "Beta"]})
    )
    assert (
        result.loc[result.company_id == "A", "debt_to_equity_percentile"].iloc[0]
        > result.loc[result.company_id == "B", "debt_to_equity_percentile"].iloc[0]
    )


def test_missing_peer_group():
    result = build_peer_percentiles(
        sample().iloc[:1], pd.DataFrame({"id": ["A"], "company_name": ["Alpha"]})
    )
    assert result.peer_group.iloc[0] == "Industrials"
