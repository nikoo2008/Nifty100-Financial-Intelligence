"""Configurable preset and custom financial screeners."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from openpyxl.formatting.rule import ColorScaleRule

from src.analytics.peer import build_peer_percentiles, write_peer_outputs

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "screener_config.yaml"
PRESETS = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def latest_ratios(ratios: pd.DataFrame) -> pd.DataFrame:
    return (
        ratios.sort_values(["company_id", "year"])
        .drop_duplicates("company_id", keep="last")
        .copy()
    )


def apply_screen(ratios: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    frame = latest_ratios(ratios)
    for metric, threshold in thresholds.items():
        operator = "max" if metric.startswith("max_") else "min"
        metric_name = metric[4:] if metric.startswith(("min_", "max_")) else metric
        column = PRESETS.get("metrics", {}).get(metric_name, metric_name)
        if column not in frame:
            continue
        if operator == "max" or column in {"debt_to_equity", "liabilities_to_assets"}:
            frame = frame[pd.to_numeric(frame[column], errors="coerce") <= threshold]
        else:
            frame = frame[pd.to_numeric(frame[column], errors="coerce") >= threshold]
    return frame


def composite_quality_score(ratios: pd.DataFrame) -> pd.DataFrame:
    frame = latest_ratios(ratios)
    metrics = [
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "net_margin_pct",
        "interest_coverage",
        "cash_conversion",
        "cagr_5y",
        "debt_to_equity",
    ]
    scores = []
    for metric in metrics:
        values = pd.to_numeric(frame[metric], errors="coerce")
        lo, hi = values.quantile(0.10), values.quantile(0.90)
        clipped = values.clip(lo, hi)
        percentile = clipped.rank(pct=True) * 100
        scores.append(100 - percentile if metric == "debt_to_equity" else percentile)
    frame["quality_score"] = pd.concat(scores, axis=1).mean(axis=1, skipna=True)
    return frame.sort_values("quality_score", ascending=False)


def generate_screener_outputs(ratios: pd.DataFrame, companies: pd.DataFrame) -> None:
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    merged = ratios.merge(
        companies[["id", "company_name"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )
    score = composite_quality_score(merged)
    with pd.ExcelWriter(output / "screener_output.xlsx", engine="openpyxl") as writer:
        for name, thresholds in PRESETS["presets"].items():
            apply_screen(merged, thresholds).to_excel(
                writer, sheet_name=name[:31], index=False
            )
        for sheet in writer.book.worksheets:
            if sheet.max_row > 1 and sheet.max_column > 1:
                sheet.freeze_panes = "A2"
                sheet.auto_filter.ref = sheet.dimensions
                sheet.conditional_formatting.add(
                    f"B2:{sheet.cell(sheet.max_row, sheet.max_column).coordinate}",
                    ColorScaleRule(
                        start_type="min",
                        start_color="F8696B",
                        mid_type="percentile",
                        mid_value=50,
                        mid_color="FFEB84",
                        end_type="max",
                        end_color="63BE7B",
                    ),
                )
    percentiles = build_peer_percentiles(merged, companies)
    write_peer_outputs(percentiles)
    return score
