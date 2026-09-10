# Project Deliverables Tracker

Updated 2026-09-10. Statuses are based on artifacts currently present in the repository.

| ID | Sprint | Deliverable | Location | Status |
|---|---|---|---|---|
| D-01 | Sprint 1 | nifty100.db | `nifty100.db` | Done |
| D-02 | Sprint 1 | load_audit.csv | `output/load_audit.csv` | Done |
| D-03 | Sprint 1 | validation_failures.csv | `reports/validation_failures.csv` | Done (actual generated location) |
| D-04 | Sprint 1 | exploratory_queries.sql | `notebooks/exploratory_queries.sql` | Done |
| D-05 | Sprint 2 | financial_ratios table | `nifty100.db` -> `financial_ratios` | Done |
| D-06 | Sprint 2 | capital_allocation.csv | `output/capital_allocation.csv` | Done |
| D-07 | Sprint 3 | screener_output.xlsx | `output/screener_output.xlsx` | Done |
| D-08 | Sprint 3 | screener_config.yaml | `config/screener_config.yaml` | Done |
| D-09 | Sprint 3 | peer_comparison.xlsx | `output/peer_comparison.xlsx` | Done |
| D-10 | Sprint 3 | Radar charts | `reports/radar_charts/` | Done (source contains 20 generated charts) |
| D-11 | Sprint 4 | Streamlit Dashboard (8 Screens) | `src/dashboard/app.py` | Done |
| D-12 | Sprint 4 | valuation_summary.xlsx | `output/valuation_summary.xlsx` | Done |
| D-13 | Sprint 5 | cashflow_intelligence.xlsx | `output/cashflow_intelligence.xlsx` | Done |
| D-14 | Sprint 5 | pros_cons_generated.csv | `output/pros_cons_generated.csv` | Done |
| D-15 | Sprint 5 | analysis_parsed.csv | `output/analysis_parsed.csv` | Done |
| D-16 | Sprint 5 | Company tearsheets | `reports/tearsheets/` | Done with caveat (100 generated; 1 source company skipped for insufficient history) |
| D-17 | Sprint 5 | Sector reports | `reports/sector/` | Done (11 reports) |
| D-18 | Sprint 5 | Portfolio Summary PDF | `reports/portfolio/` | Done |
| D-19 | Sprint 6 | cluster_labels.csv | `output/cluster_labels.csv` | Done (101 assignments across 5 clusters) |
| D-20 | Sprint 6 | FastAPI Server (16 Endpoints) | `src/api/main.py` | Done |
| D-21 | Sprint 6 | pytest_report.html | `reports/pytest_report.html` | Done (82 tests, 0 failures) |
| D-22 | Sprint 6 | analyst_guide.pdf | `docs/analyst_guide.pdf` | Done (11 pages) |
| D-23 | Sprint 6 | acceptance_checklist.pdf | `docs/acceptance_checklist.pdf` | Done |

## Source-data caveats

- The supplied source master contains 101 companies rather than the planning target of 92.
- `AGTL` is recorded in `output/skipped_tearsheets.csv` because it has fewer than three P&L years.
- The original validation output is generated at `reports/validation_failures.csv`; the tracker records that actual path.

## Quick Reference

```powershell
make load
make ratios
make test
make report
make dashboard
make api
make clean
```

## Important Rules

- Use `pd.read_excel(path, header=1)` for core Excel files.
- Normalize `company_id` before joins.
- Store monetary values in INR Crore.
- Skip Financials when applying the D/E screener filter.
- Label negative-base CAGR cases as TURNAROUND.
- Display Debt Free when interest expense is zero.
- Label simulated stock-price and market-cap datasets as SIMULATED.
- Run `make test` before commits; zero test failures are required.
