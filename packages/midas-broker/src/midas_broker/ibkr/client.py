"""
IBKR Client Portal Web API client (M05-01).

HTTP client for Interactive Brokers CP API.
Handles: accounts, positions, orders (preview + place + status), market data.
Rate limits, session timeouts, and re-authentication handled internally.
API version pinned per TH8 resolution.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Pin API version to prevent breaking changes (TH8)
_API_VERSION = "v1"
_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 3


class IBKRClientError(Exception):
    """IBKR API error with status code and message."""
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"IBKR API error {status}: {message}")


class IBKRClient:
    """Client for IBKR Client Portal Web API.

    In production: uses OAuth tokens (access_token in Authorization header).
    In beta: connects to local CP Gateway (IBKR_GATEWAY_URL).
    """

    def __init__(
        self,
        base_url: str | None = None,
        access_token: str | None = None,
    ):
        self._base_url = (
            base_url
            or os.environ.get("IBKR_GATEWAY_URL", "https://localhost:5000")
        ).rstrip("/")
        self._access_token = access_token
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/{_API_VERSION}",
            timeout=_DEFAULT_TIMEOUT,
            verify=False,  # IBKR local Gateway uses self-signed cert
        )

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict | list:
        """Make an API request with retry and error handling."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.debug(
                    "ibkr.request.start",
                    method=method,
                    path=path,
                    attempt=attempt,
                )
                resp = await self._client.request(
                    method, path, headers=self._headers(), **kwargs
                )

                if resp.status_code == 401:
                    logger.warning("ibkr.session_expired", path=path)
                    # Re-authenticate by tickling the session
                    await self._tickle_session()
                    continue

                if resp.status_code == 429:
                    logger.warning("ibkr.rate_limited", path=path, attempt=attempt)
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue

                if resp.status_code >= 400:
                    raise IBKRClientError(resp.status_code, resp.text)

                data = resp.json()
                logger.debug("ibkr.request.ok", path=path, status=resp.status_code)
                return data

            except httpx.ConnectError:
                logger.error("ibkr.connection_failed", url=self._base_url, attempt=attempt)
                if attempt == _MAX_RETRIES:
                    raise

        raise IBKRClientError(0, "Max retries exceeded")

    async def _tickle_session(self) -> None:
        """Keep the IBKR session alive."""
        try:
            await self._client.post("/tickle", headers=self._headers())
        except Exception:
            logger.warning("ibkr.tickle_failed")

    # ── Account ─────────────────────────────────────────────

    async def get_accounts(self) -> list[dict]:
        """GET /portfolio/accounts — list linked accounts."""
        return await self._request("GET", "/portfolio/accounts")

    # ── Positions ───────────────────────────────────────────

    async def get_positions(self, account_id: str) -> list[dict]:
        """GET /portfolio/{account_id}/positions — current positions."""
        data = await self._request("GET", f"/portfolio/{account_id}/positions/0")
        logger.info("ibkr.positions.fetched", account_id=account_id, count=len(data))
        return data

    # ── Orders ──────────────────────────────────────────────

    async def preview_order(self, account_id: str, order: dict) -> dict:
        """POST /iserver/account/{account_id}/orders/whatif — preview order impact."""
        result = await self._request(
            "POST",
            f"/iserver/account/{account_id}/orders/whatif",
            json={"orders": [order]},
        )
        logger.info("ibkr.order.previewed", account_id=account_id)
        return result

    async def place_order(self, account_id: str, order: dict) -> dict:
        """POST /iserver/account/{account_id}/orders — submit order.

        Returns order confirmation. May require reply to confirm message.
        """
        result = await self._request(
            "POST",
            f"/iserver/account/{account_id}/orders",
            json={"orders": [order]},
        )
        logger.info("ibkr.order.placed", account_id=account_id)

        # Handle confirmation messages (IBKR sometimes requires a reply)
        if isinstance(result, list) and result and "id" in result[0]:
            # Confirmation required
            confirm_id = result[0]["id"]
            result = await self._request(
                "POST",
                f"/iserver/reply/{confirm_id}",
                json={"confirmed": True},
            )

        return result

    async def get_order_status(self, order_id: str) -> dict:
        """GET /iserver/account/order/status/{order_id}."""
        return await self._request("GET", f"/iserver/account/order/status/{order_id}")

    # ── Market Data ──────────────────────────────────────��──

    async def get_market_data(self, conids: list[int], fields: list[str]) -> list[dict]:
        """GET /iserver/marketdata/snapshot — real-time quotes."""
        conids_str = ",".join(str(c) for c in conids)
        fields_str = ",".join(fields)
        return await self._request(
            "GET",
            f"/iserver/marketdata/snapshot?conids={conids_str}&fields={fields_str}",
        )

    # ── Lifecycle ───────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()
