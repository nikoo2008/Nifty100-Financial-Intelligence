# Nifty100 Financial Intelligence

## Sprint 1 status

SPIRIT 1 / SPRINT 1 is complete. The ETL reads genuine Excel workbooks and TSV files misnamed `.xlsx`, normalizes the seven supplied datasets, validates them, and loads `nifty100.db` with primary and foreign-key constraints.

The source master contains 101 companies. This is documented as an observed source characteristic; records were not removed to force the original specification's count of 92.

## Run the pipeline

From the project root:

```powershell
python -m src.etl.database
python -m src.etl.validator
pytest tests/
```

Equivalent Make targets are `make db`, `make validate`, and `make test` where Make is available. The database load writes `output/load_audit.csv` and `output/manual_data_quality_review.csv`; validation writes `reports/validation_failures.csv`. Exploratory SQL is in `notebooks/exploratory_queries.sql`.

The database loader enables SQLite foreign keys and runs `PRAGMA foreign_key_check` before completing. The manual review covers ABB, HDFCBANK, M&M, SBILIFE, and TCS.

The final validation run reproduces 1,192 source-quality findings in `reports/validation_failures.csv` (including warnings and errors for duplicate company-years, missing years, malformed numeric values, URL formatting, and empty text). These are reported transparently and were not suppressed or resolved by deleting valid records. No company foreign-key failures were reported.

## Sprint 2 outputs

`src/analytics/ratios.py`, `cagr.py`, and `cashflow_kpis.py` calculate profitability, leverage, efficiency, cash-flow, and 3/5/10-year CAGR KPIs. The database load adds `financial_ratios`, writes `output/capital_allocation.csv`, and logs undefined calculations to `output/ratio_edge_cases.log`. Financial institutions receive an explicit carve-out for ROCE because their debt is operating funding. Current ratio is not calculated because the source has no current-assets/current-liabilities fields.

## Sprint 3 outputs

The screener supports 15 configured metrics, six presets, custom `min_`/`max_` thresholds, winsorized quality scoring, and a financials debt/equity carve-out. The peer engine writes percentile rankings, peer medians, and radar charts from available company history. Companies without peer data are retained with missing percentiles; no peer values are fabricated.

## Sprint 4 dashboard and valuation

Start the dashboard from the project root with:

```powershell
streamlit run src/dashboard/app.py
```

The eight screens are Home, Company Profile, Screener, Peers, Trends, Sectors, Capital Allocation, and Annual Reports. The screener supports live thresholds and CSV download. Pages show `N/A` or an availability note when a source metric or year is missing.

Run valuation output generation with:

```powershell
python -m src.analytics.valuation
```

This writes `output/valuation_summary.xlsx` and `output/valuation_flags.csv`. The supplied source currently contains 101 companies, so outputs retain 101 rows rather than deleting records to force a 92-company count. If `data/raw/market_cap.xlsx` is supplied, its market-cap column is used; otherwise the valuation module uses latest book equity as a deterministic proxy and keeps the required output columns.

## Sprint 5 cash flow, NLP, and reports

Generate the Sprint 5 artifacts with:

```powershell
python -m src.nlp.parser
python -m src.nlp.pros_cons_generator
python -c "from src.analytics.cashflow_kpis import write_cashflow_outputs; write_cashflow_outputs()"
python -m src.analytics.capital_allocation
python -m src.reports.tearsheet
python -m src.reports.sector_report
python -m src.reports.portfolio_report
```

The source universe contains 101 companies. `AGTL` is logged in `output/skipped_tearsheets.csv` because it has fewer than three P&L years; 100 two-page tearsheets and 11 sector reports are generated. NLP output uses confidence-filtered, transparent rules and includes a minimum evidence/fallback signal for companies with incomplete source histories.

## Sprint 6 clustering, API, and sign-off

Generate the clustering artifacts with:

```powershell
python -m src.analytics.clustering
```

Start the API with:

```powershell
uvicorn src.api.main:app --port 8000
```

The API exposes 16 read-only endpoints under `/api/v1`, with Swagger at `/docs`. OpenAPI and Postman exports are written to `docs/openapi.json` and `docs/postman_collection.json`. Run `pytest` for the complete regression suite. Acceptance results are recorded in `output/acceptance_gates.csv`; source-universe exceptions are reported as FAIL rather than hidden.