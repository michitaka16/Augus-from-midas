"""
Signal scheduler — weekly cron that generates signals for all 5 portfolios (M04-01).

Runs post-Friday-close, publishes Sunday 7 PM ET (configurable).
Idempotent: skips if signal already exists for this week.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SignalScheduler:
    """Weekly signal generation scheduler."""

    def __init__(self, data_fabric: Any):
        self._fabric = data_fabric

    async def run_weekly(self, target_date: date | None = None) -> dict:
        """Generate signals for all 5 model portfolios.

        Args:
            target_date: Override date (for testing). Defaults to last Friday.

        Returns:
            Dict with generation results per portfolio.
        """
        from midas_strategy.signals.time_source import TimeSource
        from midas_strategy.signals.workflow import generate_signals

        dt = target_date or self._last_friday()
        week_key = dt.isocalendar()[:2]  # (year, week_number)

        logger.info("signal_cron.start", date=str(dt), week=week_key)

        # Idempotency check
        existing = await self._fabric._conn.fetchrow(
            """SELECT id FROM signals
               WHERE model_portfolio_id = 'growth'
                 AND timestamp >= $1 AND timestamp < $2""",
            datetime(dt.year, dt.month, dt.day),
            datetime(dt.year, dt.month, dt.day) + timedelta(days=7),
        )
        if existing:
            logger.info("signal_cron.already_exists", week=week_key)
            return {"status": "skipped", "reason": "already_exists"}

        # Generate signals
        time_source = TimeSource.historical(dt)
        try:
            signals = await generate_signals(
                time_source=time_source,
                data_fabric=self._fabric,
            )
        except Exception:
            logger.exception("signal_cron.generation_failed")
            return {"status": "failed", "reason": "generation_error"}

        if not signals:
            logger.warning("signal_cron.no_signals_generated")
            return {"status": "failed", "reason": "no_signals"}

        # Persist all signals atomically
        results = {}
        async with self._fabric._conn.transaction():
            for signal in signals:
                signal_id = await self._fabric._conn.fetchval(
                    """INSERT INTO signals
                       (model_portfolio_id, timestamp, regime, allocations_json,
                        reasoning_json, cost_estimate_json, ensemble_score, published, published_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW())
                       RETURNING id""",
                    signal.model_portfolio_id,
                    signal.timestamp,
                    signal.regime.regime.value,
                    json.dumps({k: v for k, v in signal.allocation.weights.items()}),
                    json.dumps(signal.reasoning),
                    json.dumps({"total": signal.total_cost}),
                    signal.regime.ensemble_score,
                )

                # Store input snapshot for replay (TC2)
                await self._fabric._conn.execute(
                    """INSERT INTO signal_inputs (signal_id, snapshot_json)
                       VALUES ($1, $2)""",
                    signal_id,
                    json.dumps(signal.signal_values_snapshot, default=str),
                )

                results[signal.model_portfolio_id] = {
                    "signal_id": signal_id,
                    "regime": signal.regime.regime.value,
                    "n_sleeves": len(signal.allocation.weights),
                    "cost": signal.total_cost,
                }

        logger.info("signal_cron.complete", date=str(dt), portfolios=len(results))
        return {"status": "published", "signals": results}

    def _last_friday(self) -> date:
        today = date.today()
        days_since_friday = (today.weekday() - 4) % 7
        return today - timedelta(days=days_since_friday)
