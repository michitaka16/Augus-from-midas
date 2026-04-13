#!/usr/bin/env python3
"""
Generate signals for all 5 model portfolios.

Usage:
    uv run python scripts/generate_signals.py               # Use last Friday
    uv run python scripts/generate_signals.py 2024-12-27     # Specific date

This runs the full strategy pipeline:
  TimeSource → data fetch → regime detection → allocator → cost model → signal output

Writes to: signals + signal_inputs tables. Publishes immediately.
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


async def run(target_date: date | None = None):
    from midas_data.fabric import DataFabric
    from midas_api.scheduler.signal_cron import SignalScheduler

    fabric = DataFabric()
    await fabric.initialize()

    scheduler = SignalScheduler(fabric)

    try:
        result = await scheduler.run_weekly(target_date=target_date)
        print(f"\nSignal generation result: {result['status']}")

        if result["status"] == "published":
            for portfolio_id, info in result.get("signals", {}).items():
                print(f"  {portfolio_id}: signal_id={info['signal_id']}, "
                      f"regime={info['regime']}, sleeves={info['n_sleeves']}, "
                      f"cost=${info['cost']:.2f}")
        elif result["status"] == "skipped":
            print(f"  Reason: {result.get('reason', 'unknown')}")
        elif result["status"] == "failed":
            print(f"  Reason: {result.get('reason', 'unknown')}")
            sys.exit(1)
    finally:
        await fabric.close()


def main():
    target = None
    if len(sys.argv) > 1:
        target = date.fromisoformat(sys.argv[1])
        print(f"Generating signals for: {target}")
    else:
        print("Generating signals for last Friday...")

    asyncio.run(run(target))


if __name__ == "__main__":
    main()
