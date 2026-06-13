"""
xray.py — 10-dimension ETF feature decomposition.

Feature vector per ETF:
 1. country_exposure  (float 0-1, US vs international)
 2. sector_weight     (float 0-1, tech/energy/finance/etc.)
 3. expense_ratio    (float, standardized)
 4. volatility_252d   (float, annualized std dev of daily returns)
 5. momentum_126d     (float, cumulative return over 126 days)
 6. liquidity         (float, avg daily dollar volume / AUM)
 7. yield            (float, trailing dividend yield)
 8. max_drawdown_252d (float, worst peak-to-trough)
 9. corr_to_spy      (float, correlation to SPY over 126d)
10. is_leveraged      (bool encoded as float, 1 if 2x/3x ETF else 0)

All features are floats (no strings) so clustering works directly.
StandardScaler is applied to all features before output.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "argus-shared" / "src"))


# ── Sleeve-based expense ratio fallback ────────────────────────────────────────

# From midas-strategy/sleeves/__init__.py — primary source when yfinance returns 0
SLEEVE_EXPENSE_RATIOS: dict[str, float] = {
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


# ── Leveraged ETF list ────────────────────────────────────────────────────────

# Equity asset class: 1 = equity ETF, 0 = non-equity (bond/metal/commodity)
ASSET_CLASS_EQUITY: dict[str, float] = {
    # Fixed income
    "AGG": 0.0,
    "BND": 0.0,
    "LQD": 0.0,
    "TLT": 0.0,
    # Precious metals
    "GLD": 0.0,
    "SLV": 0.0,
}


# ── Country exposure ───────────────────────────────────────────────────────────

# Approximate US/international exposure per ETF (0 = fully international, 1 = fully US)
COUNTRY_EXPOSURE: dict[str, float] = {
    # US equity
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
    # Developed intl
    "VEA": 0.0,
    "EFA": 0.0,
    # Emerging markets
    "VWO": 0.0,
    "EEM": 0.0,
    # Fixed income
    "BND": 1.0,
    "AGG": 1.0,
    "TLT": 1.0,
    "LQD": 1.0,
    # Commodities
    "GLD": 1.0,
    "SLV": 1.0,
}


# ── Sector exposure ────────────────────────────────────────────────────────────

# Primary sector weight per ETF (0-1 scale, single dominant sector)
SECTOR_EXPOSURE: dict[str, float] = {
    "VTI": 0.3,
    "VOO": 0.3,
    "SPY": 0.3,  # Broad US
    "QQQ": 0.5,
    "XLK": 0.9,  # Tech
    "IWM": 0.4,  # Small cap
    "VIG": 0.4,
    "SCHD": 0.4,  # Dividend
    "VEA": 0.0,
    "VWO": 0.0,
    "EEM": 0.0,
    "EFA": 0.0,  # Intl
    "XLF": 0.8,  # Financials
    "XLE": 0.9,  # Energy
    "XLV": 0.9,  # Healthcare
    "XLI": 0.9,  # Industrials
    "BND": 0.0,
    "AGG": 0.0,
    "TLT": 0.0,
    "LQD": 0.0,  # Bonds
    "GLD": 0.0,
    "SLV": 0.0,  # Precious metals
    "ESGU": 0.3,  # ESG (US-heavy)
}


# ── Feature computation ────────────────────────────────────────────────────────


def compute_features(
    prices: dict[str, list[float]],
    stats: dict[str, dict[str, float]],
    spy_prices: list[float],
) -> pd.DataFrame:
    """
    Compute 10-dim feature vector per ETF.

    Parameters
    ----------
    prices : dict[ticker → list of daily close prices (oldest first)]
    stats : dict[ticker → dict with expense_ratio, dividend_yield, aum, avg_volume]
    spy_prices : list of SPY daily close prices for correlation

    Returns
    -------
    DataFrame with ticker as index, 10 feature columns, standardized (StandardScaler)
    """
    tickers = list(prices.keys())

    feat_names = [
        "country_exposure",
        "sector_exposure",
        "expense_ratio",
        "volatility_252d",
        "momentum_126d",
        "liquidity",
        "yield",
        "max_drawdown_252d",
        "corr_to_spy",
        "asset_class_equity",
    ]

    raw: dict[str, list[float]] = {f: [] for f in feat_names}

    spy_rets = (
        np.diff(spy_prices) / np.array(spy_prices[:-1]) if len(spy_prices) > 1 else np.array([])
    )

    for ticker in tickers:
        p = np.array(prices[ticker])
        rets = np.diff(p) / p[:-1] if len(p) > 1 else np.array([])

        # 1. country_exposure
        raw["country_exposure"].append(COUNTRY_EXPOSURE.get(ticker, 0.5))

        # 2. sector_exposure
        raw["sector_exposure"].append(SECTOR_EXPOSURE.get(ticker, 0.0))

        # 3. expense_ratio — use yfinance value, fall back to sleeve definition
        s = stats.get(ticker, {})
        er = float(s.get("expense_ratio", 0.0))
        if er == 0.0:
            er = SLEEVE_EXPENSE_RATIOS.get(ticker, 0.001)
        raw["expense_ratio"].append(er)

        # 4. volatility_252d (annualized)
        vol = float(np.std(rets) * np.sqrt(252)) if len(rets) >= 20 else 0.0
        raw["volatility_252d"].append(vol)

        # 5. momentum_126d (cumulative return over last 126 days of returns)
        if len(rets) >= 126:
            mom = float(np.prod(1 + rets[-126:]) - 1)
        elif len(rets) >= 20:
            mom = float(np.prod(1 + rets) - 1)
        else:
            mom = 0.0
        raw["momentum_126d"].append(mom)

        # 6. liquidity (avg daily dollar volume / AUM in billions)
        aum = float(s.get("aum", 1.0))
        avg_vol = float(s.get("avg_volume", 0))
        last_price = float(p[-1]) if len(p) > 0 else 0.0
        dollar_vol = avg_vol * last_price
        # liquidity = dollar volume / AUM (higher = more liquid)
        liq = (dollar_vol / (aum * 1e9)) if aum > 0 and dollar_vol > 0 else 0.0
        raw["liquidity"].append(liq)

        # 7. yield
        raw["yield"].append(float(s.get("dividend_yield", 0.0)))

        # 8. max_drawdown_252d
        if len(p) >= 20:
            peak = np.maximum.accumulate(p)
            drawdown = (p - peak) / peak
            mdd = float(np.min(drawdown))
        else:
            mdd = 0.0
        raw["max_drawdown_252d"].append(mdd)

        # 9. corr_to_spy (126d returns)
        if len(rets) >= 126 and len(spy_rets) >= 126:
            etf_rets = rets[-126:]
            spy_rets_126 = spy_rets[-126:]
            if np.std(etf_rets) > 0 and np.std(spy_rets_126) > 0:
                corr = float(np.corrcoef(etf_rets, spy_rets_126)[0, 1])
            else:
                corr = 0.0
        else:
            corr = 0.0
        raw["corr_to_spy"].append(corr if np.isfinite(corr) else 0.0)

        # 10. asset_class_equity (1 = equity, 0 = bond/metal/commodity)
        raw["asset_class_equity"].append(ASSET_CLASS_EQUITY.get(ticker, 1.0))

    df_raw = pd.DataFrame(raw, index=tickers)

    # Replace NaN/inf with 0
    df_raw = df_raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # StandardScaler
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    df_scaled = pd.DataFrame(
        scaler.fit_transform(df_raw),
        index=tickers,
        columns=feat_names,
    )

    return df_scaled


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import csv
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Compute 10-dim ETF feature vectors")
    parser.add_argument(
        "--cache-dir", default=None, help="Path to apps/argus/data/ (default: auto)"
    )
    args = parser.parse_args()

    # Auto-detect cache dir
    if args.cache_dir:
        cache_dir = Path(args.cache_dir)
    else:
        # Navigate: packages/argus/src/argus/core/ -> midas/ -> apps/argus/data/
        # 4 parents = packages/argus/src/argus/core/ -> argus -> src -> argus -> packages -> midas/
        midas_root = Path(__file__).resolve().parents[5]
        cache_dir = midas_root / "apps" / "argus" / "data"

    price_cache = cache_dir / "etf_prices.csv"
    stats_cache = cache_dir / "etf_stats.csv"

    print(f"Reading price data from: {price_cache}")
    print(f"Reading stats data from: {stats_cache}")

    # Load price cache
    prices: dict[str, list[float]] = {}
    if price_cache.exists():
        with open(price_cache) as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.pop("ticker")
                prices[ticker] = [float(v) for v in row.values() if v]
    else:
        print("ERROR: price cache not found. Run data_fetch.py first.")
        sys.exit(1)

    # Load stats cache
    stats: dict[str, dict[str, float]] = {}
    if stats_cache.exists():
        with open(stats_cache) as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row["ticker"]
                stats[ticker] = {
                    "expense_ratio": float(row.get("expense_ratio", 0)),
                    "dividend_yield": float(row.get("dividend_yield", 0)),
                    "aum": float(row.get("aum", 0)),
                    "avg_volume": int(row.get("avg_volume", 0)),
                }
    else:
        print("WARNING: stats cache not found. Using defaults.")

    # SPY prices for correlation
    spy_prices = prices.get("SPY", prices.get("VTI", []))
    if not spy_prices:
        print("WARNING: No SPY/VTI prices found, using first available for corr_to_spy")
        spy_prices = list(prices.values())[0] if prices else []

    df = compute_features(prices, stats, spy_prices)

    print(f"\n{'='*80}")
    print("X-RAY FEATURE VECTORS (StandardScaler applied)")
    print(f"{'='*80}")
    print(f"\nShape: {df.shape[0]} ETFs × {df.shape[1]} features\n")
    print(df.round(4).to_string())
    print(f"\nSaved to: {cache_dir / 'etf_xray_features.csv'}")
    df.round(6).to_csv(cache_dir / "etf_xray_features.csv")
