"""
recommender.py — Within-cluster ETF similarity recommender.

Implements BOTH cosine similarity AND Euclidean distance.
Dimension A: Human decides which metric to use based on empirical comparison.

For a given ETF:
  1. Find its cluster from clustering.py results
  2. Find all other ETFs in the same cluster
  3. Compute pairwise similarity using both metrics
  4. Return top-N recommendations sorted by descending similarity
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
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

    df = pd.DataFrame(raw, index=tickers).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return df


def get_cluster_for_etf(cluster_results: dict, ticker: str) -> int | None:
    """Get cluster ID for a given ticker (requires K to be specified)."""
    return cluster_results.get("cluster_map", {}).get(ticker)


def recommend(
    query_ticker: str,
    df: pd.DataFrame,
    cluster_labels: list[int],
    metric: str,
    top_n: int = 5,
) -> list[tuple[str, float]]:
    """
    Return top-N similar ETFs within the same cluster.

    Parameters
    ----------
    query_ticker : ETF to find similar matches for
    df : raw 8-dim feature DataFrame (index = tickers)
    cluster_labels : list of cluster assignments aligned with df.index
    metric : "cosine" or "euclidean"
    top_n : number of recommendations

    Returns
    -------
    list of (ticker, similarity_score) sorted descending
    """
    tickers = list(df.index)
    try:
        query_idx = tickers.index(query_ticker)
    except ValueError:
        raise ValueError(f"Ticker {query_ticker} not found in universe") from None

    query_cluster = cluster_labels[query_idx]

    # Standardize features
    scaler = StandardScaler()
    X = scaler.fit_transform(df.values)

    query_vec = X[query_idx].reshape(1, -1)

    # Find same-cluster peers
    same_cluster_idx = [
        i for i in range(len(tickers)) if i != query_idx and cluster_labels[i] == query_cluster
    ]

    if not same_cluster_idx:
        return []

    peer_X = X[same_cluster_idx]
    peer_tickers = [tickers[i] for i in same_cluster_idx]

    if metric == "cosine":
        sims = cosine_similarity(query_vec, peer_X)[0]
        # Convert to positive scores (cosine is already -1 to 1)
        # Higher = more similar
        results = sorted(zip(peer_tickers, sims, strict=True), key=lambda x: x[1], reverse=True)
    elif metric == "euclidean":
        dists = euclidean_distances(query_vec, peer_X)[0]
        # Convert distance to similarity: 1 / (1 + d)
        sims = [1.0 / (1.0 + d) for d in dists]
        results = sorted(zip(peer_tickers, sims, strict=True), key=lambda x: x[1], reverse=True)
    else:
        raise ValueError(f"Unknown metric: {metric}. Use 'cosine' or 'euclidean'.")

    return results[:top_n]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ETF similarity recommender")
    parser.add_argument("--ticker", default="VTI", help="Query ticker (default: VTI)")
    parser.add_argument("--top-n", type=int, default=3, help="Top-N recommendations")
    parser.add_argument(
        "--cluster-k", type=int, default=4, help="Which K to use for cluster assignments"
    )
    args = parser.parse_args()

    cache_dir = Path(__file__).resolve().parents[5] / "apps" / "argus" / "data"

    # Load clustering results
    with open(cache_dir / "cluster_results.json") as f:
        cluster_data = json.load(f)
    tickers = cluster_data["tickers"]
    k_results = cluster_data["k_results"]

    if str(args.cluster_k) not in k_results and args.cluster_k not in k_results:
        print(f"Available K values: {sorted(k_results.keys())}")
        sys.exit(1)

    labels = k_results[str(args.cluster_k)]["labels"]

    # Load features
    df = load_xray_data()

    print(f"\n{'='*70}")
    print(f"RECOMMENDER: {args.ticker}")
    print(f"Cluster assignments (K={args.cluster_k}):")
    for i, t in enumerate(tickers):
        print(f"  {t}: cluster {labels[i]}")

    print(f"\n{'='*70}")
    print(f"TOP-{args.top_n} RECOMMENDATIONS USING COSINE SIMILARITY")
    print("=" * 70)
    try:
        cosine_recs = recommend(args.ticker, df, labels, "cosine", args.top_n)
        for rank, (ticker, score) in enumerate(cosine_recs, 1):
            print(f"  {rank}. {ticker:<6}  cosine_sim = {score:.4f}")
    except ValueError as e:
        print(f"  ERROR: {e}")

    print(f"\n{'='*70}")
    print(f"TOP-{args.top_n} RECOMMENDATIONS USING EUCLIDEAN SIMILARITY")
    print("(similarity = 1 / (1 + euclidean_distance))")
    print("=" * 70)
    try:
        euclid_recs = recommend(args.ticker, df, labels, "euclidean", args.top_n)
        for rank, (ticker, score) in enumerate(euclid_recs, 1):
            print(f"  {rank}. {ticker:<6}  euclid_sim = {score:.4f}")
    except ValueError as e:
        print(f"  ERROR: {e}")
