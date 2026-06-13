"""
data_fetch.py — Fetch ETF holdings and price data via yfinance with CSV cache.

ETF universe: user-specified 24 ETFs (VTI, VOO, SPY, QQQ, IWM, VIG, SCHD,
VEA, VWO, EEM, EFA, XLK, XLF, XLE, XLV, XLI, BND, AGG, TLT, LQD, GLD,
SLV, ESGU)

Cache strategy:
- data/etf_prices.csv — 252-day price history per ETF
- data/etf_holdings.csv — top holdings per ETF
- data/etf_stats.csv — key stats (expense_ratio, dividend_yield, AUM)
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Add argus-shared to path for sleeve imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "argus-shared" / "src"))

# ── Configuration ──────────────────────────────────────────────────────────────

ETFS = [
    "VTI",
    "VOO",
    "SPY",
    "QQQ",
    "IWM",
    "VIG",
    "SCHD",
    "VEA",
    "VWO",
    "EEM",
    "EFA",
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLI",
    "BND",
    "AGG",
    "TLT",
    "LQD",
    "GLD",
    "SLV",
    "ESGU",
]

# yfinance-compatible names for holdings lookup
ETF_YFINANCE_NAMES: dict[str, str] = {
    "VTI": "Vanguard Total Stock Market ETF",
    "VOO": "Vanguard S&P 500 ETF",
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "IWM": "iShares Russell 2000 ETF",
    "VIG": "Vanguard Dividend Appreciation ETF",
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "VEA": "Vanguard FTSE Developed Markets ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
    "EEM": "iShares MSCI Emerging Markets ETF",
    "EFA": "iShares MSCI EAFE ETF",
    "XLK": "Technology Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "BND": "Vanguard Total Bond Market ETF",
    "AGG": "iShares Core U.S. Aggregate Bond ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "LQD": "iShares iBoxx Investment Grade Corporate Bond ETF",
    "GLD": "SPDR Gold Shares",
    "SLV": "iShares Silver Trust",
    "ESGU": "iShares ESG Aware MSCI USA ETF",
}

DATA_DIR = Path(__file__).resolve().parents[5] / "apps" / "argus" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PRICE_CACHE = DATA_DIR / "etf_prices.csv"
HOLDINGS_CACHE = DATA_DIR / "etf_holdings.csv"
STATS_CACHE = DATA_DIR / "etf_stats.csv"
UNIVERSE_CACHE = DATA_DIR / "etf_universe.csv"

TRADING_DAYS = 252


# ── Dataclasses ────────────────────────────────────────────────────────────────


@dataclass
class ETFPriceData:
    ticker: str
    prices_252d: list[float]  # daily close prices, oldest first
    dates: list[str]
    returns_126d: list[float]  # daily returns for momentum computation
    volume_252d: list[int]


@dataclass
class ETFStats:
    ticker: str
    expense_ratio: float  # as decimal, e.g. 0.0009 = 9 bps
    dividend_yield: float  # as decimal
    aum: float  # in billions USD
    avg_volume: int  # avg daily volume in shares


@dataclass
class ETFHoldings:
    ticker: str
    holdings: list[tuple[str, float]]  # list of (ticker, weight_pct)


@dataclass
class ETFData:
    """Combined data for one ETF."""

    ticker: str
    prices: ETFPriceData | None = None
    stats: ETFStats | None = None
    holdings: ETFHoldings | None = None


# ── yfinance fetcher ──────────────────────────────────────────────────────────


def _import_yfinance() -> Any:
    try:
        import yfinance

        return yfinance
    except ImportError:
        raise ImportError("yfinance is required. Install with: pip install yfinance") from None


def fetch_price_history(ticker: str, days: int = TRADING_DAYS) -> ETFPriceData | None:
    """Fetch 252-day price history from yfinance."""
    yf = _import_yfinance()
    end = date.today()
    start = end - timedelta(days=days * 2)  # fetch extra for buffer

    try:
        data = yf.download(
            ticker,
            start=str(start),
            end=str(end),
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        return None

    if data is None or data.empty:
        return None

    # Handle multi-level columns (auto_adjust=True may return DataFrame)
    close_col = data["Close"]
    if hasattr(close_col, "columns"):
        close_col = close_col.iloc[:, 0]  # first ticker column
    close_col = close_col.dropna()

    vol_col = data["Volume"]
    if hasattr(vol_col, "columns"):
        vol_col = vol_col.iloc[:, 0]
    vol_col = vol_col.dropna()

    closes = close_col.tail(days)
    volumes = vol_col.tail(days)

    if len(closes) < days // 2:
        return None

    price_list = closes.tolist()
    vol_list = volumes.tolist() if len(volumes) == len(closes) else [0] * len(closes)

    # Daily returns
    import numpy as np

    returns = np.diff(price_list) / price_list[:-1] if len(price_list) > 1 else []
    returns = [float(r) for r in returns]

    date_list = [str(d.date()) if hasattr(d, "date") else str(d) for d in closes.index]

    return ETFPriceData(
        ticker=ticker,
        prices_252d=[float(p) for p in price_list],
        dates=date_list,
        returns_126d=returns[-126:] if len(returns) >= 126 else returns,
        volume_252d=[int(v) for v in vol_list],
    )


def fetch_stats(ticker: str) -> ETFStats | None:
    """Fetch key stats (expense_ratio, yield, AUM) from yfinance."""
    yf = _import_yfinance()
    try:
        t = yf.Ticker(ticker)
        info = t.info
    except Exception:
        return None

    if not info or "navPrice" in info and len(info) < 3:
        return None

    def safe_float(key: str) -> float:
        val = info.get(key)
        if val is None:
            return 0.0
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    def safe_int(key: str) -> int:
        val = info.get(key)
        if val is None:
            return 0
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    expense = safe_float("expenseRatio")
    if expense == 0.0:
        expense = safe_float("annualReportExpenseRatio")
    if expense == 0.0:
        expense = safe_float("netExpenseRatio")
    yield_val = safe_float("dividendYield")
    if yield_val == 0.0:
        yield_val = safe_float("trailingDividendYield")
    aum = safe_float("totalAssets")
    aum_b = aum / 1e9 if aum > 0 else 0.0
    avg_vol = safe_int("averageVolume")

    return ETFStats(
        ticker=ticker,
        expense_ratio=expense,
        dividend_yield=yield_val,
        aum=aum_b,
        avg_volume=avg_vol,
    )


def fetch_holdings(ticker: str) -> ETFHoldings | None:
    """Fetch top 10 holdings from yfinance."""
    yf = _import_yfinance()
    try:
        t = yf.Ticker(ticker)
        # yfinance stores holdings as a DataFrame
        hd = t.get_info().get("top_holdings", {})
        if not hd:
            return None
        # holdings is a dict with 'symbol' and 'weightPercent' keys
        holding_list = hd if isinstance(hd, list) else hd.get("holdings", [])
        if not holding_list:
            return None
        holdings = []
        for h in holding_list[:10]:
            sym = h.get("symbol") or h.get("holdingSymbol", "")
            wt = h.get("weightPercent", h.get("weight", 0.0))
            if sym:
                holdings.append((str(sym), float(wt)))
        return ETFHoldings(ticker=ticker, holdings=holdings)
    except Exception:
        return None


# ── CSV Cache ─────────────────────────────────────────────────────────────────


def _read_prices_cache() -> dict[str, list[float]]:
    if not PRICE_CACHE.exists():
        return {}
    out = {}
    with open(PRICE_CACHE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.pop("ticker")
            out[ticker] = [float(v) for v in row.values() if v]
    return out


def _write_prices_cache(data: dict[str, ETFPriceData]) -> None:
    if not data:
        return
    tickers = list(data.keys())
    all_prices = [data[t].prices_252d for t in tickers]
    max_len = max(len(p) for p in all_prices)

    with open(PRICE_CACHE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"] + [f"d{i}" for i in range(max_len)])
        for ticker in tickers:
            prices = data[ticker].prices_252d
            writer.writerow([ticker] + prices + ["" for _ in range(max_len - len(prices))])


def _read_stats_cache() -> dict[str, ETFStats]:
    if not STATS_CACHE.exists():
        return {}
    out = {}
    with open(STATS_CACHE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["ticker"]] = ETFStats(
                ticker=row["ticker"],
                expense_ratio=float(row.get("expense_ratio", 0)),
                dividend_yield=float(row.get("dividend_yield", 0)),
                aum=float(row.get("aum", 0)),
                avg_volume=int(row.get("avg_volume", 0)),
            )
    return out


def _write_stats_cache(data: dict[str, ETFStats]) -> None:
    with open(STATS_CACHE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "expense_ratio", "dividend_yield", "aum", "avg_volume"])
        for stats in data.values():
            writer.writerow(
                [
                    stats.ticker,
                    stats.expense_ratio,
                    stats.dividend_yield,
                    stats.aum,
                    stats.avg_volume,
                ]
            )


# ── Main fetch function ───────────────────────────────────────────────────────


def fetch_all_etf_data(use_cache: bool = True) -> dict[str, ETFData]:
    """
    Fetch all ETF data. Returns dict of ticker → ETFData.

    Data quality per ETF is logged as: full | partial | holdings_only | failed
    """
    results: dict[str, ETFData] = {}
    price_cache = _read_prices_cache() if use_cache else {}
    stats_cache = _read_stats_cache() if use_cache else {}

    price_results: dict[str, ETFPriceData] = {}
    stats_results: dict[str, ETFStats] = {}

    data_quality: dict[str, str] = {}

    print(f"\n{'='*60}")
    print(f"FETCHING ETF DATA — {len(ETFS)} ETFs")
    print(f"{'='*60}")

    for ticker in ETFS:
        prices = None
        if ticker in price_cache:
            cached = price_cache[ticker]
            prices = ETFPriceData(
                ticker=ticker,
                prices_252d=cached,
                dates=[],
                returns_126d=cached[-125:] if len(cached) > 125 else [],
                volume_252d=[0] * len(cached),
            )
            data_quality[ticker] = "full (cache)"
            print(f"  [CACHE]  {ticker}: using cached price data ({len(cached)} days)")
        else:
            print(f"  LIVE     {ticker}: fetching from yfinance...", end=" ", flush=True)
            prices = fetch_price_history(ticker)
            if prices:
                price_results[ticker] = prices
                print(f"OK ({len(prices.prices_252d)} prices)")
            else:
                print("FAILED")

        stats = None
        if ticker in stats_cache:
            stats = stats_cache[ticker]
            data_quality[ticker] = data_quality.get(ticker, "stats_only")
            print(f"  [CACHE]  {ticker}: using cached stats")
        else:
            stats = fetch_stats(ticker)
            if stats:
                stats_results[ticker] = stats
            else:
                print(f"  WARN     {ticker}: no stats available")

        # Holdings — always try live (no cache)
        holdings = fetch_holdings(ticker)

        if prices and stats:
            data_quality[ticker] = "full"
        elif prices and not stats:
            data_quality[ticker] = "partial"
        elif not prices and stats:
            data_quality[ticker] = "holdings_only"
        else:
            data_quality[ticker] = "failed"

        results[ticker] = ETFData(ticker=ticker, prices=prices, stats=stats, holdings=holdings)

    # Write caches
    if price_results:
        all_prices = {t: r.prices for t, r in results.items() if r.prices}
        _write_prices_cache({t: results[t].prices for t in all_prices if results[t].prices})
        print(f"\n  Wrote {len(price_results)} price records to cache")
    if stats_results:
        _write_stats_cache(stats_results)
        print(f"  Wrote {len(stats_results)} stats records to cache")

    # Summary table
    print(f"\n{'='*60}")
    print("DATA QUALITY SUMMARY")
    print(f"{'='*60}")
    print(f"{'Ticker':<8} {'Quality':<20} {'Prices':>8} {'Stats':>6} {'Holdings':>10}")
    print("-" * 60)
    for ticker in ETFS:
        d = results[ticker]
        q = data_quality.get(ticker, "?")
        n_prices = len(d.prices.prices_252d) if d.prices else 0
        n_stats = "yes" if d.stats else "no"
        n_hold = len(d.holdings.holdings) if d.holdings else 0
        print(f"{ticker:<8} {q:<20} {n_prices:>8} {n_stats:>6} {n_hold:>10}")

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch ETF data from yfinance")
    parser.add_argument("--no-cache", action="store_true", help="Skip CSV cache")
    args = parser.parse_args()

    data = fetch_all_etf_data(use_cache=not args.no_cache)
    print(f"\nFetched data for {len(data)} ETFs")
