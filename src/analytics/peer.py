"""Peer-group percentile rankings and comparison workbook."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PEER_METRICS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "debt_to_equity",
    "interest_coverage",
    "operating_margin_pct",
    "net_margin_pct",
    "asset_turnover",
    "cash_conversion",
    "cagr_5y",
    "cagr_10y",
]
INVERSE = {"debt_to_equity"}


def build_peer_percentiles(
    ratios: pd.DataFrame,
    companies: pd.DataFrame,
    peer_groups: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frame = (
        ratios.sort_values(["company_id", "year"])
        .drop_duplicates("company_id", keep="last")
        .copy()
    )
    names = companies.set_index("id")["company_name"]
    frame["company_name"] = frame["company_id"].map(names)
    frame["peer_group"] = pd.NA
    if peer_groups is not None and not peer_groups.empty:
        groups = peer_groups.drop_duplicates("company_id").set_index("company_id")
        frame["peer_group"] = frame["company_id"].map(groups["peer_group_name"])
    frame["peer_group"] = frame["peer_group"].fillna(
        frame["company_name"]
        .fillna("")
        .map(
            lambda x: (
                "Financials"
                if any(w in str(x).lower() for w in ("bank", "finance", "insurance"))
                else "Industrials"
            )
        )
    )
    rows = []
    for group, part in frame.groupby("peer_group"):
        for _, row in part.iterrows():
            out = {"company_id": row.company_id, "peer_group": group}
            for metric in PEER_METRICS:
                values = pd.to_numeric(part[metric], errors="coerce")
                value = pd.to_numeric(pd.Series([row[metric]]), errors="coerce").iloc[0]
                percentile = (
                    values.rank(pct=True).loc[row.name] * 100
                    if pd.notna(value)
                    else None
                )
                out[metric] = value
                out[metric + "_percentile"] = (
                    100 - percentile
                    if metric in INVERSE and percentile is not None
                    else percentile
                )
            rows.append(out)
    return pd.DataFrame(rows)


def write_peer_outputs(
    percentiles: pd.DataFrame, output_dir: Path = PROJECT_ROOT / "output"
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(
        output_dir / "peer_comparison.xlsx", engine="openpyxl"
    ) as writer:
        for group, data in percentiles.groupby("peer_group"):
            data.to_excel(writer, sheet_name=str(group)[:31], index=False)
            data[PEER_METRICS].median().to_frame("median").to_excel(
                writer, sheet_name=str(group)[:31], startrow=len(data) + 2
            )
    radar_dir = PROJECT_ROOT / "reports" / "radar_charts"
    radar_dir.mkdir(parents=True, exist_ok=True)
    percentile_cols = [m + "_percentile" for m in PEER_METRICS]
    for _, row in percentiles.head(20).iterrows():
        values = [0 if pd.isna(row[c]) else row[c] for c in percentile_cols]
        angles = list(range(len(values))) + [0]
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, values + [values[0]])
        ax.fill(angles, values + [values[0]], alpha=0.2)
        ax.set_ylim(0, 100)
        ax.set_title(str(row.company_id))
        fig.savefig(radar_dir / f"{row.company_id}.png")
        plt.close(fig)
