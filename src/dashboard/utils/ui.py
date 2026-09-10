"""Small presentation helpers shared by dashboard pages."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st
from .db import get_companies, get_ratios, latest, metric_value


def company_options() -> list[str]:
    companies = get_companies()
    return companies.id.tolist() if not companies.empty else []


def company_picker(label: str = "Company") -> str | None:
    companies = get_companies()
    if companies.empty: return None
    choices = companies.assign(label=companies.company_name + " (" + companies.id + ")")
    selected = st.selectbox(label, choices.label.tolist())
    return selected.rsplit(" (", 1)[-1].rstrip(")")


def kpis(values: dict[str, object]) -> None:
    columns = st.columns(len(values))
    for column, (label, value) in zip(columns, values.items()):
        column.metric(label, value)


def company_frame(ticker: str) -> pd.DataFrame:
    return latest(get_ratios(ticker), ticker)


def line_chart(frame: pd.DataFrame, x: str, y: list[str], title: str):
    available = [column for column in y if column in frame and frame[column].notna().any()]
    if not available: st.info("Data is not available for this company."); return
    figure = px.line(frame, x=x, y=available, markers=True, title=title)
    figure.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(figure, use_container_width=True)


def safe_text(value: object) -> str:
    return "N/A" if value is None or pd.isna(value) else str(value)
