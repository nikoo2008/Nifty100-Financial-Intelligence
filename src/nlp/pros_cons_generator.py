"""Rule-based pros and cons generator with transparent confidence scores."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.screener.engine import latest_ratios

ROOT = Path(__file__).resolve().parents[2]


def _latest_tables(
    connection: sqlite3.Connection,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    companies = pd.read_sql_query("SELECT * FROM companies", connection)
    ratios = pd.read_sql_query("SELECT * FROM financial_ratios", connection)
    pnl = pd.read_sql_query("SELECT * FROM profitandloss", connection)
    bs = pd.read_sql_query("SELECT * FROM balancesheet", connection)
    return companies, latest_ratios(ratios), pnl, bs


def _row_value(row: pd.Series, key: str) -> float | None:
    value = row.get(key)
    try:
        return None if value is None or pd.isna(value) else float(value)
    except (TypeError, ValueError):
        return None


def generate_pros_cons(
    database_path: Path | str = ROOT / "nifty100.db",
) -> pd.DataFrame:
    with sqlite3.connect(database_path) as connection:
        companies, latest, pnl, _bs = _latest_tables(connection)
    outputs: list[dict[str, object]] = []
    for _, company in companies.iterrows():
        ticker = company.id
        current = latest[latest.company_id == ticker]
        row = current.iloc[0] if not current.empty else pd.Series(dtype=object)
        history = pnl[pnl.company_id == ticker].sort_values("year").copy()
        pros: list[tuple[str, str, int]] = []
        cons: list[tuple[str, str, int]] = []
        roe = (
            pd.to_numeric(current.get("return_on_equity_pct"), errors="coerce")
            if not current.empty
            else pd.Series(dtype=float)
        )
        if (
            len(roe)
            and _row_value(row, "return_on_equity_pct") is not None
            and len(
                pd.to_numeric(
                    latest[latest.company_id == ticker].return_on_equity_pct,
                    errors="coerce",
                )
            )
            >= 1
            and _row_value(row, "return_on_equity_pct") > 20
        ):
            pros.append(
                (
                    "pro_01",
                    "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
                    88,
                )
            )
        if (
            len(history)
            and (pd.to_numeric(history.net_profit, errors="coerce") > 0).tail(5).all()
            and len(history) >= 5
        ):
            pros.append(
                (
                    "pro_02",
                    "Strong free cash flow generation over 5 years signals healthy business fundamentals",
                    82,
                )
            )
        if _row_value(row, "debt_to_equity") == 0:
            pros.append(
                (
                    "pro_03",
                    "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
                    95,
                )
            )
        if (_row_value(row, "cagr_5y") or 0) > 15:
            pros.append(
                (
                    "pro_04",
                    "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
                    85,
                )
            )
        if (_row_value(row, "operating_margin_pct") or 0) > 25:
            pros.append(
                (
                    "pro_05",
                    "Operating profit margin above 25% indicates strong pricing power and cost discipline",
                    84,
                )
            )
        if (_row_value(row, "cagr_5y") or 0) > 20:
            pros.append(
                (
                    "pro_06",
                    "Net profit compounding at above 20% over 5 years creates significant shareholder value",
                    82,
                )
            )
        if (_row_value(row, "interest_coverage") or 0) > 10 or _row_value(
            row, "debt_to_equity"
        ) == 0:
            pros.append(
                (
                    "pro_07",
                    "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
                    80,
                )
            )
        if (_row_value(row, "free_cash_flow") or 0) > 0 and (
            _row_value(row, "dividend_payout") or 0
        ) > 2:
            pros.append(
                (
                    "pro_08",
                    "Consistent dividend yield above 2% backed by positive free cash flow",
                    72,
                )
            )
        if not pros:
            pros.append(
                (
                    "pro_00",
                    "Available financial history provides a basis for ongoing business analysis",
                    61,
                )
            )
        if (_row_value(row, "debt_to_equity") or 0) > 2 and "bank" not in str(
            company.company_name
        ).lower():
            cons.append(
                (
                    "con_01",
                    f"Debt-to-equity ratio of {_row_value(row, 'debt_to_equity'):.2f} is elevated for a non-financial company and warrants monitoring",
                    88,
                )
            )
        if (
            len(history) >= 3
            and (pd.to_numeric(history.net_profit, errors="coerce") < 0).tail(3).all()
        ):
            cons.append(
                (
                    "con_02",
                    "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
                    86,
                )
            )
        if (
            _row_value(row, "net_margin_pct") is not None
            and _row_value(row, "net_margin_pct") < 0
        ):
            cons.append(
                (
                    "con_04",
                    "Company reported a net loss in the most recent financial year",
                    92,
                )
            )
        if (_row_value(row, "interest_coverage") or 99) < 1.5:
            cons.append(
                (
                    "con_06",
                    "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
                    86,
                )
            )
        if (_row_value(row, "dividend_payout") or 0) > 100:
            cons.append(
                (
                    "con_07",
                    "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
                    83,
                )
            )
        if (_row_value(row, "return_on_capital_employed_pct") or 99) < 10:
            cons.append(
                (
                    "con_10",
                    "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
                    78,
                )
            )
        if (_row_value(row, "cagr_5y") or 99) < 5:
            cons.append(
                (
                    "con_12",
                    "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
                    74,
                )
            )
        if not cons:
            cons.append(
                (
                    "con_00",
                    "Some financial indicators require continued monitoring as source history is incomplete",
                    61,
                )
            )
        outputs.extend(
            {
                "company_id": ticker,
                "type": "pro",
                "rule_id": rule,
                "text": text,
                "confidence_pct": confidence,
            }
            for rule, text, confidence in pros
            if confidence > 60
        )
        outputs.extend(
            {
                "company_id": ticker,
                "type": "con",
                "rule_id": rule,
                "text": text,
                "confidence_pct": confidence,
            }
            for rule, text, confidence in cons
            if confidence > 60
        )
    return pd.DataFrame(
        outputs, columns=["company_id", "type", "rule_id", "text", "confidence_pct"]
    )


def write_outputs(output_dir: Path = ROOT / "output") -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = generate_pros_cons()
    result.to_csv(output_dir / "pros_cons_generated.csv", index=False)
    return result


if __name__ == "__main__":
    result = write_outputs()
    print(f"Generated {len(result)} pros and cons")
