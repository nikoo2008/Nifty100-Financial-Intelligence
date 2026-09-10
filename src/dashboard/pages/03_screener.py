import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios, latest

st.header("Screener")
companies = get_companies()
frame = latest(get_ratios()).merge(
    companies[["id", "company_name", "sector"]],
    left_on="company_id",
    right_on="id",
    how="left",
)
metrics = {
    "ROE min": ("return_on_equity_pct", -50.0, 100.0),
    "D/E max": ("debt_to_equity", 0.0, 20.0),
    "FCF min": ("free_cash_flow", -100000.0, 100000.0),
    "Revenue CAGR min": ("cagr_5y", -100.0, 100.0),
    "PAT CAGR min": ("cagr_5y", -100.0, 100.0),
    "OPM min": ("operating_margin_pct", -100.0, 100.0),
    "P/E max": ("pe", 0.0, 100.0),
    "P/B max": ("pb", 0.0, 20.0),
    "Dividend Yield min": ("dividend_payout", 0.0, 100.0),
    "ICR min": ("interest_coverage", 0.0, 100.0),
}
presets = {
    "Quality": {"return_on_equity_pct": 15, "debt_to_equity": 2},
    "Value": {"debt_to_equity": 3},
    "Growth": {"cagr_5y": 10},
    "Dividend": {"dividend_payout": 20},
    "Debt-Free": {"debt_to_equity": 0.2},
    "Turnaround": {"net_margin_pct": 0},
}
choice = st.sidebar.selectbox("Preset", ["Custom"] + list(presets))
thresholds = {}
for label, (column, low, high) in metrics.items():
    default = presets.get(choice, {}).get(
        column, low if label.endswith("min") else high
    )
    thresholds[column] = st.sidebar.slider(
        label, float(low), float(high), float(default)
    )
result = frame.copy()
for column, threshold in thresholds.items():
    if column in result:
        values = pd.to_numeric(result[column], errors="coerce")
        result = (
            result[values >= threshold]
            if column not in {"debt_to_equity", "pe", "pb"}
            else result[values <= threshold]
        )
result["composite_score"] = (
    pd.to_numeric(result.get("return_on_equity_pct"), errors="coerce").rank(pct=True)
    * 100
)
columns = ["company_id", "company_name", "sector", "composite_score"] + [
    c for c, _, _ in metrics.values() if c in result
]
result = result.loc[:, ~result.columns.duplicated()][
    [c for c in columns if c in result]
]
st.caption(f"{len(result)} companies match your filters")
st.download_button(
    "Download CSV", result.to_csv(index=False), "screener_results.csv", "text/csv"
)
st.dataframe(result, hide_index=True, use_container_width=True)
