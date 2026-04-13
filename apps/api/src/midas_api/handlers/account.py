"""
User account + subscription handlers (M07-03).

Manages portfolio selection, notification preferences, IBKR linking.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AccountHandlers:
    """User account management handlers."""

    def __init__(self, conn: Any):
        self._conn = conn

    async def get_profile(self, user_id: int) -> dict:
        """GET /account — user profile."""
        row = await self._conn.fetchrow(
            "SELECT id, email, mfa_enabled, created_at FROM users.accounts WHERE id = $1",
            user_id,
        )
        if not row:
            return {"error": "User not found", "status": 404}

        prefs = await self._conn.fetchrow(
            "SELECT model_portfolio_id, notification_settings_json, timeout_hours, paper_trading FROM users.preferences WHERE user_id = $1",
            user_id,
        )

        has_ibkr = await self._conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM tokens.user_tokens WHERE user_id = $1)",
            user_id,
        )

        return {
            "id": row["id"],
            "email": row["email"],
            "mfa_enabled": row["mfa_enabled"],
            "created_at": row["created_at"].isoformat(),
            "preferences": {
                "model_portfolio_id": prefs["model_portfolio_id"] if prefs else "growth",
                "notification_settings": json.loads(prefs["notification_settings_json"]) if prefs else {},
                "timeout_hours": prefs["timeout_hours"] if prefs else 24,
                "paper_trading": prefs["paper_trading"] if prefs else True,
            },
            "ibkr_linked": has_ibkr,
            "status": 200,
        }

    async def update_portfolio(self, user_id: int, model_portfolio_id: str) -> dict:
        """PUT /account/portfolio — change model portfolio subscription."""
        valid = await self._conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM model_portfolios WHERE id = $1 AND is_active = TRUE)",
            model_portfolio_id,
        )
        if not valid:
            return {"error": f"Invalid portfolio: {model_portfolio_id}", "status": 400}

        await self._conn.execute(
            "UPDATE users.preferences SET model_portfolio_id = $1 WHERE user_id = $2",
            model_portfolio_id, user_id,
        )

        logger.info("account.portfolio_changed", user_id=user_id, portfolio=model_portfolio_id)
        return {"model_portfolio_id": model_portfolio_id, "status": 200}

    async def update_preferences(self, user_id: int, preferences: dict) -> dict:
        """PUT /account/preferences — update notification settings, timeout."""
        updates = []
        params = [user_id]
        idx = 2

        if "notification_settings" in preferences:
            updates.append(f"notification_settings_json = ${idx}")
            params.append(json.dumps(preferences["notification_settings"]))
            idx += 1

        if "timeout_hours" in preferences:
            timeout = max(12, min(72, int(preferences["timeout_hours"])))
            updates.append(f"timeout_hours = ${idx}")
            params.append(timeout)
            idx += 1

        if "paper_trading" in preferences:
            updates.append(f"paper_trading = ${idx}")
            params.append(bool(preferences["paper_trading"]))
            idx += 1

        if updates:
            sql = f"UPDATE users.preferences SET {', '.join(updates)} WHERE user_id = $1"
            await self._conn.execute(sql, *params)
            logger.info("account.preferences_updated", user_id=user_id)

        return {"status": 200}

    async def link_ibkr(self, user_id: int) -> dict:
        """POST /account/ibkr/link — initiate IBKR OAuth flow."""
        from midas_broker.ibkr.oauth import IBKROAuth

        oauth = IBKROAuth(self._conn)
        import secrets
        state = secrets.token_urlsafe(32)

        url = oauth.get_authorization_url(state)
        logger.info("account.ibkr_link.start", user_id=user_id)
        return {"authorization_url": url, "state": state, "status": 200}

    async def ibkr_callback(self, user_id: int, code: str) -> dict:
        """GET /account/ibkr/callback — complete IBKR OAuth flow."""
        from midas_broker.ibkr.oauth import IBKROAuth

        oauth = IBKROAuth(self._conn)
        result = await oauth.exchange_code(code, user_id)
        logger.info("account.ibkr_linked", user_id=user_id)
        return {"status": 200, **result}

    async def unlink_ibkr(self, user_id: int) -> dict:
        """DELETE /account/ibkr/unlink — revoke IBKR tokens."""
        from midas_broker.ibkr.oauth import IBKROAuth

        oauth = IBKROAuth(self._conn)
        await oauth.revoke(user_id)
        logger.info("account.ibkr_unlinked", user_id=user_id)
        return {"status": 200}
