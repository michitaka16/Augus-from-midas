"""
Approval handlers — pending, approve, reject, hold, history (M07-04).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ApprovalHandlers:
    """Trade approval management handlers."""

    def __init__(self, conn: Any, audit_trail: Any | None = None):
        self._conn = conn
        self._audit = audit_trail

    async def get_pending(self, user_id: int) -> dict:
        """GET /approvals/pending — list pending approvals for this user."""
        rows = await self._conn.fetch(
            """SELECT a.id, a.signal_id, a.status, a.created_at, a.trades_json,
                      s.model_portfolio_id, s.regime, s.allocations_json, s.cost_estimate_json
               FROM users.approvals a
               JOIN signals s ON s.id = a.signal_id
               WHERE a.user_id = $1 AND a.status = 'pending'
               ORDER BY a.created_at DESC""",
            user_id,
        )

        approvals = [{
            "id": r["id"],
            "signal_id": r["signal_id"],
            "model_portfolio_id": r["model_portfolio_id"],
            "regime": r["regime"],
            "allocations": json.loads(r["allocations_json"]),
            "cost_estimate": json.loads(r["cost_estimate_json"]),
            "trades": json.loads(r["trades_json"]),
            "created_at": r["created_at"].isoformat(),
        } for r in rows]

        return {"approvals": approvals, "count": len(approvals), "status": 200}

    async def approve(self, user_id: int, approval_id: int) -> dict:
        """POST /approvals/{id}/approve — approve and execute trades."""
        row = await self._conn.fetchrow(
            "SELECT id, signal_id, status, trades_json FROM users.approvals WHERE id = $1 AND user_id = $2",
            approval_id, user_id,
        )
        if not row:
            return {"error": "Approval not found", "status": 404}
        if row["status"] != "pending":
            return {"error": f"Approval already {row['status']}", "status": 409}

        await self._conn.execute(
            "UPDATE users.approvals SET status = 'approved', decided_at = $1, method = 'manual' WHERE id = $2",
            datetime.utcnow(), approval_id,
        )

        if self._audit:
            await self._audit.append(
                event_type="approval_decided",
                payload={"approval_id": approval_id, "decision": "approved", "user_id": user_id},
                actor=f"user:{user_id}",
            )

        logger.info("approval.approved", user_id=user_id, approval_id=approval_id)
        return {"status": 200, "decision": "approved"}

    async def reject(self, user_id: int, approval_id: int) -> dict:
        """POST /approvals/{id}/reject."""
        await self._conn.execute(
            "UPDATE users.approvals SET status = 'rejected', decided_at = $1, method = 'manual' WHERE id = $2 AND user_id = $3",
            datetime.utcnow(), approval_id, user_id,
        )

        if self._audit:
            await self._audit.append(
                event_type="approval_decided",
                payload={"approval_id": approval_id, "decision": "rejected"},
                actor=f"user:{user_id}",
            )

        logger.info("approval.rejected", user_id=user_id, approval_id=approval_id)
        return {"status": 200, "decision": "rejected"}

    async def hold(self, user_id: int, approval_id: int) -> dict:
        """POST /approvals/{id}/hold — acknowledge but hold (resets escalation)."""
        await self._conn.execute(
            "UPDATE users.approvals SET status = 'held', decided_at = $1, method = 'manual' WHERE id = $2 AND user_id = $3",
            datetime.utcnow(), approval_id, user_id,
        )

        logger.info("approval.held", user_id=user_id, approval_id=approval_id)
        return {"status": 200, "decision": "held"}

    async def get_history(self, user_id: int, limit: int = 50, offset: int = 0) -> dict:
        """GET /approvals/history — past decisions."""
        rows = await self._conn.fetch(
            """SELECT a.id, a.signal_id, a.status, a.decided_at, a.method, a.created_at,
                      s.model_portfolio_id, s.regime
               FROM users.approvals a
               JOIN signals s ON s.id = a.signal_id
               WHERE a.user_id = $1
               ORDER BY a.created_at DESC
               LIMIT $2 OFFSET $3""",
            user_id, limit, offset,
        )

        return {
            "approvals": [{
                "id": r["id"],
                "signal_id": r["signal_id"],
                "model_portfolio_id": r["model_portfolio_id"],
                "regime": r["regime"],
                "status": r["status"],
                "method": r["method"],
                "decided_at": r["decided_at"].isoformat() if r["decided_at"] else None,
                "created_at": r["created_at"].isoformat(),
            } for r in rows],
            "status": 200,
        }
