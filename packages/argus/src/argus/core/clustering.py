"""
clustering.py — K-means K=3..8 with silhouette evaluation.

9 features (after Dimension A):
  country_exposure, sector_exposure, expense_ratio, volatility_252d,
  momentum_126d, liquidity, yield, corr_to_spy, asset_class_equity

Dimension A: Uses Euclidean distance on z-scored features (not cosine).
DO NOT auto-select K — human decides.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "argus-shared" / "src"))

LEVERAGED_TICKERS = {
    "TQQQ",
    "SQQQ",
    "SOXL",
    "SOXS",
    "SPXL",
    "SPXS",
    "TNA",
    "TZA",
    "UWTI",
    "DWTI",
    "ERX",
    "ERY",
    "NUGT",
    "DUST",
    "USO",
    "UCO",
    "BOIL",
    "KOLD",
}

# From sleeves taxonomy
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

ASSET_CLASS_EQUITY = {
    "VTI": 1,
    "VOO": 1,
    "SPY": 1,
    "QQQ": 1,
    "IWM": 1,
    "VIG": 1,
    "SCHD": 1,
    "ESGU": 1,
    "XLK": 1,
    "XLF": 1,
    "XLE": 1,
    "XLV": 1,
    "XLI": 1,
    "VEA": 1,
    "VWO": 1,
    "EEM": 1,
    "EFA": 1,
    "BND": 0,
    "AGG": 0,
    "TLT": 0,
    "LQD": 0,
    "GLD": 0,
    "SLV": 0,
}


def load_xray_data() -> pd.DataFrame:
    """Load raw features (9 dims) from CSV caches and universe metadata."""
    cache_dir = Path(__file__).resolve().parents[5] / "apps" / "argus" / "data"
    prices = {}
    with open(cache_dir / "etf_prices.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.pop("ticker")
            prices[ticker] = [float(v) for v in row.values() if v]

    stats = {}
    with open(cache_dir / "etf_stats.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["ticker"]
            stats[ticker] = {
                "expense_ratio": float(row.get("expense_ratio", 0)),
                "dividend_yield": float(row.get("dividend_yield", 0)),
                "aum": float(row.get("aum", 0)),
                "avg_volume": int(row.get("avg_volume", 0)),
            }

    # Load asset_class_equity from universe metadata
    asset_class_equity = {}
    with open(cache_dir / "etf_universe.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            asset_class_equity[row["ticker"]] = int(row.get("asset_class_equity", 0))

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
        "asset_class_equity",
    ]
    raw = {f: [] for f in feat_names}

    spy_prices = prices.get("SPY", [])
    spy_rets = (
        np.diff(spy_prices) / np.array(spy_prices[:-1]) if len(spy_prices) > 1 else np.array([])
    )

    for ticker in tickers:
        p = np.array(prices[ticker])
        rets = np.diff(p) / p[:-1] if len(p) > 1 else np.array([])

        raw["country_exposure"].append(COUNTRY_EXPOSURE.get(ticker, 0.5))
        raw["sector_exposure"].append(SECTOR_EXPOSURE.get(ticker, 0.0))

        er = stats.get(ticker, {}).get("expense_ratio", 0.0)
        if er == 0.0:
            er = SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001)
        raw["expense_ratio"].append(er)

        vol = float(np.std(rets) * np.sqrt(252)) if len(rets) >= 20 else 0.0
        raw["volatility_252d"].append(vol)

        if len(rets) >= 126:
            mom = float(np.prod(1 + rets[-126:]) - 1)
        elif len(rets) >= 20:
            mom = float(np.prod(1 + rets) - 1)
        else:
            mom = 0.0
        raw["momentum_126d"].append(mom)

        aum = stats.get(ticker, {}).get("aum", 1.0)
        avg_vol = stats.get(ticker, {}).get("avg_volume", 0)
        last_price = float(p[-1]) if len(p) > 0 else 0.0
        dollar_vol = avg_vol * last_price
        liq = (dollar_vol / (aum * 1e9)) if aum > 0 and dollar_vol > 0 else 0.0
        raw["liquidity"].append(liq)

        raw["yield"].append(stats.get(ticker, {}).get("dividend_yield", 0.0))

        if len(rets) >= 126 and len(spy_rets) >= 126:
            er126 = rets[-126:]
            sr = spy_rets[-126:]
            if np.std(er126) > 0 and np.std(sr) > 0:
                corr = float(np.corrcoef(er126, sr)[0, 1])
            else:
                corr = 0.0
        else:
            corr = 0.0
        raw["corr_to_spy"].append(corr if np.isfinite(corr) else 0.0)
        raw["asset_class_equity"].append(asset_class_equity.get(ticker, 0))

    df_raw = pd.DataFrame(raw, index=tickers).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return df_raw


def run_clustering(df_raw: pd.DataFrame, k_range: range):
    """Run K-means for K in k_range, return silhouette scores and cluster labels."""
    scaler = StandardScaler()
    X = scaler.fit_transform(df_raw)

    results = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=20, max_iter=500)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels)
        inertia = km.inertia_
        results[k] = {
            "labels": labels,
            "silhouette": sil,
            "inertia": inertia,
            "scaler": scaler,
            "X": X,
            "kmeans": km,
        }
    return results


def print_elbow(silhouette_scores: dict, inertia: dict):
    """Print silhouette scores and inertia table."""
    print(f"\n{'='*70}")
    print(f"{'K':>4}  {'Silhouette':>12}  {'Inertia':>12}")
    print("-" * 70)
    for k in sorted(silhouette_scores):
        print(f"{k:>4}  {silhouette_scores[k]:>12.4f}  {inertia[k]:>12.1f}")


def print_top2_clusters(results: dict, tickers: list, silhouette_scores: dict):
    """Print cluster assignments for top 2 silhouette K values."""
    sorted_k = sorted(silhouette_scores, key=lambda k: silhouette_scores[k], reverse=True)[:2]

    print(f"\n{'='*70}")
    print("TOP 2 SILHOUETTE K — CLUSTER ASSIGNMENTS")
    print("=" * 70)

    for k in sorted_k:
        r = results[k]
        labels = r["labels"]
        print(f"\n--- K = {k}  (silhouette = {silhouette_scores[k]:.4f}) ---")
        for cluster_id in sorted(set(labels)):
            members = [tickers[i] for i in range(len(tickers)) if labels[i] == cluster_id]
            print(f"  Cluster {cluster_id}: {', '.join(members)}")


def print_cluster_profiles(df_raw: pd.DataFrame, results: dict, tickers: list):
    """Print mean feature values per cluster for top-2 K."""
    sorted_k = sorted(results.keys(), key=lambda k: results[k]["silhouette"], reverse=True)[:2]

    for k in sorted_k:
        labels = results[k]["labels"]
        df_plot = df_raw.copy()
        df_plot["cluster"] = labels
        print(f"\n--- K={k} cluster profiles (mean feature values) ---")
        profile = df_plot.groupby("cluster").mean()
        print(profile.round(4).to_string())


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="K-means clustering K=3..8")
    parser.add_argument("--cache-dir", default=None)
    args = parser.parse_args()

    cache_dir = (
        Path(args.cache_dir)
        if args.cache_dir
        else Path(__file__).resolve().parents[5] / "apps" / "argus" / "data"
    )

    print(f"Loading ETF data from: {cache_dir}")
    df_raw = load_xray_data()
    tickers = list(df_raw.index)

    print(f"\n{'='*70}")
    print("CLUSTERING: 9 Features × 23 ETFs")
    print(f"{'='*70}")
    print(f"Features: {list(df_raw.columns)}")
    print(f"ETFs: {tickers}")

    results = run_clustering(df_raw, range(3, 9))
    silhouette_scores = {k: results[k]["silhouette"] for k in results}
    inertia = {k: results[k]["inertia"] for k in results}

    print_elbow(silhouette_scores, inertia)
    print_top2_clusters(results, tickers, silhouette_scores)
    print_cluster_profiles(df_raw, results, tickers)

    # Save results for VIZ
    out = {}
    for k in range(3, 9):
        r = results[k]
        out[k] = {
            "silhouette": float(r["silhouette"]),
            "inertia": float(r["inertia"]),  # noqa: E501
            "labels": [int(label) for label in r["labels"]],
        }

    import json

    with open(cache_dir / "cluster_results.json", "w") as f:
        json.dump({"tickers": tickers, "k_results": out}, f)

    print(f"\nSaved cluster_results.json to {cache_dir}")
