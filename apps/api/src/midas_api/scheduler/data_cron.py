"""
Data refresh scheduler — daily/weekly/on-demand data ingestion (M04-04).

Daily: EODHD EOD bars + FRED macro signals after market close.
Weekly: Fundamentals + corporate actions.
On-demand: Screen-active pulls throttled to 1 req/10s per user.
Perplexity: On material price moves or debate chat open.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DataRefreshScheduler:
    """Scheduled data ingestion jobs."""

    def __init__(self, data_fabric: Any):
        self._fabric = data_fabric

    async def daily_refresh(self, target_date: date | None = None) -> dict:
        """Daily job: EOD bars + FRED signals after market close."""
        from midas_data.sources.eodhd import EODHDClient
        from midas_data.sources.fred import FREDClient
        from midas_strategy.sleeves import get_all_tickers

        dt = target_date or date.today()
        logger.info("data_refresh.daily.start", date=str(dt))

        eodhd = EODHDClient()
        fred = FREDClient()
        results = {"bars": 0, "signals": 0}

        # EOD bars for all tickers
        tickers = get_all_tickers()
        for ticker in tickers:
            try:
                bars = await eodhd.fetch_eod_bars(ticker, dt, dt)
                if bars:
                    inserted = await self._fabric.ingest_bars(ticker, bars)
                    results["bars"] += inserted
            except Exception:
                logger.exception("data_refresh.bar_error", ticker=ticker)

        # FRED regime signals
        try:
            all_signals = await fred.fetch_all_regime_signals(dt, dt)
            for signal_name, series_data in all_signals.items():
                for point in series_data:
                    if point.get("date") and point.get("value") is not None:
                        await self._fabric.ingest_regime_signals(
                            point["date"], {signal_name: point["value"]}
                        )
                        results["signals"] += 1
        except Exception:
            logger.exception("data_refresh.fred_error")

        logger.info("data_refresh.daily.complete", date=str(dt), results=results)
        return results

    async def weekly_refresh(self) -> dict:
        """Weekly job: Fundamentals + corporate actions."""
        from midas_data.sources.eodhd import EODHDClient
        from midas_strategy.sleeves import get_all_tickers

        logger.info("data_refresh.weekly.start")
        eodhd = EODHDClient()
        results = {"fundamentals": 0, "corp_actions": 0}

        for ticker in get_all_tickers():
            try:
                actions = await eodhd.fetch_corp_actions(ticker)
                if actions:
                    inserted = await self._fabric._ingestor.ingest_corp_actions(ticker, actions)
                    results["corp_actions"] += inserted
            except Exception:
                logger.exception("data_refresh.corp_action_error", ticker=ticker)

        logger.info("data_refresh.weekly.complete", results=results)
        return results

    async def on_demand_refresh(self, ticker: str, user_id: str | None = None) -> dict:
        """Screen-active pull: refresh bars since last fetch.

        Throttled to max 1 req/10s per user via Redis counter.
        """
        from midas_data.sources.eodhd import EODHDClient

        # Throttle check
        if user_id and self._fabric._cache:
            throttle_key = f"throttle:refresh:{user_id}"
            try:
                client = await self._fabric._cache._get_client()
                if await client.exists(throttle_key):
                    return {"status": "throttled"}
                await client.set(throttle_key, "1", ex=10)
            except Exception:
                pass  # Redis down — allow the request

        eodhd = EODHDClient()
        today = date.today()
        start = today - timedelta(days=7)  # Fetch last week to fill any gaps

        try:
            bars = await eodhd.fetch_eod_bars(ticker, start, today)
            if bars:
                inserted = await self._fabric.ingest_bars(ticker, bars)
                logger.info("data_refresh.on_demand", ticker=ticker, inserted=inserted)
                return {"status": "refreshed", "inserted": inserted}
        except Exception:
            logger.exception("data_refresh.on_demand_error", ticker=ticker)

        return {"status": "no_data"}
