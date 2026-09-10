import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_peers

st.header("Peer comparison")
peers = get_peers()
companies = get_companies()
if peers.empty:
    st.info("Peer data is not available.")
    st.stop()
groups = sorted(peers.peer_group.dropna().unique())
group = st.selectbox("Peer group", groups)
data = peers[peers.peer_group == group].merge(
    companies[["id", "company_name"]], left_on="company_id", right_on="id", how="left"
)
ticker = st.selectbox(
    "Benchmark company",
    data.company_id.tolist(),
    format_func=lambda x: (
        f"{data.loc[data.company_id == x, 'company_name'].iloc[0]} ({x})"
    ),
)
metrics = [
    ("ROE", "return_on_equity_pct_percentile"),
    ("ROCE", "return_on_capital_employed_pct_percentile"),
    ("D/E", "debt_to_equity_percentile"),
    ("ICR", "interest_coverage_percentile"),
    ("OPM", "operating_margin_pct_percentile"),
    ("NPM", "net_margin_pct_percentile"),
    ("Turnover", "asset_turnover_percentile"),
    ("Cash conversion", "cash_conversion_percentile"),
]
selected = data[data.company_id == ticker].iloc[0]
average = data[[column for _, column in metrics]].mean(numeric_only=True)
figure = go.Figure()
figure.add_trace(
    go.Scatterpolar(
        r=[selected.get(c, 0) or 0 for _, c in metrics]
        + [selected.get(metrics[0][1], 0) or 0],
        theta=[n for n, _ in metrics] + [metrics[0][0]],
        fill="toself",
        name=ticker,
    )
)
figure.add_trace(
    go.Scatterpolar(
        r=[average.get(c, 0) for _, c in metrics] + [average.get(metrics[0][1], 0)],
        theta=[n for n, _ in metrics] + [metrics[0][0]],
        name="Peer average",
    )
)
figure.update_layout(
    polar={"radialaxis": {"range": [0, 100]}},
    margin={"l": 10, "r": 10, "t": 30, "b": 10},
)
st.plotly_chart(figure, use_container_width=True)
st.dataframe(
    data[["company_id", "company_name"] + [c for _, c in metrics]],
    hide_index=True,
    use_container_width=True,
)
