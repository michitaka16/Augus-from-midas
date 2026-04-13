#!/usr/bin/env python3
"""
Midas development seed data.

Populates the local database with sample data for development.
Deterministic (seeded random) so local dev is reproducible.

Usage:
    uv run python scripts/seed_dev.py

NOT for production — gated by MIDAS_ENV=development check.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def seed():
    env = os.environ.get("MIDAS_ENV", "development")
    if env != "development":
        print(f"MIDAS_ENV={env} — seed data is only for development. Aborting.")
        sys.exit(1)

    try:
        import asyncpg
    except ImportError:
        print("asyncpg required. Install with: uv pip install asyncpg")
        sys.exit(1)

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set in .env")
        sys.exit(1)

    conn = await asyncpg.connect(url)
    rng = random.Random(42)  # Deterministic seed

    try:
        # Seed ETF universe
        etfs = [
            ("SPY", "SPDR S&P 500 ETF", "equity_sector", 0.0945, 80_000_000),
            ("QQQ", "Invesco QQQ", "equity_sector", 0.20, 50_000_000),
            ("GLD", "SPDR Gold Shares", "precious_metals", 0.40, 10_000_000),
            ("SLV", "iShares Silver Trust", "precious_metals", 0.50, 15_000_000),
            ("SHY", "iShares 1-3 Year Treasury", "govt_bonds_short", 0.15, 5_000_000),
            ("IEF", "iShares 7-10 Year Treasury", "govt_bonds_intermediate", 0.15, 8_000_000),
            ("TLT", "iShares 20+ Year Treasury", "govt_bonds_long", 0.15, 15_000_000),
            ("LQD", "iShares IG Corporate Bond", "ig_corp_bonds", 0.14, 10_000_000),
            ("VNQ", "Vanguard Real Estate ETF", "reits", 0.12, 5_000_000),
            ("DJP", "iPath Bloomberg Commodity", "commodities", 0.70, 3_000_000),
            ("VYM", "Vanguard High Dividend Yield", "dividend_etfs", 0.06, 3_000_000),
            ("VWO", "Vanguard FTSE Emerging Markets", "em_equity", 0.08, 10_000_000),
        ]

        for ticker, name, sleeve, er, adv in etfs:
            await conn.execute(
                """INSERT INTO etf_universe (ticker, name, inception_date, sleeve, expense_ratio, avg_daily_volume, liquidity_tier)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING""",
                ticker, name, date(2000, 1, 3), sleeve, er, adv,
                "high" if adv > 5_000_000 else "medium",
            )

        # Seed 1 year of sample bars for key ETFs
        sample_tickers = ["SPY", "GLD", "TLT", "VNQ"]
        start = date(2024, 1, 2)
        end = date(2024, 12, 31)

        for ticker in sample_tickers:
            base_price = {"SPY": 470.0, "GLD": 190.0, "TLT": 95.0, "VNQ": 85.0}[ticker]
            current = start
            price = base_price

            while current <= end:
                if current.weekday() < 5:  # Weekdays only
                    daily_return = rng.gauss(0.0003, 0.012)
                    price *= (1 + daily_return)
                    high = price * (1 + abs(rng.gauss(0, 0.005)))
                    low = price * (1 - abs(rng.gauss(0, 0.005)))
                    vol = int(rng.gauss(10_000_000, 2_000_000))

                    await conn.execute(
                        """INSERT INTO bars (ticker, date, open, high, low, close, adj_close, volume, source)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT DO NOTHING""",
                        ticker, current,
                        round(price * (1 + rng.gauss(0, 0.002)), 2),
                        round(high, 2),
                        round(low, 2),
                        round(price, 2),
                        round(price, 2),
                        max(vol, 100_000),
                        "seed",
                    )

                current += timedelta(days=1)

        # Seed a sample regime signal
        await conn.execute(
            """INSERT INTO regime_signals (date, signal_name, value, ensemble_score, regime, source)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING""",
            date(2024, 12, 31), "ensemble", 0.28, 0.28, "normal", "seed",
        )

        # Seed a sample signal for Growth portfolio
        await conn.execute(
            """INSERT INTO signals (model_portfolio_id, timestamp, regime, allocations_json, reasoning_json, cost_estimate_json, ensemble_score, published, published_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT DO NOTHING""",
            "growth",
            datetime(2024, 12, 29, 19, 0, 0),
            "normal",
            json.dumps({"SPY": 0.25, "GLD": 0.15, "TLT": 0.10, "VNQ": 0.10, "LQD": 0.10, "VWO": 0.15, "VYM": 0.10, "DJP": 0.05}),
            json.dumps({"summary": "Normal regime. Equity and EM momentum strong."}),
            json.dumps({"total": 4.52, "commission": 2.10, "slippage": 1.42, "impact": 0.80, "fees": 0.20}),
            0.28,
            True,
            datetime(2024, 12, 29, 19, 0, 0),
        )

        print("Seed data loaded successfully.")
        print(f"  ETFs: {len(etfs)}")
        print(f"  Bars: ~{len(sample_tickers) * 252} (4 tickers x 1 year)")
        print(f"  Regime signal: 1")
        print(f"  Sample signal: 1 (Growth portfolio)")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
