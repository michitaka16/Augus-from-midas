#!/usr/bin/env python3
"""
Expand ETF universe from 23 to 60.
Fetches data via yfinance, computes features, re-runs K-means.
"""

import csv
import json
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import yfinance as yf  # noqa: E402
from sklearn.cluster import KMeans  # noqa: E402
from sklearn.metrics import silhouette_score  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

DATA_DIR = "apps/argus/data"

# 37 new ETFs to add
NEW_TICKERS = [
    # US Sectors
    "XLP",
    "XLY",
    "XLU",
    "XLRE",
    "SOXX",
    "KRE",
    "ITA",
    # International
    "FXI",
    "MCHI",
    "INDA",
    "EWJ",
    "EWG",
    "EWZ",
    # Bonds
    "SHY",
    "IEF",
    "MUB",
    "EMB",
    "HYG",
    "BNDX",
    "VCIT",
    # Dividend/Value
    "VYM",
    "HDV",
    "DVY",
    "NOBL",
    "VTV",
    "IWD",
    # Growth
    "MGK",
    "VUG",
    "IWF",
    "IVW",
    # Thematic
    "ARKK",
    "ICLN",
    "JETS",
    "CIBR",
    # ESG
    "ESGV",
    "SUSA",
    "ESGD",
    # REIT
    "VNQ",
]

# Sleeve assignments for new ETFs
SLEEVE_MAP = {
    "XLP": "consumer_staples",
    "XLY": "consumer_discretionary",
    "XLU": "utilities",
    "XLRE": "real_estate",
    "SOXX": "technology",
    "KRE": "financials",
    "ITA": "industrials",
    "FXI": "em_equity",
    "MCHI": "em_equity",
    "INDA": "em_equity",
    "EWJ": "intl_equity",
    "EWG": "intl_equity",
    "EWZ": "em_equity",
    "SHY": "govt_bonds_short",
    "IEF": "govt_bonds_intermediate",
    "MUB": "muni_bonds",
    "EMB": "em_bonds",
    "HYG": "hy_bonds",
    "BNDX": "intl_bonds",
    "VCIT": "ig_corp_bonds",
    "VYM": "dividend_etfs",
    "HDV": "dividend_etfs",
    "DVY": "dividend_etfs",
    "NOBL": "dividend_etfs",
    "VTV": "dividend_etfs",
    "IWD": "dividend_etfs",
    "MGK": "growth_etfs",
    "VUG": "growth_etfs",
    "IWF": "growth_etfs",
    "IVW": "growth_etfs",
    "ARKK": "thematic",
    "ICLN": "thematic",
    "JETS": "thematic",
    "CIBR": "thematic",
    "ESGV": "esg_etfs",
    "SUSA": "esg_etfs",
    "ESGD": "esg_etfs",
    "VNQ": "reit",
}

ASSET_CLASS_MAP = {
    "XLP": "equity",
    "XLY": "equity",
    "XLU": "equity",
    "XLRE": "equity",
    "SOXX": "equity",
    "KRE": "equity",
    "ITA": "equity",
    "FXI": "equity",
    "MCHI": "equity",
    "INDA": "equity",
    "EWJ": "equity",
    "EWG": "equity",
    "EWZ": "equity",
    "SHY": "bond",
    "IEF": "bond",
    "MUB": "bond",
    "EMB": "bond",
    "HYG": "bond",
    "BNDX": "bond",
    "VCIT": "bond",
    "VYM": "equity",
    "HDV": "equity",
    "DVY": "equity",
    "NOBL": "equity",
    "VTV": "equity",
    "IWD": "equity",
    "MGK": "equity",
    "VUG": "equity",
    "IWF": "equity",
    "IVW": "equity",
    "ARKK": "equity",
    "ICLN": "equity",
    "JETS": "equity",
    "CIBR": "equity",
    "ESGV": "equity",
    "SUSA": "equity",
    "ESGD": "equity",
    "VNQ": "real_estate",
}

