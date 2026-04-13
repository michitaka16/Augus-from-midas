"""Nexus API gateway — mounts all handlers."""
from __future__ import annotations
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

class MidasAPI:
    def __init__(self, conn: Any, audit_trail: Any = None):
        from midas_api.handlers.signals import SignalHandlers
        from midas_api.handlers.auth import AuthHandlers
        from midas_api.handlers.account import AccountHandlers
        from midas_api.handlers.approvals import ApprovalHandlers
        from midas_api.handlers.backtests import BacktestHandlers
        from midas_api.handlers.debate import DebateHandlers
        from midas_api.handlers.regime import RegimeHandlers
        from midas_api.handlers.notifications import NotificationService
        from midas_api.handlers.rate_limit import RateLimiter
        self.signals = SignalHandlers(conn)
        self.auth = AuthHandlers(conn)
        self.account = AccountHandlers(conn)
        self.approvals = ApprovalHandlers(conn, audit_trail)
        self.backtests = BacktestHandlers(conn)
        self.debate = DebateHandlers(conn)
        self.regime = RegimeHandlers(conn)
        self.notifications = NotificationService(conn)
        self.rate_limiter = RateLimiter()
        logger.info("api.initialized", handlers=8)

    ROUTES = {
        "GET /signals/latest": "signals.get_latest_all",
        "POST /auth/signup": "auth.signup",
        "POST /auth/login": "auth.login",
        "GET /account": "account.get_profile",
        "GET /approvals/pending": "approvals.get_pending",
        "POST /approvals/{id}/approve": "approvals.approve",
        "GET /backtests/{id}/latest": "backtests.get_latest",
        "POST /debate/message": "debate.send_message",
        "GET /regime/current": "regime.get_current",
    }

    async def close(self):
        await self.rate_limiter.close()
