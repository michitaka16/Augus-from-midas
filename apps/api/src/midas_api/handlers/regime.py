"""Regime + strategy health handlers (M07-07)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RegimeHandlers:
    def __init__(self, conn: Any):
        self._conn = conn

    async def get_current(self) -> dict:
        """GET /regime/current — current regime state + all signal values."""
        row = await self._conn.fetchrow(
            """SELECT date, signal_name, value, ensemble_score, regime
               FROM regime_signals
               WHERE ensemble_score IS NOT NULL
               ORDER BY date DESC LIMIT 1"""
        )
        if not row:
            return {"regime": "normal", "confidence": 0, "signals": {}}

        # Fetch all signal values for this date
        signals_rows = await self._conn.fetch(
            "SELECT signal_name, value FROM regime_signals WHERE date = $1",
            row["date"],
        )

        return {
            "regime": row["regime"] or "normal",
            "ensemble_score": row["ensemble_score"],
            "date": row["date"].isoformat(),
            "signals": {r["signal_name"]: r["value"] for r in signals_rows},
        }

    async def get_history(self, limit: int = 50) -> dict:
        """GET /regime/history — past regime transitions."""
        rows = await self._conn.fetch(
            """SELECT date, ensemble_score, regime
               FROM regime_signals
               WHERE regime IS NOT NULL AND ensemble_score IS NOT NULL
               ORDER BY date DESC LIMIT $1""",
            limit,
        )
        return {
            "transitions": [{
                "date": r["date"].isoformat(),
                "regime": r["regime"],
                "ensemble_score": r["ensemble_score"],
            } for r in rows],
        }

    async def get_strategy_health(self, model_portfolio_id: str) -> dict:
        """GET /health/strategy/{portfolio_id} — performance vs benchmark."""
        run = await self._conn.fetchrow(
            """SELECT results_json, benchmarks_json, deflated_sharpe, pbo
               FROM backtest_runs
               WHERE model_portfolio_id = $1 AND status = 'completed'
               ORDER BY started_at DESC LIMIT 1""",
            model_portfolio_id,
        )
        if not run:
            return {"status": "no_data"}

        results = json.loads(run["results_json"]) if run["results_json"] else {}
        benchmarks = json.loads(run["benchmarks_json"]) if run["benchmarks_json"] else []

        return {
            "model_portfolio_id": model_portfolio_id,
            "sharpe": results.get("sharpe"),
            "deflated_sharpe": run["deflated_sharpe"],
            "pbo": run["pbo"],
            "benchmarks": benchmarks,
        }
