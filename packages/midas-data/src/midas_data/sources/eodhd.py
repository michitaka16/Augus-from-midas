"""
EODHD API adapter for market data ingestion.

Provides EOD bars, fundamentals, corporate actions, delisted tickers, and
exchange symbol listings via the EODHD Historical Data API. All methods return
raw dicts; normalization into Bar/Fundamental/CorpAction models happens in the
data fabric layer.

Constraints:
  - API key required (EODHD_API_KEY env var).
  - Default rate limit: 20 requests/minute (configurable). Exponential backoff
    on HTTP 429.
  - The delisted-tickers endpoint may not exist on all EODHD plans. See M01-15
    for the verification blocker.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import date
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_BASE_URL = "https://eodhd.com/api"


class EODHDClient:
    """Async client for the EODHD Historical Data API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        rate_limit_rpm: int = 20,
        max_retries: int = 5,
        base_backoff: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ["EODHD_API_KEY"]
        self._rate_limit_rpm = rate_limit_rpm
        self._min_interval = 60.0 / rate_limit_rpm
        self._max_retries = max_retries
        self._base_backoff = base_backoff
        self._last_request_time: float = 0.0
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> EODHDClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Rate-limit + retry helpers
    # ------------------------------------------------------------------

    async def _throttle(self) -> None:
        """Enforce minimum interval between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        log_context: dict[str, Any] | None = None,
    ) -> Any:
        """Issue a GET request with rate limiting and exponential backoff on 429."""
        params = dict(params or {})
        params.setdefault("api_token", self._api_key)
        params.setdefault("fmt", "json")

        ctx = log_context or {}

        for attempt in range(1, self._max_retries + 1):
            await self._throttle()
            logger.info("eodhd.request.start", path=path, attempt=attempt, **ctx)
            try:
                resp = await self._client.get(path, params=params)

                if resp.status_code == 429:
                    backoff = self._base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "eodhd.request.rate_limited",
                        path=path,
                        attempt=attempt,
                        backoff_s=backoff,
                        **ctx,
                    )
                    await asyncio.sleep(backoff)
                    continue

                resp.raise_for_status()
                data = resp.json()
                logger.info(
                    "eodhd.request.ok",
                    path=path,
                    status=resp.status_code,
                    **ctx,
                )
                return data

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "eodhd.request.http_error",
                    path=path,
                    status=exc.response.status_code,
                    attempt=attempt,
                    error=str(exc),
                    **ctx,
                )
                if attempt == self._max_retries:
                    raise
                backoff = self._base_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

            except httpx.RequestError as exc:
                logger.error(
                    "eodhd.request.network_error",
                    path=path,
                    attempt=attempt,
                    error=str(exc),
                    **ctx,
                )
                if attempt == self._max_retries:
                    raise
                backoff = self._base_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        # Unreachable in normal flow, but satisfy type checkers.
        msg = f"Exhausted {self._max_retries} retries for {path}"
        raise RuntimeError(msg)

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def fetch_eod_bars(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch end-of-day OHLCV bars for *ticker* between *start* and *end*.

        Returns a list of raw dicts with keys: date, open, high, low, close,
        adjusted_close, volume.
        """
        ctx = {"ticker": ticker, "start": str(start), "end": str(end)}
        logger.info("eodhd.fetch_eod_bars.start", **ctx)
        data = await self._request(
            f"/eod/{ticker}",
            params={"from": str(start), "to": str(end)},
            log_context=ctx,
        )
        result = data if isinstance(data, list) else []
        logger.info("eodhd.fetch_eod_bars.ok", bars=len(result), **ctx)
        return result

    async def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        """Fetch fundamental data (P/E, yield, AUM, etc.) for *ticker*.

        Returns the full raw JSON response from EODHD's fundamentals endpoint.
        """
        ctx = {"ticker": ticker}
        logger.info("eodhd.fetch_fundamentals.start", **ctx)
        data = await self._request(
            f"/fundamentals/{ticker}",
            log_context=ctx,
        )
        result = data if isinstance(data, dict) else {}
        logger.info("eodhd.fetch_fundamentals.ok", **ctx)
        return result

    async def fetch_corp_actions(self, ticker: str) -> list[dict[str, Any]]:
        """Fetch corporate actions (splits, dividends) for *ticker*.

        Returns a list of raw dicts from EODHD's dividends and splits endpoints
        combined.
        """
        ctx = {"ticker": ticker}
        logger.info("eodhd.fetch_corp_actions.start", **ctx)

        dividends = await self._request(
            f"/div/{ticker}",
            log_context={**ctx, "action_type": "dividend"},
        )
        splits = await self._request(
            f"/splits/{ticker}",
            log_context={**ctx, "action_type": "split"},
        )

        div_list = dividends if isinstance(dividends, list) else []
        split_list = splits if isinstance(splits, list) else []

        for item in div_list:
            item["_action_type"] = "dividend"
        for item in split_list:
            item["_action_type"] = "split"

        result = div_list + split_list
        logger.info(
            "eodhd.fetch_corp_actions.ok",
            dividends=len(div_list),
            splits=len(split_list),
            **ctx,
        )
        return result

    async def fetch_delisted_tickers(self) -> list[dict[str, Any]]:
        """Fetch delisted/expired tickers for point-in-time universe construction.

        BLOCKER (M01-15): This endpoint may not exist on all EODHD plans. Verify
        via a test query before relying on it. If unavailable, source from
        Polygon.io or SEC EDGAR XBRL.
        """
        ctx: dict[str, Any] = {"endpoint": "exchange-symbol-list", "filter": "delisted"}
        logger.info("eodhd.fetch_delisted_tickers.start", **ctx)
        data = await self._request(
            "/exchange-symbol-list/US",
            params={"type": "etf", "delisted": "1"},
            log_context=ctx,
        )
        result = data if isinstance(data, list) else []
        logger.info("eodhd.fetch_delisted_tickers.ok", count=len(result), **ctx)
        return result

    async def fetch_exchange_symbols(
        self,
        exchange: str = "US",
    ) -> list[dict[str, Any]]:
        """Fetch all symbols listed on *exchange*.

        Returns a list of raw dicts with ticker, name, exchange, type, etc.
        """
        ctx = {"exchange": exchange}
        logger.info("eodhd.fetch_exchange_symbols.start", **ctx)
        data = await self._request(
            f"/exchange-symbol-list/{exchange}",
            log_context=ctx,
        )
        result = data if isinstance(data, list) else []
        logger.info("eodhd.fetch_exchange_symbols.ok", count=len(result), **ctx)
        return result
