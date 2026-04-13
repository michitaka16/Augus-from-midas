#!/usr/bin/env python3
"""
Run a full backtest for a model portfolio.

Usage:
    uv run python scripts/run_backtest.py growth                    # Full 2000-present
    uv run python scripts/run_backtest.py growth 2015-01-01 2024-12-31  # Custom range
    uv run python scripts/run_backtest.py all                       # All 5 portfolios

Runs walk-forward + CPCV. Reports Sharpe, Deflated Sharpe, PBO.
Checks mandatory benchmark gate (must beat 60/40 net of costs).
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import structlog

logger = structlog.get_logger(__name__)

ALL_PORTFOLIOS = ["aggressive_growth", "growth", "balanced", "conservative", "income"]


async def run_single(portfolio_id: str, start: date, end: date):
    from midas_data.fabric import DataFabric
    from midas_backtest.engine.walkforward import WalkForwardEngine
    from midas_backtest.engine.cpcv import CPCVEngine
    from midas_backtest.metrics import annualized_sharpe, max_drawdown_from_returns
    from midas_backtest.metrics.drawdown import compute_drawdown_metrics
    from midas_backtest.metrics.benchmark import benchmark_60_40, benchmark_vti
    from midas_strategy.sleeves import get_primary_tickers

    print(f"\n{'='*60}")
    print(f"Backtest: {portfolio_id} ({start} to {end})")
    print(f"{'='*60}")

    fabric = DataFabric()
    await fabric.initialize()

    try:
        # 1. Walk-forward
        print("\n1. Running walk-forward validation...")
        wf_engine = WalkForwardEngine(initial_train_years=3, test_step_years=1)
        wf_result = await wf_engine.run(fabric, portfolio_id, start, end)

        print(f"   Periods: {wf_result.n_periods}")
        print(f"   Total Return: {wf_result.total_return:.2%}")
        print(f"   Annualized Return: {wf_result.annualized_return:.2%}")
        print(f"   Sharpe: {wf_result.sharpe:.3f}")
        print(f"   Max Drawdown: {wf_result.max_drawdown:.2%}")
        print(f"   Avg Turnover: {wf_result.avg_turnover:.2%}")
        print(f"   Avg Cost Drag: {wf_result.avg_cost_drag:.4%}")

        # 2. CPCV
        print("\n2. Running CPCV (Combinatorial Purged Cross-Validation)...")
        all_returns = []
        for p in wf_result.periods:
            all_returns.extend(p.returns)

        if all_returns:
            cpcv_engine = CPCVEngine(n_groups=10, purge_days=5, embargo_days=2)
            cpcv_result = await cpcv_engine.run(all_returns)
            print(f"   Splits: {cpcv_result.n_splits}")
            print(f"   Mean OOS Sharpe: {cpcv_result.mean_sharpe:.3f}")
            print(f"   PBO: {cpcv_result.pbo:.1%}")

            # PBO gate
            if cpcv_result.pbo > 0.4:
                print(f"   ⚠ WARNING: PBO {cpcv_result.pbo:.1%} > 40% threshold — strategy may be overfit")
            else:
                print(f"   ✓ PBO below 40% threshold")
        else:
            print("   Skipped — no returns data")
            cpcv_result = None

        # 3. Benchmark comparison (mandatory per PC2)
        print("\n3. Benchmark comparison (mandatory)...")
        primary = get_primary_tickers()
        spy_bars = await fabric.get_bars(primary.get("equity_sector", "SPY"), start, end)
        tlt_bars = await fabric.get_bars(primary.get("govt_bonds_long", "TLT"), start, end)

        spy_returns = _bars_to_returns(spy_bars)
        tlt_returns = _bars_to_returns(tlt_bars)

        bm_60_40 = benchmark_60_40(spy_returns, tlt_returns)
        bm_vti = benchmark_vti(spy_returns)

        print(f"   vs 60/40: Sharpe {bm_60_40.sharpe:.3f}, Return {bm_60_40.total_return:.2%}")
        print(f"   vs VTI:   Sharpe {bm_vti.sharpe:.3f}, Return {bm_vti.total_return:.2%}")

        # Benchmark gate
        if wf_result.sharpe > bm_60_40.sharpe:
            print(f"   ✓ BEATS 60/40 (Sharpe {wf_result.sharpe:.3f} > {bm_60_40.sharpe:.3f})")
        else:
            print(f"   ✗ FAILS benchmark gate (Sharpe {wf_result.sharpe:.3f} ≤ {bm_60_40.sharpe:.3f})")
            print(f"   This portfolio would NOT ship per PC2 resolution.")

        # 4. Drawdown metrics
        print("\n4. Drawdown analysis...")
        dd = compute_drawdown_metrics(all_returns)
        print(f"   Max Drawdown: {dd.max_drawdown:.2%}")
        print(f"   Max DD Duration: {dd.max_drawdown_duration_days} days")

        # 5. Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY: {portfolio_id}")
        print(f"  Sharpe:           {wf_result.sharpe:.3f}")
        print(f"  PBO:              {cpcv_result.pbo:.1%}" if cpcv_result else "  PBO:              N/A")
        print(f"  Beats 60/40:      {'YES' if wf_result.sharpe > bm_60_40.sharpe else 'NO'}")
        print(f"  Max Drawdown:     {dd.max_drawdown:.2%}")
        print(f"  Ship:             {'YES' if wf_result.sharpe > bm_60_40.sharpe and (not cpcv_result or cpcv_result.pbo < 0.4) else 'NO'}")
        print(f"{'='*60}")

    finally:
        await fabric.close()


def _bars_to_returns(bars: list[dict]) -> list[float]:
    """Convert bar list to daily returns."""
    returns = []
    for i in range(1, len(bars)):
        prev = float(bars[i - 1].get("adj_close", bars[i - 1].get("close", 0)))
        curr = float(bars[i].get("adj_close", bars[i].get("close", 0)))
        if prev > 0:
            returns.append((curr - prev) / prev)
    return returns


async def run_all(start: date, end: date):
    for pid in ALL_PORTFOLIOS:
        await run_single(pid, start, end)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    portfolio = sys.argv[1]
    start = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2000, 1, 1)
    end = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else date.today()

    if portfolio == "all":
        asyncio.run(run_all(start, end))
    elif portfolio in ALL_PORTFOLIOS:
        asyncio.run(run_single(portfolio, start, end))
    else:
        print(f"Unknown portfolio: {portfolio}")
        print(f"Available: {', '.join(ALL_PORTFOLIOS)} or 'all'")
        sys.exit(1)


if __name__ == "__main__":
    main()
