import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios, latest

st.header("Capital allocation map")
companies = get_companies()
data = latest(get_ratios()).merge(
    companies[["id", "company_name", "sector"]],
    left_on="company_id",
    right_on="id",
    how="left",
)
if data.empty:
    st.info("Capital allocation data is not available.")
    st.stop()
pattern = data.capital_allocation_pattern.fillna("insufficient_data")
counts = pattern.value_counts().rename_axis("pattern").reset_index(name="companies")
figure = px.treemap(
    counts,
    path=["pattern"],
    values="companies",
    title="Companies by capital allocation pattern",
)
st.plotly_chart(figure, use_container_width=True)
selected = st.selectbox("Pattern", counts.pattern.tolist())
st.dataframe(
    data.loc[pattern == selected, ["company_id", "company_name", "sector"]],
    hide_index=True,
    use_container_width=True,
)
