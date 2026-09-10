"""KMeans archetype clustering and portfolio statistics."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def _load_latest(database_path: Path = DB_PATH) -> pd.DataFrame:
    """Load latest company features from the normalized SQLite database."""
    with sqlite3.connect(database_path) as connection:
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", connection)
        pd.read_sql_query(
            "SELECT company_id, year, sales FROM profitandloss", connection
        )
        companies = pd.read_sql_query(
            "SELECT id AS company_id, company_name FROM companies", connection
        )
    ratios = ratios.sort_values("year").drop_duplicates("company_id", keep="last")
    annual = pd.read_sql_query(
        "SELECT company_id, year, operating_activity, investing_activity FROM cashflow",
        sqlite3.connect(database_path),
    )
    annual = annual.sort_values("year")
    annual["fcf"] = pd.to_numeric(
        annual.operating_activity, errors="coerce"
    ) + pd.to_numeric(annual.investing_activity, errors="coerce")
    fcf_growth = []
    for ticker, frame in annual.groupby("company_id"):
        values = frame.fcf.dropna()
        growth = np.nan
        if len(values) >= 2 and values.iloc[0] > 0 and values.iloc[-1] > 0:
            years = max(int(frame.year.iloc[-1] - frame.year.iloc[0]), 1)
            growth = ((values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1) * 100
        fcf_growth.append({"company_id": ticker, "fcf_cagr_5yr": growth})
    growth = pd.DataFrame(fcf_growth)
    result = companies.merge(ratios, on="company_id", how="left").merge(
        growth, on="company_id", how="left"
    )
    result["revenue_cagr_5yr"] = pd.to_numeric(result.get("cagr_5y"), errors="coerce")
    result["operating_profit_margin_pct"] = pd.to_numeric(
        result.get("operating_margin_pct"), errors="coerce"
    )
    return result


def _cluster_names(centers: pd.DataFrame) -> dict[int, str]:
    """Assign descriptive archetype names from cluster center rankings."""
    names = {}
    for cluster_id, center in centers.iterrows():
        (
            center["return_on_equity_pct"]
            + center["revenue_cagr_5yr"]
            + center["fcf_cagr_5yr"]
            - center["debt_to_equity"] * 5
        )
        if (
            center["return_on_equity_pct"]
            >= centers.return_on_equity_pct.quantile(0.75)
            and center["revenue_cagr_5yr"] >= centers.revenue_cagr_5yr.median()
        ):
            name = "High-Quality Compounders"
        elif (
            center["debt_to_equity"] >= centers.debt_to_equity.quantile(0.75)
            and center["return_on_equity_pct"] <= centers.return_on_equity_pct.median()
        ):
            name = "Distressed or Turnaround"
        elif (
            center["debt_to_equity"] <= centers.debt_to_equity.quantile(0.25)
            and center["return_on_equity_pct"] >= centers.return_on_equity_pct.median()
        ):
            name = "Defensive Dividend Payers"
        elif center["revenue_cagr_5yr"] >= centers.revenue_cagr_5yr.quantile(0.75):
            name = "Emerging Growth"
        else:
            name = "Value Cyclicals"
        names[int(cluster_id)] = name
    if len(set(names.values())) < len(names):
        ordered = sorted(names, key=lambda key: float(centers.loc[key].sum()))
        fallback = [
            "Distressed or Turnaround",
            "Value Cyclicals",
            "Defensive Dividend Payers",
            "Emerging Growth",
            "High-Quality Compounders",
        ]
        names.update(
            {cluster: fallback[index] for index, cluster in enumerate(ordered)}
        )
    return names


def build_clusters(
    database_path: Path = DB_PATH,
    output_dir: Path = ROOT / "output",
    reports_dir: Path = ROOT / "reports",
) -> pd.DataFrame:
    """Fit five reproducible KMeans clusters and write analysis artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    frame = _load_latest(database_path)
    feature_frame = frame[FEATURES].apply(pd.to_numeric, errors="coerce")
    sectors = (
        frame.company_id.map(frame.set_index("company_id").company_name)
        .fillna("")
        .map(
            lambda value: (
                "Financials"
                if any(
                    word in str(value).lower()
                    for word in ("bank", "finance", "insurance")
                )
                else "Diversified"
            )
        )
    )
    for feature in FEATURES:
        feature_frame[feature] = feature_frame[feature].fillna(
            feature_frame.assign(sector=sectors)
            .groupby("sector")[feature]
            .transform("median")
        )
        feature_frame[feature] = (
            feature_frame[feature].fillna(feature_frame[feature].median()).fillna(0)
        )
    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_frame)
    model = KMeans(n_clusters=5, random_state=42, n_init=20)
    labels = model.fit_predict(scaled)
    centers = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_), columns=FEATURES
    )
    names = _cluster_names(centers)
    distances = model.transform(scaled).min(axis=1)
    result = frame[["company_id"]].copy()
    result["cluster_id"] = labels
    result["cluster_name"] = [names[label] for label in labels]
    result["distance_from_centroid"] = distances
    result.to_csv(output_dir / "cluster_labels.csv", index=False)
    profile = (
        feature_frame.assign(cluster_id=labels)
        .groupby("cluster_id")[FEATURES]
        .agg(["mean", "median"])
    )
    profile.to_csv(output_dir / "cluster_profiles.csv")
    elbow = []
    for k in range(2, 11):
        elbow.append(
            KMeans(n_clusters=k, random_state=42, n_init=10).fit(scaled).inertia_
        )
    plt.figure(figsize=(7, 4))
    plt.plot(range(2, 11), elbow, marker="o")
    plt.axvline(5, color="red", linestyle="--")
    plt.xlabel("Clusters")
    plt.ylabel("Inertia")
    plt.title("KMeans elbow plot")
    plt.tight_layout()
    plt.savefig(reports_dir / "elbow_plot.png", dpi=150)
    plt.close()
    stats = feature_frame.describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).T.rename(
        columns={
            "10%": "P10",
            "25%": "P25",
            "50%": "P50",
            "75%": "P75",
            "90%": "P90",
            "mean": "Mean",
            "std": "Std",
        }
    )[["P10", "P25", "P50", "P75", "P90", "Mean", "Std"]]
    stats.to_csv(output_dir / "portfolio_stats.csv")
    kpis = [
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "debt_to_equity",
        "operating_margin_pct",
        "net_margin_pct",
        "interest_coverage",
        "free_cash_flow",
        "cash_conversion",
        "cagr_5y",
        "cagr_10y",
    ]
    with sqlite3.connect(database_path) as connection:
        kpi_frame = pd.read_sql_query(
            f"SELECT {', '.join(kpis)} FROM financial_ratios", connection
        ).apply(pd.to_numeric, errors="coerce")
    correlation = kpi_frame.corr(method="pearson")
    try:
        import seaborn as sns

        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation, annot=True, fmt=".2f", cmap="vlag", center=0)
        plt.tight_layout()
        plt.savefig(reports_dir / "correlation_heatmap.png", dpi=150)
        plt.close()
    except ImportError:
        plt.figure(figsize=(10, 8))
        plt.imshow(correlation, cmap="coolwarm", aspect="auto")
        plt.colorbar()
        plt.xticks(range(len(kpis)), kpis, rotation=90)
        plt.yticks(range(len(kpis)), kpis)
        plt.tight_layout()
        plt.savefig(reports_dir / "correlation_heatmap.png", dpi=150)
        plt.close()
    z = feature_frame.assign(company_id=frame.company_id, broad_sector=sectors).copy()
    outliers = []
    for sector, group in z.groupby("broad_sector"):
        for feature in FEATURES:
            values = group[feature]
            std = values.std()
            zscore = (
                (values - values.mean()) / std
                if std and not pd.isna(std)
                else values * 0
            )
            for index in group.index[zscore.abs() > 3]:
                outliers.append(
                    {
                        "company_id": z.loc[index, "company_id"],
                        "broad_sector": sector,
                        "metric": feature,
                        "value": z.loc[index, feature],
                        "z_score": zscore.loc[index],
                    }
                )
    pd.DataFrame(outliers).to_csv(output_dir / "outlier_report.csv", index=False)
    return result


if __name__ == "__main__":
    print(f"Clustered {len(build_clusters())} companies")
