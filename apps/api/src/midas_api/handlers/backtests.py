"""Backtest API handlers — for debate agent citations and explorer (M07-05)."""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class BacktestHandlers:
    def __init__(self, conn: Any):
        self._conn = conn

    async def get_latest(self, model_portfolio_id: str) -> dict | None:
        """GET /backtests/{portfolio_id}/latest."""
        row = await self._conn.fetchrow(
            """SELECT id, model_portfolio_id, started_at, results_json,
                      horizons_json, regime_stats_json, benchmarks_json,
                      deflated_sharpe, pbo, worst_12m_return, status
               FROM backtest_runs
               WHERE model_portfolio_id = $1 AND status = 'completed'
               ORDER BY started_at DESC LIMIT 1""",
            model_portfolio_id,
        )
        if not row:
            return None
        return _format_run(row)

    async def get_run(self, run_id: int) -> dict | None:
        """GET /backtests/{run_id} — specific run for citation links."""
        row = await self._conn.fetchrow(
            "SELECT * FROM backtest_runs WHERE id = $1", run_id
        )
        if not row:
            return None
        return _format_run(row)

    async def get_history(self, model_portfolio_id: str, limit: int = 20) -> dict:
        """GET /backtests/{portfolio_id}/history."""
        rows = await self._conn.fetch(
            """SELECT id, started_at, deflated_sharpe, pbo, status
               FROM backtest_runs
               WHERE model_portfolio_id = $1
               ORDER BY started_at DESC LIMIT $2""",
            model_portfolio_id, limit,
        )
        return {
            "model_portfolio_id": model_portfolio_id,
            "runs": [{
                "id": r["id"],
                "started_at": r["started_at"].isoformat(),
                "deflated_sharpe": r["deflated_sharpe"],
                "pbo": r["pbo"],
                "status": r["status"],
            } for r in rows],
        }


def _format_run(row: Any) -> dict:
    return {
        "id": row["id"],
        "model_portfolio_id": row["model_portfolio_id"],
        "started_at": row["started_at"].isoformat(),
        "results": json.loads(row["results_json"]) if row["results_json"] else {},
        "horizons": json.loads(row["horizons_json"]) if row["horizons_json"] else [],
        "regime_stats": json.loads(row["regime_stats_json"]) if row["regime_stats_json"] else [],
        "benchmarks": json.loads(row["benchmarks_json"]) if row["benchmarks_json"] else [],
        "deflated_sharpe": row["deflated_sharpe"],
        "pbo": row["pbo"],
        "worst_12m_return": row["worst_12m_return"],
        "status": row["status"],
    }
