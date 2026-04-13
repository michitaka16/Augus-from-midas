"""
Redis cache layer for Midas data fabric.

TTL contract:
- EOD bars: never invalidate after market close confirmed
- Screen-active intraday: 60 seconds
- News: time-decay (fresh=1h, >24h=6h, >72h=skip refetch)

Stampede protection: probabilistic early expiry.
Redis-down fallback: return None, caller falls through to Postgres.
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DataCache:
    """Redis-backed cache with TTL contracts and stampede protection."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._client: Any = None

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
            except ImportError as exc:
                raise ImportError(
                    "redis[asyncio] is required for caching. "
                    "Install with: pip install redis"
                ) from exc
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def _jitter_ttl(self, ttl: int) -> int:
        """Stampede protection: subtract random 0-10% from TTL."""
        if ttl <= 0:
            return ttl
        jitter = random.randint(0, max(1, ttl // 10))
        return max(1, ttl - jitter)

    # ── Bars ────────────────────────────────────────────────

    async def get_bars(self, ticker: str, start: date, end: date) -> list[dict] | None:
        try:
            client = await self._get_client()
            key = f"bars:{ticker}:{start}:{end}"
            data = await client.get(key)
            if data:
                logger.debug("cache.bars.hit", ticker=ticker, mode="cache")
                return json.loads(data)
            logger.debug("cache.bars.miss", ticker=ticker, mode="cache")
            return None
        except Exception:
            logger.warning("cache.bars.error", ticker=ticker, mode="fallback")
            return None

    async def set_bars(self, ticker: str, bars: list[dict], confirmed: bool = True) -> None:
        try:
            client = await self._get_client()
            if not bars:
                return
            start = bars[0].get("date", "")
            end = bars[-1].get("date", "")
            key = f"bars:{ticker}:{start}:{end}"
            serialized = json.dumps(bars, default=str)
            if confirmed:
                # EOD confirmed bars never expire
                await client.set(key, serialized)
            else:
                # Intraday: 60s TTL
                await client.set(key, serialized, ex=self._jitter_ttl(60))
        except Exception:
            logger.warning("cache.bars.set_error", ticker=ticker, mode="fallback")

    # ── Regime Signals ──────────────────────────────────────

    async def get_regime_signals(self, dt: date) -> dict | None:
        try:
            client = await self._get_client()
            key = f"regime:{dt}"
            data = await client.get(key)
            if data:
                logger.debug("cache.regime.hit", date=str(dt), mode="cache")
                return json.loads(data)
            logger.debug("cache.regime.miss", date=str(dt), mode="cache")
            return None
        except Exception:
            logger.warning("cache.regime.error", mode="fallback")
            return None

    async def set_regime_signals(self, dt: date, signals: dict) -> None:
        try:
            client = await self._get_client()
            key = f"regime:{dt}"
            # Regime signals for past dates never change
            await client.set(key, json.dumps(signals, default=str))
        except Exception:
            logger.warning("cache.regime.set_error", mode="fallback")

    # ── News ────────────────────────────────────────────────

    async def get_news(self, query: str) -> list[dict] | None:
        try:
            client = await self._get_client()
            key = f"news:{query}"
            data = await client.get(key)
            if data:
                logger.debug("cache.news.hit", query=query[:50], mode="cache")
                return json.loads(data)
            logger.debug("cache.news.miss", query=query[:50], mode="cache")
            return None
        except Exception:
            logger.warning("cache.news.error", mode="fallback")
            return None

    async def set_news(self, query: str, items: list[dict], ttl_seconds: int | None = None) -> None:
        try:
            client = await self._get_client()
            key = f"news:{query}"
            if ttl_seconds is None:
                ttl_seconds = self._compute_news_ttl(items)
            serialized = json.dumps(items, default=str)
            await client.set(key, serialized, ex=self._jitter_ttl(ttl_seconds))
        except Exception:
            logger.warning("cache.news.set_error", mode="fallback")

    def _compute_news_ttl(self, items: list[dict]) -> int:
        """Time-decay TTL based on freshest item's publication age."""
        if not items:
            return 3600
        now = datetime.utcnow()
        freshest = None
        for item in items:
            pub = item.get("published_at")
            if isinstance(pub, str):
                try:
                    pub = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
                except (ValueError, TypeError):
                    continue
            if isinstance(pub, datetime) and (freshest is None or pub > freshest):
                freshest = pub
        if freshest is None:
            return 3600
        age = now - freshest
        if age < timedelta(hours=24):
            return 3600      # Fresh: 1 hour
        elif age < timedelta(hours=72):
            return 21600     # Aging: 6 hours
        else:
            return 86400     # Old: 24 hours (effectively skip refetch)

    # ── Invalidation ────────────────────────────────────────

    async def invalidate(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count deleted."""
        try:
            client = await self._get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await client.delete(*keys)
                logger.info("cache.invalidate", pattern=pattern, count=len(keys))
            return len(keys)
        except Exception:
            logger.warning("cache.invalidate.error", pattern=pattern, mode="fallback")
            return 0

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
