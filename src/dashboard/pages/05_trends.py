import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_ratios
from src.dashboard.utils.ui import company_picker

st.header("Trend analysis")
ticker = company_picker(); data = get_ratios(ticker) if ticker else get_ratios()
metric_map = {"ROE": "return_on_equity_pct", "ROCE": "return_on_capital_employed_pct", "Net margin": "net_margin_pct", "Operating margin": "operating_margin_pct", "Free cash flow": "free_cash_flow", "Revenue CAGR": "cagr_5y"}
selected = st.multiselect("Metrics (up to 3)", list(metric_map), default=["ROE", "ROCE"], max_selections=3)
columns = [metric_map[item] for item in selected if metric_map[item] in data]
if not data.empty and columns:
    figure = px.line(data, x="year", y=columns, markers=True, title=f"{ticker} trends"); figure.update_layout(hovermode="x unified", margin=dict(l=10,r=10,t=50,b=10)); st.plotly_chart(figure, use_container_width=True)
else: st.info("Select a company and at least one metric with available data.")
