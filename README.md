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