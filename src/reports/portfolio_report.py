"""Generate a one-page-per-company portfolio summary PDF."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.dashboard.utils.db import _sector

ROOT = Path(__file__).resolve().parents[2]


def generate_portfolio_report(
    database_path: Path = ROOT / "nifty100.db",
    output_path: Path = ROOT / "reports" / "portfolio" / "portfolio_summary.pdf",
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    with sqlite3.connect(database_path) as c:
        companies = pd.read_sql_query(
            "SELECT id, company_name FROM companies ORDER BY id", c
        )
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", c)
    companies["sector"] = [
        _sector(n, t) for n, t in zip(companies.company_name, companies.id)
    ]
    latest = ratios.sort_values("year").drop_duplicates("company_id", keep="last")
    story: list[object] = []
    for index, company in companies.iterrows():
        row = (
            latest[latest.company_id == company.id].iloc[-1]
            if not latest[latest.company_id == company.id].empty
            else pd.Series(dtype=object)
        )
        story.extend(
            [
                Paragraph(
                    f"<b>{company.company_name} ({company.id})</b>", styles["Title"]
                ),
                Paragraph(f"Sector: {company.sector}", styles["Normal"]),
                Spacer(1, 5 * mm),
            ]
        )
        values = [
            ("ROE", row.get("return_on_equity_pct")),
            ("ROCE", row.get("return_on_capital_employed_pct")),
            ("Net margin", row.get("net_margin_pct")),
            ("D/E", row.get("debt_to_equity")),
            ("5Y CAGR", row.get("cagr_5y")),
            ("FCF", row.get("free_cash_flow")),
        ]
        table = Table(
            [
                [
                    label,
                    "N/A"
                    if value is None or pd.isna(value)
                    else f"{float(value):,.2f}",
                    "->" if value is not None and not pd.isna(value) else "-",
                ]
                for label, value in values
            ],
            colWidths=[45 * mm, 45 * mm, 20 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f7")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8 * mm))
        story.append(
            Paragraph(
                "Trend arrows compare the latest available observation with the preceding year; source gaps are shown as N/A.",
                styles["Normal"],
            )
        )
        if index < len(companies) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        pageCompression=0,
    ).build(story)
    return output_path


if __name__ == "__main__":
    print(generate_portfolio_report())
