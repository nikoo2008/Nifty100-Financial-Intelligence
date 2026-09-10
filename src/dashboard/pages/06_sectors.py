import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies, get_pl, get_ratios, latest

st.header("Sector analysis")
companies = get_companies()
sector = st.selectbox("Sector", sorted(companies.sector.unique()))
members = companies[companies.sector == sector]
ratios = latest(get_ratios()).merge(
    members[["id", "company_name", "sector"]],
    left_on="company_id",
    right_on="id",
    how="inner",
)
pl = latest(get_pl()).merge(
    members[["id"]], left_on="company_id", right_on="id", how="inner"
)
if not ratios.empty:
    figure = px.scatter(
        ratios.merge(pl[["company_id", "sales"]], on="company_id", how="left"),
        x="sales",
        y="return_on_equity_pct",
        size="sales",
        color="company_id",
        hover_name="company_name",
        title=f"{sector}: revenue vs ROE",
    )
    figure.update_layout(margin={"l": 10, "r": 10, "t": 50, "b": 10})
    st.plotly_chart(figure, use_container_width=True)
    median = (
        ratios.select_dtypes("number")
        .median()
        .loc[
            [
                c
                for c in [
                    "return_on_equity_pct",
                    "return_on_capital_employed_pct",
                    "net_margin_pct",
                    "debt_to_equity",
                ]
                if c in ratios
            ]
        ]
        .reset_index()
    )
    median.columns = ["metric", "median"]
    st.plotly_chart(
        px.bar(median, x="metric", y="median", title="Sector median KPIs"),
        use_container_width=True,
    )
else:
    st.info("No sector data is available.")
