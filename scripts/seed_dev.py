#!/usr/bin/env python3
"""
Midas development seed data.

Populates the local database with rich sample data so the product
demonstrates all features out of the box:
- 10 sleeve ETFs + bars for all of them
- All 8 regime signals for current date
- Signals for all 5 model portfolios
- Backtest runs for all 5 portfolios with realistic metrics
- Pending approval for the current user (if any)
- News items with embeddings
- Audit trail entries showing the flow

Deterministic (seeded random) so local dev is reproducible.

Usage:
    uv run python scripts/seed_dev.py

NOT for production — gated by MIDAS_ENV=development check.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# ── Portfolio allocations (target weights by regime) ──
PORTFOLIO_ALLOCATIONS = {
    "aggressive_growth": {
        "normal": {"SPY": 0.35, "QQQ": 0.20, "VWO": 0.15, "GLD": 0.10, "VNQ": 0.10, "DJP": 0.05},
        "cautious": {"SPY": 0.20, "GLD": 0.20, "IEF": 0.20, "TLT": 0.15, "VNQ": 0.10},
        "turbulent": {"SHY": 0.80, "GLD": 0.20},
    },
    "growth": {
        "normal": {"SPY": 0.25, "GLD": 0.15, "TLT": 0.10, "VNQ": 0.10, "LQD": 0.10, "VWO": 0.15, "VYM": 0.10, "DJP": 0.05},
        "cautious": {"SPY": 0.15, "GLD": 0.20, "TLT": 0.20, "LQD": 0.20, "VYM": 0.10, "SHY": 0.15},
        "turbulent": {"SHY": 0.80, "GLD": 0.20},
    },
    "balanced": {
        "normal": {"SPY": 0.20, "GLD": 0.10, "IEF": 0.15, "TLT": 0.15, "LQD": 0.15, "VNQ": 0.10, "VYM": 0.10, "VWO": 0.05},
        "cautious": {"IEF": 0.25, "TLT": 0.20, "LQD": 0.20, "GLD": 0.15, "SPY": 0.10, "VYM": 0.10},
        "turbulent": {"SHY": 0.70, "GLD": 0.20, "LQD": 0.10},
    },
    "conservative": {
        "normal": {"IEF": 0.25, "LQD": 0.20, "SHY": 0.15, "TLT": 0.15, "SPY": 0.10, "VYM": 0.10, "GLD": 0.05},
        "cautious": {"SHY": 0.30, "IEF": 0.25, "LQD": 0.20, "GLD": 0.15, "VYM": 0.10},
        "turbulent": {"SHY": 0.80, "GLD": 0.10, "LQD": 0.10},
    },
    "income": {
        "normal": {"VYM": 0.30, "LQD": 0.20, "VNQ": 0.15, "IEF": 0.15, "TLT": 0.10, "SPY": 0.05, "GLD": 0.05},
        "cautious": {"VYM": 0.25, "LQD": 0.25, "IEF": 0.20, "TLT": 0.15, "VNQ": 0.10, "GLD": 0.05},
        "turbulent": {"VYM": 0.30, "LQD": 0.30, "SHY": 0.30, "GLD": 0.10},
    },
}

REGIME_SIGNALS = {
    "hy_oas": 345.0,
    "vix3m_backwardation": 0.92,
    "pc1_variance": 0.34,
    "vix_level": 14.2,
    "sma200_persistence": 42.0,
    "realized_vol_21d": 11.3,
    "yield_curve_3m10y": 1.48,
    "ensemble": 0.28,
}

SIGNAL_WEIGHTS = {
    "hy_oas": 0.25,
    "vix3m_backwardation": 0.20,
    "pc1_variance": 0.20,
    "vix_level": 0.10,
    "sma200_persistence": 0.10,
    "realized_vol_21d": 0.10,
    "yield_curve_3m10y": 0.05,
}


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
    rng = random.Random(42)
    today = date.today()

    try:
        # ── 1. Seed ETF universe ──
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

        # ── 2. Seed bars for ALL sleeve ETFs (1 year ending today) ──
        sample_tickers = ["SPY", "GLD", "TLT", "VNQ", "QQQ", "SHY", "IEF", "LQD", "VYM", "VWO", "DJP", "SLV"]
        start = today - timedelta(days=400)
        end = today

        base_prices = {
            "SPY": 550.0, "QQQ": 480.0, "GLD": 240.0, "SLV": 28.0,
            "SHY": 82.0, "IEF": 95.0, "TLT": 92.0, "LQD": 110.0,
            "VNQ": 90.0, "DJP": 25.0, "VYM": 125.0, "VWO": 45.0,
        }
        daily_vol = {
            "SPY": 0.011, "QQQ": 0.014, "GLD": 0.009, "SLV": 0.015,
            "SHY": 0.002, "IEF": 0.004, "TLT": 0.008, "LQD": 0.003,
            "VNQ": 0.012, "DJP": 0.010, "VYM": 0.010, "VWO": 0.013,
        }

        bar_count = 0
        for ticker in sample_tickers:
            price = base_prices.get(ticker, 100.0)
            vol_pct = daily_vol.get(ticker, 0.01)
            current = start
            local_rng = random.Random(hash(ticker) & 0xFFFFFFFF)

            while current <= end:
                if current.weekday() < 5:
                    daily_return = local_rng.gauss(0.0003, vol_pct)
                    price *= (1 + daily_return)
                    high = price * (1 + abs(local_rng.gauss(0, vol_pct * 0.5)))
                    low = price * (1 - abs(local_rng.gauss(0, vol_pct * 0.5)))
                    vol = max(int(local_rng.gauss(base_prices.get(ticker, 100) * 100_000, 2_000_000)), 100_000)

                    await conn.execute(
                        """INSERT INTO bars (ticker, date, open, high, low, close, adj_close, volume, source)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT DO NOTHING""",
                        ticker, current,
                        round(price * (1 + local_rng.gauss(0, vol_pct * 0.3)), 2),
                        round(high, 2),
                        round(low, 2),
                        round(price, 2),
                        round(price, 2),
                        vol,
                        "seed",
                    )
                    bar_count += 1
                current += timedelta(days=1)

        # ── 3. Seed ALL 8 regime signals for today ──
        for signal_name, value in REGIME_SIGNALS.items():
            await conn.execute(
                """INSERT INTO regime_signals (date, signal_name, value, ensemble_score, regime, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING""",
                today, signal_name, value, 0.28, "normal", "seed",
            )

        # Also seed a few days of regime history for the Dashboard
        for days_ago in [1, 2, 3, 7, 14, 30, 60, 90, 180, 365]:
            hist_date = today - timedelta(days=days_ago)
            hist_score = 0.28 + (days_ago % 3) * 0.05  # Vary slightly
            hist_regime = "normal" if hist_score < 0.35 else "cautious"
            await conn.execute(
                """INSERT INTO regime_signals (date, signal_name, value, ensemble_score, regime, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING""",
                hist_date, "ensemble", hist_score, hist_score, hist_regime, "seed",
            )

        # ── 4. Seed signals for ALL 5 portfolios (current + 4 weekly history) ──
        signal_ids = {}
        for weeks_ago in range(5):
            signal_date = datetime.combine(today - timedelta(days=weeks_ago * 7), datetime.min.time().replace(hour=19))
            for portfolio_id in ["aggressive_growth", "growth", "balanced", "conservative", "income"]:
                allocations = PORTFOLIO_ALLOCATIONS[portfolio_id]["normal"]
                cost = round(rng.uniform(3.5, 8.5), 2)
                ensemble = round(0.20 + rng.uniform(0, 0.15), 3)
                reasoning = {
                    "regime": f"Normal regime (score {ensemble:.3f}, confidence 82%)",
                    "allocation": f"Selected {len(allocations)} sleeves, vol target {14 if portfolio_id == 'growth' else (18 if portfolio_id == 'aggressive_growth' else (10 if portfolio_id == 'balanced' else 6))}%",
                    "cost": f"Total rebalance cost: ${cost:.2f}",
                }

                signal_id = await conn.fetchval(
                    """INSERT INTO signals (model_portfolio_id, timestamp, regime, allocations_json, reasoning_json, cost_estimate_json, ensemble_score, published, published_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT DO NOTHING
                    RETURNING id""",
                    portfolio_id, signal_date, "normal",
                    json.dumps(allocations),
                    json.dumps(reasoning),
                    json.dumps({"total": cost, "commission": round(cost * 0.45, 2), "slippage": round(cost * 0.30, 2), "impact": round(cost * 0.20, 2), "fees": round(cost * 0.05, 2)}),
                    ensemble, True, signal_date,
                )
                if weeks_ago == 0 and signal_id:
                    signal_ids[portfolio_id] = signal_id

        # ── 5. Seed backtest runs for all 5 portfolios ──
        backtest_stats = {
            "aggressive_growth": {"sharpe": 0.84, "dsr": 0.61, "pbo": 0.28, "max_dd": -0.312, "worst_12m": -0.183, "return_annual": 0.118},
            "growth": {"sharpe": 0.72, "dsr": 0.58, "pbo": 0.31, "max_dd": -0.241, "worst_12m": -0.141, "return_annual": 0.092},
            "balanced": {"sharpe": 0.65, "dsr": 0.52, "pbo": 0.33, "max_dd": -0.158, "worst_12m": -0.088, "return_annual": 0.068},
            "conservative": {"sharpe": 0.54, "dsr": 0.43, "pbo": 0.36, "max_dd": -0.082, "worst_12m": -0.047, "return_annual": 0.045},
            "income": {"sharpe": 0.52, "dsr": 0.41, "pbo": 0.37, "max_dd": -0.091, "worst_12m": -0.052, "return_annual": 0.048},
        }

        for portfolio_id, stats in backtest_stats.items():
            horizons = [
                {"name": "1-year", "sharpe": stats["sharpe"] + 0.15, "max_dd": stats["max_dd"] * 0.5, "turnover": 1.42, "cost_drag": 0.0031, "return": stats["return_annual"] * 1.1},
                {"name": "3-year", "sharpe": stats["sharpe"] + 0.08, "max_dd": stats["max_dd"] * 0.7, "turnover": 1.28, "cost_drag": 0.0028, "return": stats["return_annual"] * 3.2},
                {"name": "5-year", "sharpe": stats["sharpe"] + 0.03, "max_dd": stats["max_dd"] * 0.85, "turnover": 1.19, "cost_drag": 0.0025, "return": stats["return_annual"] * 5.1},
                {"name": "10-year", "sharpe": stats["sharpe"] - 0.04, "max_dd": stats["max_dd"] * 0.95, "turnover": 1.12, "cost_drag": 0.0022, "return": stats["return_annual"] * 9.2},
                {"name": "Full (26y)", "sharpe": stats["sharpe"], "max_dd": stats["max_dd"], "turnover": 1.08, "cost_drag": 0.0020, "return": stats["return_annual"] * 18.5},
            ]
            benchmarks = [
                {"name": "60/40 (SPY/TLT)", "sharpe": 0.48, "total_return": 1.42, "max_drawdown": -0.22, "cost_drag_pct": 0.0},
                {"name": "Equal Weight", "sharpe": 0.61, "total_return": 1.85, "max_drawdown": -0.28, "cost_drag_pct": 0.001},
                {"name": "VTI", "sharpe": 0.65, "total_return": 2.12, "max_drawdown": -0.34, "cost_drag_pct": 0.0},
            ]
            results = {
                "sharpe": stats["sharpe"],
                "total_return": stats["return_annual"] * 18.5,
                "annualized_return": stats["return_annual"],
                "annualized_vol": stats["return_annual"] / stats["sharpe"],
                "max_drawdown": stats["max_dd"],
                "max_drawdown_duration_days": 380,
                "avg_cost_drag_pct": 0.0020,
                "avg_turnover": 1.08,
                "beats_60_40": True,
            }

            await conn.execute(
                """INSERT INTO backtest_runs (model_portfolio_id, started_at, results_json, horizons_json, benchmarks_json,
                    deflated_sharpe, pbo, worst_12m_return, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                portfolio_id,
                datetime.utcnow() - timedelta(hours=6),
                json.dumps(results),
                json.dumps(horizons),
                json.dumps(benchmarks),
                stats["dsr"],
                stats["pbo"],
                stats["worst_12m"],
                "completed",
            )

        # ── 6. Seed news items ──
        news_items = [
            ("Markets rally as Fed signals rate pause", "The Federal Reserve indicated a pause in rate hikes following improving inflation data.", "2026-04-10T14:30:00Z"),
            ("Credit spreads tighten on Treasury outperformance", "HY OAS narrowed 15bps this week as investors embraced risk.", "2026-04-09T11:00:00Z"),
            ("VIX settles below 15 amid calm trading", "Implied volatility continues its descent, reaching 4-month lows.", "2026-04-08T16:00:00Z"),
            ("Gold gains 2% on geopolitical tensions", "Safe-haven demand pushes gold above $2,400/oz.", "2026-04-07T09:00:00Z"),
            ("Yield curve steepens as long-end rises", "The 3m10y spread widened to 148bps, signaling economic confidence.", "2026-04-06T15:00:00Z"),
        ]
        for title, content, published in news_items:
            await conn.execute(
                """INSERT INTO news_items (source, published_at, title, content, summary, perplexity_citations_json, query)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING""",
                "perplexity", datetime.fromisoformat(published.replace("Z", "+00:00")),
                title, content, content[:100], "[]", "market_overview",
            )

        # ── 6.5. Seed a pending approval for every existing user ──
        # So users who log in see an actionable approval card immediately
        users = await conn.fetch("SELECT id FROM users.accounts")
        growth_signal_id = signal_ids.get("growth")
        approvals_seeded = 0
        if growth_signal_id and users:
            trades_json = json.dumps([
                {"ticker": "GLD", "direction": "buy", "shares": 15, "value": 2847.0, "cost": 1.02},
                {"ticker": "TLT", "direction": "sell", "shares": 8, "value": 832.0, "cost": 0.68},
                {"ticker": "VWO", "direction": "sell", "shares": 5, "value": 240.0, "cost": 0.22},
            ])
            for row in users:
                # Check if user already has a pending approval for this signal
                existing = await conn.fetchval(
                    "SELECT id FROM users.approvals WHERE user_id = $1 AND signal_id = $2",
                    row["id"], growth_signal_id,
                )
                if not existing:
                    await conn.execute(
                        """INSERT INTO users.approvals (user_id, signal_id, status, trades_json)
                        VALUES ($1, $2, 'pending', $3)""",
                        row["id"], growth_signal_id, trades_json,
                    )
                    approvals_seeded += 1

        # ── 7. Seed audit trail with realistic flow ──
        prev_hash = "0" * 64
        for weeks_ago in range(5):
            ts = datetime.utcnow() - timedelta(days=weeks_ago * 7, hours=1)
            for event_type, payload_dict in [
                ("signal_published", {"portfolio": "growth", "regime": "normal", "cost": 4.52}),
                ("regime_changed", {"from": "normal", "to": "normal", "date": str(today - timedelta(days=weeks_ago * 7))}),
            ]:
                payload_str = json.dumps(payload_dict, sort_keys=True)
                combined = prev_hash + payload_str
                hash_val = hashlib.sha256(combined.encode()).hexdigest()
                await conn.execute(
                    """INSERT INTO audit_trail (prev_hash, timestamp, event_type, payload_json, actor, hash)
                    VALUES ($1, $2, $3, $4, $5, $6)""",
                    prev_hash, ts, event_type, payload_str, "system", hash_val,
                )
                prev_hash = hash_val

        print("Seed data loaded successfully.")
        print(f"  ETFs:              {len(etfs)}")
        print(f"  Bars:              ~{bar_count} ({len(sample_tickers)} tickers x ~260 days)")
        print(f"  Regime signals:    {len(REGIME_SIGNALS)} current + 10 historical")
        print(f"  Signals:           25 (5 portfolios x 5 weeks)")
        print(f"  Backtest runs:     5 (one per portfolio)")
        print(f"  News items:        {len(news_items)}")
        print(f"  Pending approvals: {approvals_seeded} (one per existing user)")
        print(f"  Audit trail:       10 entries")
        print("")
        print("Open http://localhost:3000 to see the populated dashboard.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
