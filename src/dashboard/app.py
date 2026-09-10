"""Main entry point for the Nifty 100 Streamlit dashboard."""
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Nifty 100 Analytics", layout="wide", initial_sidebar_state="expanded")

PAGES = Path(__file__).parent / "pages"
pages = [
    st.Page(PAGES / "01_home.py", title="Home", icon=":material/home:"),
    st.Page(PAGES / "02_profile.py", title="Company Profile", icon=":material/business:"),
    st.Page(PAGES / "03_screener.py", title="Screener", icon=":material/filter_alt:"),
    st.Page(PAGES / "04_peers.py", title="Peers", icon=":material/groups:"),
    st.Page(PAGES / "05_trends.py", title="Trends", icon=":material/show_chart:"),
    st.Page(PAGES / "06_sectors.py", title="Sectors", icon=":material/domain:"),
    st.Page(PAGES / "07_capital.py", title="Capital Allocation", icon=":material/account_tree:"),
    st.Page(PAGES / "08_reports.py", title="Annual Reports", icon=":material/article:"),
]
st.title("Nifty 100 Analytics")
st.caption("Financial intelligence for the source universe loaded by the ETL pipeline.")
navigation = st.navigation(pages)
navigation.run()
