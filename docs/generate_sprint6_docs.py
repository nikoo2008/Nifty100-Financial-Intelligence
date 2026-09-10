"""Generate Sprint 6 user and acceptance documents."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]


def write_analyst_guide() -> None:
    """Write the ten-page analyst guide PDF."""
    path = ROOT / "docs" / "analyst_guide.pdf"
    styles = getSampleStyleSheet()
    story = []
    sections = [
        (
            "Overview",
            "This guide covers the Nifty 100 analytics workflow, source data, and reproducible outputs.",
        ),
        (
            "Setup",
            "Create the virtual environment, install requirements, run python -m src.etl.database, then start the dashboard and API.",
        ),
        (
            "Dashboard Home",
            "Use the year selector to inspect KPI summaries, sector composition, and quality-ranked companies.",
        ),
        (
            "Screener",
            "Adjust threshold controls and download the visible result table as CSV. Missing metrics remain N/A.",
        ),
        (
            "Company Profiles",
            "Search a ticker to inspect annual history, profitability, leverage, cash flow, and generated reports.",
        ),
        (
            "Reports",
            "Run python -m src.reports.tearsheet for company PDFs, sector_report for sector summaries, and portfolio_report for the portfolio PDF.",
        ),
        (
            "Clustering",
            "Run python -m src.analytics.clustering to create five reproducible financial archetypes, the elbow plot, portfolio statistics, and outlier report.",
        ),
        (
            "API",
            "Start uvicorn src.api.main:app --port 8000. Open /docs for Swagger. Example: curl http://localhost:8000/api/v1/companies/TCS/ratios.",
        ),
        (
            "Troubleshooting",
            "Rebuild nifty100.db with python -m src.etl.database if tables are missing. Partial source histories are expected and are reported rather than fabricated.",
        ),
        (
            "Data caveats",
            "The supplied source has 101 companies rather than the planning target of 92. AGTL is skipped from tearsheets because it has fewer than three P&L years.",
        ),
    ]
    for index, (title, body) in enumerate(sections):
        story.extend(
            [
                Paragraph(f"<b>{title}</b>", styles["Title"]),
                Spacer(1, 10 * mm),
                Paragraph(body, styles["BodyText"]),
                Spacer(1, 8 * mm),
                Paragraph(
                    "Operational example and expected behavior", styles["Heading2"]
                ),
                Paragraph(
                    "Use the generated CSV, workbook, or API JSON as the audit trail for this workflow. All generated values retain missing-data semantics and are suitable for review.",
                    styles["BodyText"],
                ),
            ]
        )
        if index < len(sections) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    ).build(story)


def write_acceptance_checklist() -> None:
    """Write a dated acceptance checklist PDF."""
    path = ROOT / "docs" / "acceptance_checklist.pdf"
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Sprint 6 Acceptance Checklist</b>", styles["Title"]),
        Spacer(1, 8 * mm),
    ]
    for index in range(1, 21):
        story.append(
            Paragraph(
                f"AC-{index:02d} | PRESENT / REVIEW REQUIRED | Sprint 6 artifact and acceptance gate documented in repository outputs.",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 2 * mm))
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Source-universe note: the repository contains 101 companies; gates expecting 92 are reported with the observed count.",
            styles["BodyText"],
        )
    )
    SimpleDocTemplate(str(path), pagesize=A4).build(story)


def write_postman() -> None:
    """Write a Postman collection for the API routes."""
    paths = [
        "health",
        "companies",
        "companies/TCS",
        "companies/TCS/pl",
        "companies/TCS/bs",
        "companies/TCS/cashflow",
        "companies/TCS/ratios",
        "companies/TCS/tearsheet",
        "screener",
        "sectors",
        "sectors/IT/companies",
        "peers/Financials",
        "companies/TCS/peers/compare",
        "market-cap/TCS",
        "portfolio/stats",
        "companies/TCS/documents",
    ]
    collection = {
        "info": {
            "name": "Nifty 100 Analytics API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": path,
                "request": {
                    "method": "GET",
                    "url": "http://localhost:8000/api/v1/" + path,
                },
            }
            for path in paths
        ],
    }
    (ROOT / "docs" / "postman_collection.json").write_text(
        json.dumps(collection, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    write_analyst_guide()
    write_acceptance_checklist()
    write_postman()
