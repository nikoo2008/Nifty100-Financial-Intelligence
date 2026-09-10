import pandas as pd
import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_companies, get_ratios, latest, metric_value
from src.dashboard.utils.ui import kpis

st.header("Market overview")
year = st.sidebar.selectbox("Analysis year", list(range(2019, 2025)), index=5)
companies = get_companies(); ratios = get_ratios(year=year)
if ratios.empty: ratios = latest(get_ratios())
frame = ratios.merge(companies[["id", "company_name", "sector"]], left_on="company_id", right_on="id", how="left")
median = lambda c: metric_value(pd.to_numeric(frame[c], errors="coerce").median()) if c in frame else "N/A"
kpis({"Average ROE": f"{pd.to_numeric(frame.get('return_on_equity_pct'), errors='coerce').mean():.1f}%" if not frame.empty else "N/A", "Median P/E": "N/A", "Median D/E": median("debt_to_equity"), "Total Companies": len(companies), "Median Revenue CAGR 5yr": median("cagr_5y"), "Debt-Free Companies": int((pd.to_numeric(frame.get("debt_to_equity"), errors="coerce") == 0).sum()) if not frame.empty else 0})
left, right = st.columns(2)
with left:
    st.subheader("Sector distribution")
    if not companies.empty: st.plotly_chart(px.pie(companies, names="sector", title="Companies by sector", hole=.48), use_container_width=True)
with right:
    st.subheader("Top quality companies")
    if not frame.empty:
        score = frame.assign(composite_score=pd.to_numeric(frame.return_on_equity_pct, errors="coerce").rank(pct=True) * 100).sort_values("composite_score", ascending=False)
        st.dataframe(score[["company_id", "company_name", "sector", "composite_score"]].head(5), hide_index=True, use_container_width=True)
