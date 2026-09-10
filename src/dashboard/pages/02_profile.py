import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies, get_pl, get_ratios, latest, metric_value
from src.dashboard.utils.ui import kpis

st.header("Company profile")
companies = get_companies()
query = st.text_input("Search company or ticker", placeholder="TCS or Tata Consultancy")
filtered = companies if not query else companies[companies.company_name.str.contains(query, case=False, na=False) | companies.id.str.contains(query.upper(), case=False, na=False)]
if filtered.empty: st.warning("Ticker not found - please try another"); st.stop()
ticker = st.selectbox("Company", filtered.id, format_func=lambda value: f"{filtered.loc[filtered.id == value, 'company_name'].iloc[0]} ({value})")
company = companies[companies.id == ticker].iloc[0]; ratios = get_ratios(ticker); pl = get_pl(ticker)
latest_row = latest(ratios, ticker).iloc[0] if not ratios.empty else None
st.subheader(company.company_name)
st.caption(f"{company.sector} | NSE ticker: {ticker}")
st.write(company.about_company or "Company description is not available in the source data.")
value = lambda c: metric_value(None if latest_row is None else latest_row.get(c))
kpis({"ROE": value("return_on_equity_pct") + "%", "ROCE": value("return_on_capital_employed_pct") + "%", "Net margin": value("net_margin_pct") + "%", "D/E": value("debt_to_equity"), "Revenue CAGR 5yr": value("cagr_5y") + "%", "FCF": value("free_cash_flow")})
if pl.empty: st.info("Data available note: no profit and loss history was loaded."); st.stop()
fig = go.Figure(); fig.add_bar(x=pl.year, y=pl.sales, name="Revenue"); fig.add_bar(x=pl.year, y=pl.net_profit, name="Net profit"); fig.update_layout(title="Revenue and net profit", barmode="group", margin=dict(l=10,r=10,t=50,b=10)); st.plotly_chart(fig, use_container_width=True)
if not ratios.empty:
    fig = go.Figure(); fig.add_trace(go.Scatter(x=ratios.year, y=ratios.return_on_equity_pct, name="ROE")); fig.add_trace(go.Scatter(x=ratios.year, y=ratios.return_on_capital_employed_pct, name="ROCE", yaxis="y2")); fig.update_layout(title="ROE and ROCE", yaxis_title="ROE %", yaxis2=dict(title="ROCE %", overlaying="y", side="right"), margin=dict(l=10,r=10,t=50,b=10)); st.plotly_chart(fig, use_container_width=True)
st.subheader("Pros and cons")
st.info("Pros and cons are shown when present in the loaded source dataset.")
