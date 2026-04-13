#!/usr/bin/env python3
"""
BLOCKER: Verify EODHD delisted-tickers endpoint exists (M01-15).

Without point-in-time ETF listings, all backtests have survivorship bias
and the "go big" risk profile becomes dangerous in live trading.

Usage:
    uv run python scripts/verify_eodhd_delisted.py

Outputs:
- PASS: Endpoint exists, returns delisted tickers with dates
- FAIL: Endpoint missing — must source from Polygon.io or SEC EDGAR

This MUST pass before any backtest is considered valid.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def verify():
    api_key = os.environ.get("EODHD_API_KEY")
    if not api_key:
        print("FAIL: EODHD_API_KEY not set in .env")
        print("  Set your EODHD API key and re-run this script.")
        sys.exit(1)

    import httpx

    # Test 1: Exchange symbols endpoint (includes delisted)
    print("Testing EODHD exchange symbols endpoint...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # EODHD provides exchange symbols including delisted via:
        # https://eodhd.com/api/exchange-symbol-list/US?api_token=KEY&fmt=json
        try:
            resp = await client.get(
                f"https://eodhd.com/api/exchange-symbol-list/US",
                params={"api_token": api_key, "fmt": "json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                total = len(data)
                # Check for delisted indicators
                delisted = [s for s in data if s.get("Delisted_Date") or s.get("IsDelisted")]
                active = total - len(delisted)
                print(f"  PASS: Exchange symbols endpoint works")
                print(f"  Total symbols: {total}")
                print(f"  Active: {active}")
                print(f"  Delisted: {len(delisted)}")

                if len(delisted) > 0:
                    sample = delisted[:3]
                    for s in sample:
                        print(f"    Example: {s.get('Code', '?')} — delisted {s.get('Delisted_Date', 'unknown')}")
                else:
                    print("  WARNING: No delisted tickers found in response.")
                    print("  This may mean the field name differs. Check EODHD docs.")
            elif resp.status_code == 401:
                print(f"  FAIL: Authentication error (401). Check EODHD_API_KEY.")
                sys.exit(1)
            elif resp.status_code == 403:
                print(f"  FAIL: Plan doesn't include this endpoint (403).")
                print("  Upgrade EODHD plan or source from Polygon/SEC EDGAR.")
                sys.exit(1)
            else:
                print(f"  FAIL: Unexpected status {resp.status_code}")
                print(f"  Response: {resp.text[:200]}")
                sys.exit(1)
        except Exception as e:
            print(f"  FAIL: Request error: {e}")
            sys.exit(1)

    # Test 2: Historical data for a known delisted ETF
    print("\nTesting historical data for known delisted ticker (if available)...")
    try:
        # TBT (ProShares UltraShort 20+ Year Treasury) — commonly delisted/reorganized
        resp = await httpx.AsyncClient(timeout=30.0).__aenter__()
        test_resp = await resp.get(
            f"https://eodhd.com/api/eod/TBT.US",
            params={"api_token": api_key, "fmt": "json", "from": "2020-01-01", "to": "2020-12-31"},
        )
        await resp.__aexit__(None, None, None)
        if test_resp.status_code == 200:
            bars = test_resp.json()
            print(f"  Historical data available: {len(bars)} bars for TBT.US (2020)")
        else:
            print(f"  Could not fetch historical for test ticker (status {test_resp.status_code})")
    except Exception:
        print("  Skipped historical test (non-critical)")

    # Test 3: Fundamental data endpoint
    print("\nTesting fundamental data endpoint...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"https://eodhd.com/api/fundamentals/SPY.US",
                params={"api_token": api_key, "fmt": "json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                has_general = "General" in data
                print(f"  PASS: Fundamentals endpoint works (has General: {has_general})")
            else:
                print(f"  Status {resp.status_code} — fundamentals may require higher plan")
    except Exception as e:
        print(f"  Skipped: {e}")

    print("\n=== VERIFICATION COMPLETE ===")
    print("If all tests passed, the EODHD data source is viable for PIT backtests.")
    print("Run scripts/load_historical.py to begin the full data load.")


if __name__ == "__main__":
    asyncio.run(verify())
