"""
umap_viz.py — UMAP 2D dimensionality reduction with Plotly interactive scatter.

Produces an interactive HTML scatter plot colored by cluster.
Hover shows ticker + cluster. No distance calculations from UMAP coords.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects  # noqa: F401 — used in type annotation
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "argus-shared" / "src"))

SLEEVE_EXPENSE_RATIOS = {
    "SPY": 0.0945,
    "QQQ": 0.20,
    "XLF": 0.09,
    "GLD": 0.40,
    "SLV": 0.50,
    "SHY": 0.15,
    "SHV": 0.15,
    "IEF": 0.15,
    "IEI": 0.15,
    "TLT": 0.15,
    "TLH": 0.15,
    "LQD": 0.14,
    "VCIT": 0.04,
    "VNQ": 0.12,
    "IYR": 0.39,
    "DJP": 0.70,
    "GSG": 0.75,
    "DBC": 0.87,
    "VYM": 0.06,
    "DVY": 0.38,
    "SDY": 0.35,
    "VWO": 0.08,
    "EEM": 0.68,
}
COUNTRY_EXPOSURE = {
    "VTI": 1.0,
    "VOO": 1.0,
    "SPY": 1.0,
    "QQQ": 1.0,
    "IWM": 1.0,
    "VIG": 1.0,
    "SCHD": 1.0,
    "ESGU": 1.0,
    "XLK": 1.0,
    "XLF": 1.0,
    "XLE": 1.0,
    "XLV": 1.0,
    "XLI": 1.0,
    "VEA": 0.0,
    "EFA": 0.0,
    "VWO": 0.0,
    "EEM": 0.0,
    "BND": 1.0,
    "AGG": 1.0,
    "TLT": 1.0,
    "LQD": 1.0,
    "GLD": 1.0,
    "SLV": 1.0,
}
SECTOR_EXPOSURE = {
    "VTI": 0.3,
    "VOO": 0.3,
    "SPY": 0.3,
    "QQQ": 0.5,
    "XLK": 0.9,
    "IWM": 0.4,
    "VIG": 0.4,
    "SCHD": 0.4,
    "VEA": 0.0,
    "VWO": 0.0,
    "EEM": 0.0,
    "EFA": 0.0,
    "XLF": 0.8,
    "XLE": 0.9,
    "XLV": 0.9,
    "XLI": 0.9,
    "BND": 0.0,
    "AGG": 0.0,
    "TLT": 0.0,
    "LQD": 0.0,
    "GLD": 0.0,
    "SLV": 0.0,
    "ESGU": 0.3,
}


def load_xray_data() -> pd.DataFrame:
    cache_dir = Path(__file__).resolve().parents[5] / "apps" / "argus" / "data"
    prices, stats = {}, {}
    with open(cache_dir / "etf_prices.csv") as f:
        for row in csv.DictReader(f):
            ticker = row.pop("ticker")
            prices[ticker] = [float(v) for v in row.values() if v]
    with open(cache_dir / "etf_stats.csv") as f:
        for row in csv.DictReader(f):
            stats[row["ticker"]] = {
                "expense_ratio": float(row.get("expense_ratio", 0)),
                "dividend_yield": float(row.get("dividend_yield", 0)),
                "aum": float(row.get("aum", 0)),
                "avg_volume": int(row.get("avg_volume", 0)),
            }

    tickers = sorted(prices.keys())
    feat_names = [
        "country_exposure",
        "sector_exposure",
        "expense_ratio",
        "volatility_252d",
        "momentum_126d",
        "liquidity",
        "yield",
        "corr_to_spy",
    ]
    raw = {f: [] for f in feat_names}
    spy_prices = prices.get("SPY", [])
    spy_rets = (
        np.diff(spy_prices) / np.array(spy_prices[:-1]) if len(spy_prices) > 1 else np.array([])
    )

    for ticker in tickers:
        p = np.array(prices[ticker])
        rets = np.diff(p) / p[:-1] if len(p) > 1 else np.array([])
        s = stats.get(ticker, {})
        raw["country_exposure"].append(COUNTRY_EXPOSURE.get(ticker, 0.5))
        raw["sector_exposure"].append(SECTOR_EXPOSURE.get(ticker, 0.0))
        er = s.get("expense_ratio", 0.0)
        if er == 0.0:
            er = SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001)
        raw["expense_ratio"].append(er)
        raw["volatility_252d"].append(
            float(np.std(rets) * np.sqrt(252)) if len(rets) >= 20 else 0.0
        )
        if len(rets) >= 126:
            raw["momentum_126d"].append(float(np.prod(1 + rets[-126:]) - 1))
        elif len(rets) >= 20:
            raw["momentum_126d"].append(float(np.prod(1 + rets) - 1))
        else:
            raw["momentum_126d"].append(0.0)
        aum = s.get("aum", 1.0)
        avg_vol = s.get("avg_volume", 0)
        last_price = float(p[-1]) if len(p) > 0 else 0.0
        liq = (avg_vol * last_price / (aum * 1e9)) if aum > 0 and avg_vol > 0 else 0.0
        raw["liquidity"].append(liq)
        raw["yield"].append(s.get("dividend_yield", 0.0))
        if len(rets) >= 126 and len(spy_rets) >= 126:
            er126, sr = rets[-126:], spy_rets[-126:]
            corr = (
                float(np.corrcoef(er126, sr)[0, 1]) if np.std(er126) > 0 and np.std(sr) > 0 else 0.0
            )
        else:
            corr = 0.0
        raw["corr_to_spy"].append(corr if np.isfinite(corr) else 0.0)

    return pd.DataFrame(raw, index=tickers).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def compute_umap(df: pd.DataFrame, n_neighbors: int = 5, min_dist: float = 0.3):
    """Compute UMAP 2D coordinates."""
    try:
        import umap
    except ImportError:
        raise ImportError("umap-learn is required. Install: pip install umap-learn") from None

    scaler = StandardScaler()
    X = scaler.fit_transform(df.values)
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="euclidean",
        random_state=42,
    )
    coords = reducer.fit_transform(X)
    return coords


def make_plotly_scatter(
    coords: np.ndarray,
    tickers: list[str],
    cluster_labels: list[int],
    n_clusters: int,
    title: str,
) -> plotly.graph_objects.Figure:  # type: ignore[attr-defined]
    """Build an interactive Plotly scatter plot."""
    import plotly.express as px
    import plotly.graph_objects as go

    fig = go.Figure()

    # Define a color palette
    colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2 + px.colors.qualitative.Pastel1

    for cluster_id in sorted(set(cluster_labels)):
        mask = [c == cluster_id for c in cluster_labels]
        cluster_coords = [
            (tickers[i], float(coords[i, 0]), float(coords[i, 1])) for i, m in enumerate(mask) if m
        ]

        fig.add_trace(
            go.Scatter(
                x=[c[1] for c in cluster_coords],
                y=[c[2] for c in cluster_coords],
                mode="markers+text",
                marker=dict(size=12, color=colors[cluster_id % len(colors)], opacity=0.8),
                text=[c[0] for c in cluster_coords],
                textposition="top center",
                textfont=dict(size=9),
                hoverinfo="text",
                hovertext=[f"{c[0]}<br>Cluster {cluster_id}" for c in cluster_coords],
                name=f"Cluster {cluster_id}",
            )
        )

    fig.update_layout(
        title=dict(text=title, x=0.5),
        xaxis_title="UMAP 1",
        yaxis_title="UMAP 2",
        legend_title="Cluster",
        width=800,
        height=600,
        template="plotly_white",
    )

    return fig


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UMAP 2D visualization")
    parser.add_argument("--cluster-k", type=int, default=4, help="K for cluster coloring")
    args = parser.parse_args()

    cache_dir = Path(__file__).resolve().parents[5] / "apps" / "argus" / "data"

    # Load features
    df = load_xray_data()
    tickers = list(df.index)
    print(f"Loaded {len(tickers)} ETFs × {len(df.columns)} features")

    # Load clustering results
    with open(cache_dir / "cluster_results.json") as f:
        cluster_data = json.load(f)
    k_results = cluster_data["k_results"]

    if str(args.cluster_k) not in k_results:
        print(f"Available K values: {sorted(int(k) for k in k_results)}")
        sys.exit(1)

    labels = k_results[str(args.cluster_k)]["labels"]

    # Compute UMAP
    print("Computing UMAP (euclidean, n_neighbors=5, min_dist=0.3)...")
    coords = compute_umap(df)

    # Build Plotly figure
    fig = make_plotly_scatter(
        coords,
        tickers,
        labels,
        args.cluster_k,
        title=f"Argus ETF Universe — UMAP 2D (colored by K={args.cluster_k} clusters)",
    )

    out_path = cache_dir / "xray_map.html"
    fig.write_html(str(out_path))
    print(f"\nSaved interactive UMAP plot: {out_path}")
    print(f"Open in browser: file://{out_path}")

    # Also save coords CSV for dashboard
    with open(cache_dir / "umap_coords.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "umap_x", "umap_y", "cluster"])
        for i, t in enumerate(tickers):
            writer.writerow([t, float(coords[i, 0]), float(coords[i, 1]), labels[i]])
    print(f"Saved umap_coords.csv to {cache_dir}")
