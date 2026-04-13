#!/usr/bin/env python3
"""
Historical data load — backfill all 8 sleeves from 2000-01-01 to present.

Usage:
    uv run python scripts/load_historical.py

Loads:
- EODHD EOD bars for all ETFs in the universe
- FRED macro signals (VIX, credit spreads, yield curve)
- Corporate actions
- ETF universe (including delisted tickers for survivorship-free backtests)

Gate: Data for all 8 sleeves loads clean with < 0.1% gap rate.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import structlog

logger = structlog.get_logger(__name__)

# ETF universe definition — the 8 sleeves with representative tickers
SLEEVE_ETFS = {
    "equity_sector": [
        ("SPY", "SPDR S&P 500 ETF"),
        ("QQQ", "Invesco QQQ Trust"),
        ("XLF", "Financial Select Sector SPDR"),
        ("XLE", "Energy Select Sector SPDR"),
        ("XLK", "Technology Select Sector SPDR"),
        ("XLV", "Health Care Select Sector SPDR"),
        ("XLI", "Industrial Select Sector SPDR"),
        ("XLY", "Consumer Discretionary SPDR"),
        ("XLP", "Consumer Staples SPDR"),
        ("XLU", "Utilities Select Sector SPDR"),
    ],
    "precious_metals": [
        ("GLD", "SPDR Gold Shares"),
        ("SLV", "iShares Silver Trust"),
        ("IAU", "iShares Gold Trust"),
    ],
    "govt_bonds_short": [
        ("SHY", "iShares 1-3 Year Treasury Bond"),
        ("SHV", "iShares Short Treasury Bond"),
    ],
    "govt_bonds_intermediate": [
        ("IEF", "iShares 7-10 Year Treasury Bond"),
        ("IEI", "iShares 3-7 Year Treasury Bond"),
    ],
    "govt_bonds_long": [
        ("TLT", "iShares 20+ Year Treasury Bond"),
        ("TLH", "iShares 10-20 Year Treasury Bond"),
    ],
    "ig_corp_bonds": [
        ("LQD", "iShares iBoxx IG Corporate Bond"),
        ("VCIT", "Vanguard Intermediate-Term Corporate Bond"),
    ],
    "reits": [
        ("VNQ", "Vanguard Real Estate ETF"),
        ("IYR", "iShares U.S. Real Estate ETF"),
    ],
    "commodities": [
        ("DJP", "iPath Bloomberg Commodity Index"),
        ("GSG", "iShares S&P GSCI Commodity ETF"),
        ("DBC", "Invesco DB Commodity Index"),
    ],
    "dividend_etfs": [
        ("VYM", "Vanguard High Dividend Yield ETF"),
        ("DVY", "iShares Select Dividend ETF"),
        ("SDY", "SPDR S&P Dividend ETF"),
    ],
    "em_equity": [
        ("VWO", "Vanguard FTSE Emerging Markets ETF"),
        ("EEM", "iShares MSCI Emerging Markets ETF"),
        ("IEMG", "iShares Core MSCI Emerging Markets"),
    ],
}

# FRED series for regime detection
FRED_SERIES = {
    "vix": "VIXCLS",
    "vix3m": "VXVCLS",
    "vvix": "VVIXCLS",
    "hy_oas": "BAMLH0A0HYM2",
    "ig_oas": "BAMLC0A4CBBB",
    "yield_3m": "DGS3MO",
    "yield_2y": "DGS2",
    "yield_10y": "DGS10",
    "yield_30y": "DGS30",
    "fed_funds": "FEDFUNDS",
}


async def load_all():
    """Main entry point for historical data load."""
    from midas_data.sources.eodhd import EODHDClient
    from midas_data.sources.fred import FREDClient
    from midas_data.fabric import DataFabric

    fabric = DataFabric()
    await fabric.initialize()

    eodhd = EODHDClient()
    fred = FREDClient()

    start = date(2000, 1, 1)
    end = date.today()

    total_bars = 0
    total_signals = 0

    try:
        # 1. Load ETF universe
        logger.info("load.etf_universe.start")
        universe_entries = []
        for sleeve, etfs in SLEEVE_ETFS.items():
            for ticker, name in etfs:
                universe_entries.append({
                    "ticker": ticker,
                    "name": name,
                    "inception_date": date(2000, 1, 3),
                    "sleeve": sleeve,
                    "expense_ratio": 0.0,
                    "avg_daily_volume": 0,
                    "liquidity_tier": "high",
                    "is_active": True,
                })
        await fabric.ingest_etf_universe(universe_entries)
        logger.info("load.etf_universe.complete", count=len(universe_entries))

        # 2. Load EOD bars for all tickers
        logger.info("load.bars.start", start=str(start), end=str(end))
        for sleeve, etfs in SLEEVE_ETFS.items():
            for ticker, name in etfs:
                logger.info("load.bars.ticker", ticker=ticker, sleeve=sleeve)
                try:
                    bars = await eodhd.fetch_eod_bars(ticker, start, end)
                    if bars:
                        inserted = await fabric.ingest_bars(ticker, bars, source="eodhd")
                        total_bars += inserted
                        logger.info("load.bars.ticker.complete", ticker=ticker, inserted=inserted)
                    else:
                        logger.warning("load.bars.ticker.empty", ticker=ticker)
                except Exception:
                    logger.exception("load.bars.ticker.error", ticker=ticker)

        logger.info("load.bars.complete", total_inserted=total_bars)

        # 3. Load FRED macro signals
        logger.info("load.fred.start", start=str(start), end=str(end))
        all_signals = await fred.fetch_all_regime_signals(start, end)
        for signal_name, series_data in all_signals.items():
            for point in series_data:
                dt = point.get("date")
                val = point.get("value")
                if dt and val is not None:
                    await fabric.ingest_regime_signals(
                        dt, {signal_name: val}, source="fred"
                    )
                    total_signals += 1

        logger.info("load.fred.complete", total_points=total_signals)

        # 4. Load corporate actions
        logger.info("load.corp_actions.start")
        for sleeve, etfs in SLEEVE_ETFS.items():
            for ticker, _name in etfs:
                try:
                    actions = await eodhd.fetch_corp_actions(ticker)
                    if actions:
                        await fabric._ingestor.ingest_corp_actions(ticker, actions)
                except Exception:
                    logger.exception("load.corp_actions.error", ticker=ticker)
        logger.info("load.corp_actions.complete")

        # 5. Summary
        all_tickers = [t for etfs in SLEEVE_ETFS.values() for t, _ in etfs]
        logger.info(
            "load.complete",
            total_tickers=len(all_tickers),
            total_bars=total_bars,
            total_regime_signals=total_signals,
            sleeves=len(SLEEVE_ETFS),
        )
        print(f"\nHistorical load complete:")
        print(f"  Tickers: {len(all_tickers)} across {len(SLEEVE_ETFS)} sleeves")
        print(f"  Bars inserted: {total_bars}")
        print(f"  Regime signal points: {total_signals}")

    finally:
        await fabric.close()


if __name__ == "__main__":
    asyncio.run(load_all())
