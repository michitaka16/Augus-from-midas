"""
FRED (Federal Reserve Economic Data) adapter for regime signal ingestion.

Fetches macro indicators used by the regime detection engine: VIX term
structure, credit spreads, yield curve, and fed funds rate.

Constraints:
  - API key optional for limited use (FRED_API_KEY env var).
  - FRED publishes HY OAS (BAMLH0A0HYM2) with a ~1-day lag. During crisis
    onset, use the IBKR HYG-IEF spread proxy (ibkr_spread.py) for intraday
    estimates. See M01-08 / TH3 resolution.
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

_BASE_URL = "https://api.stlouisfed.org/fred"

# Canonical FRED series IDs for regime detection signals.
SERIES: dict[str, str] = {
    "vix": "VIXCLS",
    "vix3m": "VXVCLS",  # VIX3M
    "vvix": "VVIXCLS",
    "hy_oas": "BAMLH0A0HYM2",       # ICE BofA US HY OAS — ~1-day publication lag
    "ig_oas": "BAMLC0A4CBBB",       # ICE BofA BBB US Corporate OAS
    "yield_3m": "DGS3MO",
    "yield_2y": "DGS2",
    "yield_10y": "DGS10",
    "yield_30y": "DGS30",
    "fed_funds": "FEDFUNDS",
}


class FREDClient:
    """Async client for the FRED JSON API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        max_retries: int = 5,
        base_backoff: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("FRED_API_KEY")
        self._max_retries = max_retries
        self._base_backoff = base_backoff
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> FREDClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        log_context: dict[str, Any] | None = None,
    ) -> Any:
        """GET with exponential backoff on transient errors."""
        params = dict(params or {})
        if self._api_key:
            params["api_key"] = self._api_key
        params.setdefault("file_type", "json")

        ctx = log_context or {}

        for attempt in range(1, self._max_retries + 1):
            logger.info("fred.request.start", path=path, attempt=attempt, **ctx)
            try:
                resp = await self._client.get(path, params=params)

                if resp.status_code == 429:
                    backoff = self._base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "fred.request.rate_limited",
                        path=path,
                        attempt=attempt,
                        backoff_s=backoff,
                        **ctx,
                    )
                    await asyncio.sleep(backoff)
                    continue

                resp.raise_for_status()
                data = resp.json()
                logger.info("fred.request.ok", path=path, status=resp.status_code, **ctx)
                return data

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "fred.request.http_error",
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
                    "fred.request.network_error",
                    path=path,
                    attempt=attempt,
                    error=str(exc),
                    **ctx,
                )
                if attempt == self._max_retries:
                    raise
                backoff = self._base_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        msg = f"Exhausted {self._max_retries} retries for {path}"
        raise RuntimeError(msg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_series(
        self,
        series_id: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch observations for a single FRED series between *start* and *end*.

        Returns a list of ``{"date": "YYYY-MM-DD", "value": "..."}`` dicts.
        FRED returns values as strings; ``"."`` indicates a missing observation.
        """
        ctx = {"series_id": series_id, "start": str(start), "end": str(end)}
        logger.info("fred.fetch_series.start", **ctx)

        data = await self._request(
            "/series/observations",
            params={
                "series_id": series_id,
                "observation_start": str(start),
                "observation_end": str(end),
                "sort_order": "asc",
            },
            log_context=ctx,
        )

        observations: list[dict[str, Any]] = data.get("observations", [])
        logger.info(
            "fred.fetch_series.ok",
            observations=len(observations),
            **ctx,
        )
        return observations

    async def fetch_all_regime_signals(
        self,
        start: date,
        end: date,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch all regime signal series in parallel.

        Returns ``{signal_name: [observations...]}`` for every entry in
        :data:`SERIES`.

        Note: HY OAS (BAMLH0A0HYM2) has a ~1-day publication lag from ICE/BofA.
        During crisis onset, supplement with the IBKR HYG-IEF intraday spread
        proxy (see ibkr_spread.py, M01-08).
        """
        ctx = {"start": str(start), "end": str(end), "series_count": len(SERIES)}
        logger.info("fred.fetch_all_regime_signals.start", **ctx)

        t0 = time.monotonic()

        async def _fetch_one(name: str, sid: str) -> tuple[str, list[dict[str, Any]]]:
            obs = await self.fetch_series(sid, start, end)
            return name, obs

        tasks = [_fetch_one(name, sid) for name, sid in SERIES.items()]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, list[dict[str, Any]]] = {}
        for item in results_raw:
            if isinstance(item, BaseException):
                logger.error(
                    "fred.fetch_all_regime_signals.series_error",
                    error=str(item),
                )
                continue
            name, obs = item
            results[name] = obs

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "fred.fetch_all_regime_signals.ok",
            fetched=len(results),
            total=len(SERIES),
            elapsed_ms=round(elapsed_ms, 1),
            **ctx,
        )
        return results
