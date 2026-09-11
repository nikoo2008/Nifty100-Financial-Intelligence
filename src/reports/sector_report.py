"""Generate compact sector summary PDFs from the source database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]


def generate_sector_reports(
    database_path: Path = ROOT / "nifty100.db",
    output_dir: Path = ROOT / "reports" / "sector",
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    paths: list[Path] = []
    with sqlite3.connect(database_path) as c:
        companies = pd.read_sql_query("SELECT id, company_name FROM companies", c)
        sectors = pd.read_sql_query(
            "SELECT company_id, broad_sector FROM sectors", c
        )
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", c)
    companies = companies.merge(sectors, left_on="id", right_on="company_id", how="left")
    companies["sector"] = companies["broad_sector"].fillna("Diversified")
    companies = companies[["id", "company_name", "sector"]]
    latest = (
        ratios.sort_values("year")
        .drop_duplicates("company_id", keep="last")
        .merge(companies, left_on="company_id", right_on="id", how="left")
    )
    for sector, group in companies.groupby("sector"):
        path = output_dir / f"{sector.lower().replace(' ', '_')}_report.pdf"
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
            pageCompression=0,
        )
        story = [
            Paragraph(f"<b>{sector} sector report</b>", styles["Title"]),
            Spacer(1, 4 * mm),
        ]
        metrics = (
            latest[latest.sector == sector][
                [
                    "return_on_equity_pct",
                    "return_on_capital_employed_pct",
                    "net_margin_pct",
                    "debt_to_equity",
                    "cagr_5y",
                    "free_cash_flow",
                ]
            ]
            .median(numeric_only=True)
            .round(2)
            .to_frame("median")
            .reset_index()
        )
        story.append(
            Table(
                [["Metric", "Median"]] + metrics.values.tolist(),
                colWidths=[80 * mm, 45 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#132238")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ]
                ),
            )
        )
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph("Companies and latest available metrics", styles["Heading2"])
        )
        view = latest[latest.sector == sector]
        rows = [["Ticker", "Company", "ROE", "ROCE", "NPM", "D/E", "CAGR", "FCF"]] + [
            [
                str(r.company_id),
                str(r.company_name)[:28],
                r.return_on_equity_pct,
                r.return_on_capital_employed_pct,
                r.net_margin_pct,
                r.debt_to_equity,
                r.cagr_5y,
                r.free_cash_flow,
            ]
            for _, r in view.iterrows()
        ]
        story.append(
            Table(
                rows,
                colWidths=[
                    20 * mm,
                    58 * mm,
                    15 * mm,
                    15 * mm,
                    15 * mm,
                    15 * mm,
                    15 * mm,
                    20 * mm,
                ],
                repeatRows=1,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#132238")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.2, colors.lightgrey),
                        ("FONTSIZE", (0, 0), (-1, -1), 6),
                    ]
                ),
            )
        )
        doc.build(story)
        paths.append(path)
    return paths


if __name__ == "__main__":
    print(f"Generated {len(generate_sector_reports())} sector reports")