AC_EQUITY_MAP = {
    "XLP": 1,
    "XLY": 1,
    "XLU": 1,
    "XLRE": 1,
    "SOXX": 1,
    "KRE": 1,
    "ITA": 1,
    "FXI": 1,
    "MCHI": 1,
    "INDA": 1,
    "EWJ": 1,
    "EWG": 1,
    "EWZ": 1,
    "SHY": 0,
    "IEF": 0,
    "MUB": 0,
    "EMB": 0,
    "HYG": 0,
    "BNDX": 0,
    "VCIT": 0,
    "VYM": 1,
    "HDV": 1,
    "DVY": 1,
    "NOBL": 1,
    "VTV": 1,
    "IWD": 1,
    "MGK": 1,
    "VUG": 1,
    "IWF": 1,
    "IVW": 1,
    "ARKK": 1,
    "ICLN": 1,
    "JETS": 1,
    "CIBR": 1,
    "ESGV": 1,
    "SUSA": 1,
    "ESGD": 1,
    "VNQ": 0,
}

NAME_MAP = {
    "XLP": "Consumer Staples Select Sector SPDR",
    "XLY": "Consumer Discretionary Select Sector SPDR",
    "XLU": "Utilities Select Sector SPDR",
    "XLRE": "Real Estate Select Sector SPDR",
    "SOXX": "VanEck Semiconductor ETF",
    "KRE": "Regional Bank Select Sector SPDR",
    "ITA": "iShares U.S. Aerospace & Defense",
    "FXI": "iShares China Large-Cap ETF",
    "MCHI": "iShares MSCI China ETF",
    "INDA": "iShares MSCI India ETF",
    "EWJ": "iShares MSCI Japan ETF",
    "EWG": "iShares MSCI Germany ETF",
    "EWZ": "iShares MSCI Brazil ETF",
    "SHY": "iShares 1-3 Year Treasury Bond",
    "IEF": "iShares 7-10 Year Treasury Bond",
    "MUB": "iShares National Muni Bond",
    "EMB": "iShares J.P. Morgan USD Emerging Markets Bond",
    "HYG": "iShares iBoxx High Yield Corporate Bond",
    "BNDX": "Vanguard Total International Bond",
    "VCIT": "Vanguard Intermediate-Term Corporate Bond",
    "VYM": "Vanguard High Dividend Yield ETF",
    "HDV": "iShares Core High Dividend",
    "DVY": "iShares Select Dividend",
    "NOBL": "ProShares S&P 500 Dividend Aristocrats",
    "VTV": "Vanguard Value ETF",
    "IWD": "iShares Russell 1000 Value",
    "MGK": "Vanguard Mega Cap Growth ETF",
    "VUG": "Vanguard Growth ETF",
    "IWF": "iShares Russell 1000 Growth",
    "IVW": "iShares S&P 500 Growth",
    "ARKK": "ARK Innovation ETF",
    "ICLN": "iShares Global Clean Energy",
    "JETS": "U.S. Global Jets ETF",
    "CIBR": "ETFMG Prime Cyber Security",
    "ESGV": "iShares ESG Aware MSCI USA Small-Cap",
    "SUSA": "iShares MSCI USA ESG Select",
    "ESGD": "iShares MSCI EAFE ESG Focused",
    "VNQ": "Vanguard Real Estate ETF",
}

