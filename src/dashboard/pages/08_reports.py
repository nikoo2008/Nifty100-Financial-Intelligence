import requests
import streamlit as st

from src.dashboard.utils.db import get_companies

st.header("Annual reports")
companies = get_companies()
query = st.text_input("Search company or ticker")
filtered = (
    companies
    if not query
    else companies[
        companies.company_name.str.contains(query, case=False, na=False)
        | companies.id.str.contains(query.upper(), case=False, na=False)
    ]
)
if filtered.empty:
    st.warning("Ticker not found - please try another")
    st.stop()
ticker = st.selectbox(
    "Company",
    filtered.id,
    format_func=lambda x: (
        f"{filtered.loc[filtered.id == x, 'company_name'].iloc[0]} ({x})"
    ),
)
from src.dashboard.utils.db import _read

docs = _read(
    "SELECT year, annual_report FROM documents WHERE company_id = ? ORDER BY year DESC",
    (ticker,),
)
if docs.empty:
    st.info("No annual report records are available.")
for _, row in docs.iterrows():
    url = row.annual_report
    if not url or str(url).lower() == "nan":
        st.markdown(f"**{row.year}**  :red[Report unavailable]")
        continue
    try:
        response = requests.head(str(url), timeout=3, allow_redirects=True)
        available = response.status_code < 400
    except requests.RequestException:
        available = False
    if available:
        st.markdown(f"**{row.year}**  [Open BSE annual report]({url})")
    else:
        st.markdown(f"**{row.year}**  :red[Report unavailable]")
