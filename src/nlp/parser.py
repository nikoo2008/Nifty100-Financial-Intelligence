"""Parse CAGR-style text fields from the analysis source."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.analytics.ratios import build_financial_ratios
from src.etl.loader import load_all_core_datasets

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.IGNORECASE)
FIELDS = (
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
)
ROOT = Path(__file__).resolve().parents[2]


def parse_analysis(analysis: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    parsed: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for _, row in analysis.iterrows():
        for field in FIELDS:
            text = "" if pd.isna(row.get(field)) else str(row.get(field))
            match = PATTERN.search(text)
            if match:
                parsed.append(
                    {
                        "company_id": row.company_id,
                        "metric_type": field,
                        "period_years": int(match.group(1)),
                        "value_pct": float(match.group(2)),
                    }
                )
            else:
                failures.append(
                    {
                        "company_id": row.company_id,
                        "metric_type": field,
                        "raw_text": text,
                        "reason": "pattern_not_matched",
                    }
                )
    return pd.DataFrame(
        parsed, columns=["company_id", "metric_type", "period_years", "value_pct"]
    ), pd.DataFrame(
        failures, columns=["company_id", "metric_type", "raw_text", "reason"]
    )


def cross_validate(
    parsed: pd.DataFrame, datasets: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    ratios = build_financial_ratios(datasets)
    latest = ratios.sort_values("year").drop_duplicates("company_id", keep="last")
    checks: list[dict[str, object]] = []
    mapping = {"compounded_sales_growth": "cagr_5y", "compounded_profit_growth": None}
    for _, row in parsed.iterrows():
        computed_column = mapping.get(row.metric_type)
        if computed_column is None:
            continue
        computed = latest.loc[latest.company_id == row.company_id, computed_column]
        if computed.empty or pd.isna(computed.iloc[0]) or row.period_years != 5:
            continue
        divergence = abs(float(row.value_pct) - float(computed.iloc[0]))
        if divergence > 5:
            checks.append(
                {
                    "company_id": row.company_id,
                    "metric_type": row.metric_type,
                    "period_years": row.period_years,
                    "source_value_pct": row.value_pct,
                    "computed_value_pct": computed.iloc[0],
                    "divergence_pct": divergence,
                    "manual_review": True,
                }
            )
    return pd.DataFrame(checks)


def write_outputs(
    output_dir: Path = ROOT / "output",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets = load_all_core_datasets()
    parsed, failures = parse_analysis(datasets["analysis"])
    parsed.to_csv(output_dir / "analysis_parsed.csv", index=False)
    failures.to_csv(output_dir / "parse_failures.csv", index=False)
    cross_validate(parsed, datasets).to_csv(
        output_dir / "analysis_cross_validation.csv", index=False
    )
    return parsed, failures


if __name__ == "__main__":
    parsed, failures = write_outputs()
    print(f"Parsed {len(parsed)} entries; {len(failures)} failures")
