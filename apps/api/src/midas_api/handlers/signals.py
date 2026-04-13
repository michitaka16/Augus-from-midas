"""
Signal broadcast handlers — impersonal, CDN-cacheable (M04-02).

CRITICAL: NO user_id in request or response. NO authentication required
for signal reads. This is the publisher exemption (ADR-001).

The `/signals/latest` endpoint being CDN-cacheable is the legal tell —
if it can be cached by a CDN without per-user variation, it's impersonal.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SignalHandlers:
    """HTTP handlers for signal broadcast. Registered with Nexus."""

    def __init__(self, conn: Any):
        self._conn = conn

    async def get_latest_all(self) -> dict:
        """GET /signals/latest — most recent signal for each portfolio.

        Headers: Cache-Control: public, max-age=3600
        No authentication required. No user_id in response.
        """
        rows = await self._conn.fetch("""
            SELECT DISTINCT ON (model_portfolio_id)
                id, model_portfolio_id, timestamp, regime,
                allocations_json, reasoning_json, cost_estimate_json,
                ensemble_score
            FROM signals
            WHERE published = TRUE
            ORDER BY model_portfolio_id, timestamp DESC
        """)

        signals = []
        for row in rows:
            signals.append({
                "id": row["id"],
                "model_portfolio_id": row["model_portfolio_id"],
                "timestamp": row["timestamp"].isoformat(),
                "regime": row["regime"],
                "allocations": json.loads(row["allocations_json"]),
                "reasoning": json.loads(row["reasoning_json"]),
                "cost_estimate": json.loads(row["cost_estimate_json"]),
                "ensemble_score": row["ensemble_score"],
            })

        logger.info("signals.get_latest_all", count=len(signals))
        return {
            "signals": signals,
            "_cache": {"Cache-Control": "public, max-age=3600"},
        }

    async def get_latest_portfolio(self, model_portfolio_id: str) -> dict | None:
        """GET /signals/{portfolio_id}/latest — single portfolio latest signal."""
        row = await self._conn.fetchrow("""
            SELECT id, model_portfolio_id, timestamp, regime,
                   allocations_json, reasoning_json, cost_estimate_json,
                   ensemble_score
            FROM signals
            WHERE model_portfolio_id = $1 AND published = TRUE
            ORDER BY timestamp DESC LIMIT 1
        """, model_portfolio_id)

        if not row:
            return None

        return {
            "id": row["id"],
            "model_portfolio_id": row["model_portfolio_id"],
            "timestamp": row["timestamp"].isoformat(),
            "regime": row["regime"],
            "allocations": json.loads(row["allocations_json"]),
            "reasoning": json.loads(row["reasoning_json"]),
            "cost_estimate": json.loads(row["cost_estimate_json"]),
            "ensemble_score": row["ensemble_score"],
            "_cache": {"Cache-Control": "public, max-age=3600"},
        }

    async def get_history(self, model_portfolio_id: str, limit: int = 52, offset: int = 0) -> dict:
        """GET /signals/{portfolio_id}/history — paginated signal history."""
        rows = await self._conn.fetch("""
            SELECT id, timestamp, regime, ensemble_score,
                   cost_estimate_json
            FROM signals
            WHERE model_portfolio_id = $1 AND published = TRUE
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
        """, model_portfolio_id, limit, offset)

        entries = [{
            "id": row["id"],
            "timestamp": row["timestamp"].isoformat(),
            "regime": row["regime"],
            "ensemble_score": row["ensemble_score"],
            "total_cost": json.loads(row["cost_estimate_json"]).get("total", 0),
        } for row in rows]

        total = await self._conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE model_portfolio_id = $1 AND published = TRUE",
            model_portfolio_id,
        )

        return {
            "model_portfolio_id": model_portfolio_id,
            "entries": entries,
            "total": total,
            "limit": limit,
            "offset": offset,
            "_cache": {"Cache-Control": "public, max-age=3600"},
        }
