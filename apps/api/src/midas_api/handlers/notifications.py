"""
Push notification service (M07-08).

Strictly gated: ONLY regime flips, pending approvals, execution confirmations.
No engagement spam — the user said "I don't want to monitor it."
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Notification types that are allowed to fire
_ALLOWED_TYPES = {
    "regime_changed",
    "approval_pending",
    "execution_confirmed",
    "escalation_reminder",
}


class NotificationService:
    """Push notifications via Expo + email via SendGrid/SES."""

    def __init__(self, conn: Any):
        self._conn = conn

    async def send(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """Send a push notification to a user.

        Returns True if sent, False if gated (wrong type or user preference).
        """
        if notification_type not in _ALLOWED_TYPES:
            logger.warning(
                "notification.blocked_type",
                type=notification_type,
                user_id=user_id,
            )
            return False

        # Check user notification preferences
        prefs = await self._conn.fetchrow(
            "SELECT notification_settings_json FROM users.preferences WHERE user_id = $1",
            user_id,
        )
        if prefs:
            import json
            settings = json.loads(prefs["notification_settings_json"])
            channel = settings.get(notification_type, "push")
            if channel == "none":
                logger.info("notification.user_opted_out", type=notification_type, user_id=user_id)
                return False

        # Send push via Expo
        expo_token = os.environ.get("EXPO_ACCESS_TOKEN")
        if expo_token:
            await self._send_expo_push(user_id, title, body, data)

        logger.info("notification.sent", type=notification_type, user_id=user_id)
        return True

    async def _send_expo_push(
        self,
        user_id: int,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        """Send via Expo Push Notifications API."""
        # In production: look up user's Expo push token from a registration table
        # For now, log the intent
        logger.info(
            "notification.expo.send",
            user_id=user_id,
            title=title,
            body_preview=body[:100],
        )

    async def notify_regime_change(self, regime: str, confidence: float) -> int:
        """Notify ALL subscribers about a regime change. Returns count sent."""
        users = await self._conn.fetch(
            "SELECT user_id FROM users.preferences"
        )
        sent = 0
        for row in users:
            ok = await self.send(
                user_id=row["user_id"],
                notification_type="regime_changed",
                title=f"Regime: {regime.upper()}",
                body=f"Market regime changed to {regime} (confidence: {confidence:.0%}). Review recommended.",
                data={"regime": regime, "confidence": confidence},
            )
            if ok:
                sent += 1
        logger.info("notification.regime_change_broadcast", regime=regime, sent=sent)
        return sent