# Hardcoded sleeve expense ratios for fallback
SLEEVE_EXPENSE_RATIOS = {
    "XLP": 0.10,
    "XLY": 0.10,
    "XLU": 0.10,
    "XLRE": 0.10,
    "SOXX": 0.35,
    "KRE": 0.35,
    "ITA": 0.39,
    "FXI": 0.74,
    "MCHI": 0.59,
    "INDA": 0.59,
    "EWJ": 0.50,
    "EWG": 0.50,
    "EWZ": 0.57,
    "SHY": 0.15,
    "IEF": 0.15,
    "MUB": 0.07,
    "EMB": 0.39,
    "HYG": 0.48,
    "BNDX": 0.08,
    "VCIT": 0.04,
    "VYM": 0.06,
    "HDV": 0.08,
    "DVY": 0.38,
    "NOBL": 0.35,
    "VTV": 0.04,
    "IWD": 0.19,
    "MGK": 0.11,
    "VUG": 0.04,
    "IWF": 0.19,
    "IVW": 0.18,
    "ARKK": 0.75,
    "ICLN": 0.46,
    "JETS": 0.60,
    "CIBR": 0.60,
    "ESGV": 0.17,
    "SUSA": 0.25,
    "ESGD": 0.20,
    "VNQ": 0.12,
}

print("Fetching price data for new ETFs...")
# Fetch 252 days of price data (252 closes = 251 daily returns for diff)
end = "2024-12-31"
start = "2023-12-31"  # Go back extra to ensure 252 closes
new_prices = {}
for ticker in NEW_TICKERS:
    try:
        data = yf.download(ticker, start=start, end=end, progress=False)
        if len(data) >= 60:
            closes = data["Close"].dropna().values.ravel()  # flatten 2D -> 1D
            new_prices[ticker] = closes[-252:]
            print(f"  {ticker}: {len(new_prices[ticker])} prices")
        else:
            print(f"  {ticker}: SKIP (only {len(data)} rows)")
    except Exception as e:
        print(f"  {ticker}: SKIP ({e})")

print(f"\nFetched prices for {len(new_prices)} ETFs")

# Fetch stats
print("\nFetching ETF stats...")
new_stats = {}
for ticker in NEW_TICKERS:
    if ticker not in new_prices:
        continue
    try:
        t = yf.Ticker(ticker)
        info = t.info
        er = info.get("expenseRatio") or SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001)
        dy = info.get("dividendYield") or 0.0
        if dy and dy > 1:
            dy = dy / 100  # Sometimes in percent
        aum = info.get("totalAssets") or info.get("aum", 1e6)
        vol = info.get("averageVolume") or 0
        new_stats[ticker] = {
            "expense_ratio": float(er),
            "dividend_yield": float(dy),
            "aum": float(aum),
            "avg_volume": int(vol),
        }
        print(f"  {ticker}: ER={er:.4f}, yield={dy:.3f}, AUM={aum/1e9:.2f}B")
    except Exception as e:
        new_stats[ticker] = {
            "expense_ratio": SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001),
            "dividend_yield": 0.0,
            "aum": 1e6,
            "avg_volume": 100000,
        }
        print(f"  {ticker}: using fallback stats ({e})")

# Load existing data
print("\nLoading existing universe...")
with open(f"{DATA_DIR}/etf_universe.csv") as f:
    reader = csv.DictReader(f)
    universe_rows = list(reader)

with open(f"{DATA_DIR}/etf_prices.csv") as f:
    reader = csv.DictReader(f)
    prices_data = {}
    for r in reader:
        ticker = r.pop("ticker")
        prices_data[ticker] = np.array([float(v) for v in r.values() if v], dtype=np.float64)

with open(f"{DATA_DIR}/etf_stats.csv") as f:
    reader = csv.DictReader(f)
    stats_data = {}
    for r in reader:
        ticker = r.pop("ticker")
        stats_data[ticker] = {
            k: (float(v) if k != "avg_volume" else int(float(v))) for k, v in r.items()
        }

print(f"  Existing: {len(universe_rows)} ETFs, {len(prices_data)} price series")

# Add new ETFs to universe
for ticker in new_prices:
    if ticker in [r["ticker"] for r in universe_rows]:
        print(f"  {ticker} already exists, skipping")
        continue
    row = {
        "ticker": ticker,
        "name": NAME_MAP.get(ticker, ticker),
        "sleeve": SLEEVE_MAP.get(ticker, "other"),
        "asset_class": ASSET_CLASS_MAP.get(ticker, "equity"),
        "asset_class_equity": str(AC_EQUITY_MAP.get(ticker, 1)),
    }
    universe_rows.append(row)
    prices_data[ticker] = list(new_prices[ticker])
    stats_data[ticker] = new_stats.get(
        ticker,
        {
            "expense_ratio": SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001),
            "dividend_yield": 0.0,
            "aum": 1e6,
            "avg_volume": 100000,
        },
    )

