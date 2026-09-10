"""Company and company-history API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.api.common import (
    ROOT,
    companies_frame,
    filtered_years,
    json_records,
    latest_ratios,
    read_table,
)

router = APIRouter(tags=["companies"])


def _company(ticker: str):
    frame = companies_frame()
    match = frame[frame.id.str.upper() == ticker.upper()]
    if match.empty:
        raise HTTPException(404, "Ticker not found")
    return match.iloc[0]


@router.get("/companies")
def list_companies(
    sector: str | None = None,
    market_cap_category: str | None = None,
    search: str | None = None,
):
    """Return searchable company summaries."""
    frame = companies_frame()
    latest = latest_ratios()
    frame = frame.merge(
        latest[
            ["company_id", "return_on_equity_pct", "return_on_capital_employed_pct"]
        ],
        left_on="id",
        right_on="company_id",
        how="left",
    )
    if sector:
        frame = frame[frame.broad_sector.str.casefold() == sector.casefold()]
    if search:
        frame = frame[
            frame.company_name.str.contains(search, case=False, na=False)
            | frame.id.str.contains(search, case=False, na=False)
        ]
    frame = frame.drop(columns=["company_id"], errors="ignore").rename(
        columns={
            "id": "company_id",
            "return_on_equity_pct": "roe_pct",
            "return_on_capital_employed_pct": "roce_pct",
        }
    )
    return json_records(
        frame[
            [
                "company_id",
                "company_name",
                "broad_sector",
                "sub_sector",
                "roe_pct",
                "roce_pct",
            ]
        ]
    )


@router.get("/companies/{ticker}")
def company_profile(ticker: str):
    """Return a complete company profile and latest KPIs."""
    company = _company(ticker)
    ratios = latest_ratios()
    latest = ratios[ratios.company_id == company.id]
    result = company.to_dict()
    result["latest_kpis"] = json_records(latest)
    return result


@router.get("/companies/{ticker}/pl")
def company_pl(ticker: str, from_year: str | None = None, to_year: str | None = None):
    """Return filtered profit and loss history."""
    _company(ticker)
    return json_records(
        filtered_years(
            read_table(
                "profitandloss", "WHERE company_id = ? ORDER BY year", (ticker,)
            ),
            from_year,
            to_year,
        )
    )


@router.get("/companies/{ticker}/bs")
def company_bs(ticker: str, from_year: str | None = None, to_year: str | None = None):
    """Return filtered balance sheet history."""
    _company(ticker)
    return json_records(
        filtered_years(
            read_table("balancesheet", "WHERE company_id = ? ORDER BY year", (ticker,)),
            from_year,
            to_year,
        )
    )


@router.get("/companies/{ticker}/cashflow")
def company_cashflow(
    ticker: str, from_year: str | None = None, to_year: str | None = None
):
    """Return filtered cash-flow history."""
    _company(ticker)
    return json_records(
        filtered_years(
            read_table("cashflow", "WHERE company_id = ? ORDER BY year", (ticker,)),
            from_year,
            to_year,
        )
    )


@router.get("/companies/{ticker}/ratios")
def company_ratios(ticker: str, year: int | None = None):
    """Return computed annual ratios."""
    _company(ticker)
    frame = read_table(
        "financial_ratios", "WHERE company_id = ? ORDER BY year", (ticker,)
    )
    if year is not None:
        frame = frame[frame.year == year]
    return json_records(frame)


@router.get("/companies/{ticker}/tearsheet")
def company_tearsheet(ticker: str):
    """Download a generated company tearsheet PDF."""
    _company(ticker)
    path = ROOT / "reports" / "tearsheets" / f"{ticker.upper()}_tearsheet.pdf"
    if not path.exists():
        raise HTTPException(404, "Tearsheet unavailable")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