# Compute features
print("\nComputing 9-feature vectors...")
SECTOR_EXPOSURE = {t: 0.3 for t in new_prices if t.startswith("X")}
COUNTRY_EXPOSURE = {
    "FXI": 0.0,
    "MCHI": 0.0,
    "INDA": 0.1,
    "EWJ": 0.0,
    "EWG": 0.0,
    "EWZ": 0.0,
}
SECTOR_EXPOSURE.update(
    {
        "XLP": 0.3,
        "XLY": 0.6,
        "XLU": 0.0,
        "XLRE": 0.0,
        "SOXX": 0.8,
        "KRE": 0.7,
        "ITA": 0.6,
        "ARKK": 0.5,
        "ICLN": 0.0,
        "JETS": 0.0,
        "CIBR": 0.8,
        "ESGV": 0.3,
        "SUSA": 0.3,
        "ESGD": 0.0,
        "VNQ": 0.0,
    }
)
COUNTRY_EXPOSURE.update({t: 0.5 for t in new_prices if t not in COUNTRY_EXPOSURE})

tickers = sorted(prices_data.keys())
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
raw_feats = {f: [] for f in feat_names}
spy_prices = prices_data.get("SPY", [])
spy_rets = np.diff(spy_prices) / np.array(spy_prices[:-1]) if len(spy_prices) > 1 else np.array([])

for ticker in tickers:
    p = np.array(prices_data[ticker])
    rets = np.diff(p) / p[:-1] if len(p) > 1 else np.array([])
    s = stats_data.get(ticker, {})
    raw_feats["country_exposure"].append(COUNTRY_EXPOSURE.get(ticker, 0.5))
    raw_feats["sector_exposure"].append(SECTOR_EXPOSURE.get(ticker, 0.0))
    er = float(s.get("expense_ratio", 0.0))
    if er == 0.0:
        er = SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001)
    raw_feats["expense_ratio"].append(er)
    raw_feats["volatility_252d"].append(
        float(np.std(rets) * np.sqrt(252)) if len(rets) >= 20 else 0.0
    )
    if len(rets) >= 126:
        raw_feats["momentum_126d"].append(float(np.prod(1 + rets[-126:]) - 1))
    elif len(rets) >= 20:
        raw_feats["momentum_126d"].append(float(np.prod(1 + rets) - 1))
    else:
        raw_feats["momentum_126d"].append(0.0)
    aum = float(s.get("aum", 1.0))
    avg_vol = int(s.get("avg_volume", 0))
    last_price = float(p[-1]) if len(p) > 0 else 0.0
    liq = (avg_vol * last_price / (aum * 1e9)) if aum > 0 and avg_vol > 0 else 0.0
    raw_feats["liquidity"].append(liq)
    raw_feats["yield"].append(float(s.get("dividend_yield", 0.0)))
    if len(rets) >= 126 and len(spy_rets) >= 126:
        er126, sr = rets[-126:], spy_rets[-126:]
        corr = float(np.corrcoef(er126, sr)[0, 1]) if np.std(er126) > 0 and np.std(sr) > 0 else 0.0
    else:
        corr = 0.0
    raw_feats["corr_to_spy"].append(corr if np.isfinite(corr) else 0.0)

raw_df = np.array([raw_feats[f] for f in feat_names]).T
print(f"  Raw features shape: {raw_df.shape}")

# Standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(raw_df)

# Write etf_xray_features.csv
feat9 = [
    "country_exposure",
    "sector_exposure",
    "expense_ratio",
    "volatility_252d",
    "momentum_126d",
    "liquidity",
    "yield",
    "corr_to_spy",
]
with open(f"{DATA_DIR}/etf_xray_features.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([""] + feat9)
    for i, ticker in enumerate(tickers):
        w.writerow([ticker] + [f"{X_scaled[i, j]:.6f}" for j in range(len(feat9))])
print("  Wrote etf_xray_features.csv")

# Write etf_universe.csv
with open(f"{DATA_DIR}/etf_universe.csv", "w", newline="") as f:
    w = csv.DictWriter(
        f, fieldnames=["ticker", "name", "sleeve", "asset_class", "asset_class_equity"]
    )
    w.writeheader()
    w.writerows(universe_rows)
print(f"  Wrote etf_universe.csv ({len(universe_rows)} rows)")

# Write etf_prices.csv (replace with fresh 252-day prices for all)
all_tickers = sorted(prices_data.keys())
max_len = max(len(v) for v in prices_data.values())
headers = ["ticker"] + [f"d{i}" for i in range(max_len)]
with open(f"{DATA_DIR}/etf_prices.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(headers)
    for ticker in all_tickers:
        prices = prices_data[ticker]
        padded = list(prices) + [""] * (max_len - len(prices))
        w.writerow([ticker] + padded)
print(f"  Wrote etf_prices.csv ({len(all_tickers)} tickers, {max_len} days)")

# Write etf_stats.csv
stat_fields = ["ticker", "expense_ratio", "dividend_yield", "aum", "avg_volume"]
with open(f"{DATA_DIR}/etf_stats.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=stat_fields)
    w.writeheader()
    for ticker in all_tickers:
        s = stats_data.get(ticker, {})
        w.writerow(
            {
                "ticker": ticker,
                "expense_ratio": s.get("expense_ratio", 0.001),
                "dividend_yield": s.get("dividend_yield", 0.0),
                "aum": s.get("aum", 1e6),
                "avg_volume": s.get("avg_volume", 0),
            }
        )
print(f"  Wrote etf_stats.csv ({len(all_tickers)} rows)")

# Run K-means K=3..8
print("\nRunning K-means clustering...")
silhouettes = {}
kmeans_results = {}
for k in range(3, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    sil = silhouette_score(X_scaled, labels)
    silhouettes[k] = sil
    kmeans_results[k] = {"labels": labels.tolist(), "centers": km.cluster_centers_.tolist()}
    print(f"  K={k}: silhouette={sil:.4f}")

best_k = max(silhouettes, key=silhouettes.get)
print(f"\nBest K by silhouette: {best_k} ({silhouettes[best_k]:.4f})")

# Use K=5 (per Decision 6)
K = 5
labels = kmeans_results[K]["labels"]

# Check cluster balance
from collections import Counter  # noqa: E402

cluster_counts = Counter(labels)
print(f"\nK={K} cluster composition:")
for c in sorted(cluster_counts):
    pct = cluster_counts[c] / len(labels) * 100
    members = [tickers[i] for i, label in enumerate(labels) if label == c]
    print(f"  Cluster {c}: {cluster_counts[c]} ETFs ({pct:.1f}%)")
    print(f"    {members}")

# Check balance: no cluster > 35%
max_pct = max(cluster_counts.values()) / len(labels) * 100
print(f"\nMax cluster size: {max_pct:.1f}% (limit: 35%)")
if max_pct > 35:
    print("  WARNING: cluster imbalance exceeds 35%")
else:
    print("  OK: cluster sizes balanced")

# Write cluster_results.json
with open(f"{DATA_DIR}/cluster_results.json") as f:
    existing = json.load(f)
existing["tickers"] = tickers
existing["k_results"] = kmeans_results
with open(f"{DATA_DIR}/cluster_results.json", "w") as f:
    json.dump(existing, f, indent=2)
print("\nWrote cluster_results.json")

print("\n=== FINAL STATUS ===")
print(f"Total ETFs in universe: {len(tickers)}")
print(f"Silhouette scores: {dict(sorted(silhouettes.items()))}")
