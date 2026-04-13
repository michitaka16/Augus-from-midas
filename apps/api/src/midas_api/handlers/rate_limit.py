"""
Rate limiting — Redis-backed per-endpoint limits (M07-14).

/auth/*: 10 req/min per IP (brute force protection)
/debate/message: 20 req/min per user (LLM cost control)
/signals/*: 60 req/min per IP (CDN handles most)
/approvals/*: 30 req/min per user
"""

from __future__ import annotations

import os
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

RATE_LIMITS = {
    "auth": {"limit": 10, "window": 60, "key_type": "ip"},
    "debate": {"limit": 20, "window": 60, "key_type": "user"},
    "signals": {"limit": 60, "window": 60, "key_type": "ip"},
    "approvals": {"limit": 30, "window": 60, "key_type": "user"},
    "default": {"limit": 100, "window": 60, "key_type": "ip"},
}


class RateLimiter:
    """Redis-backed sliding window rate limiter."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._client: Any = None

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(self._redis_url, decode_responses=True)
            except ImportError:
                logger.warning("rate_limit.redis_unavailable")
                return None
        return self._client

    async def check(
        self,
        endpoint_group: str,
        identifier: str,
    ) -> tuple[bool, dict]:
        """Check if a request is allowed.

        Returns (allowed, headers) where headers include rate limit info.
        """
        config = RATE_LIMITS.get(endpoint_group, RATE_LIMITS["default"])
        limit = config["limit"]
        window = config["window"]

        client = await self._get_client()
        if not client:
            return True, {}  # Redis down — allow (fail-open for rate limiting)

        key = f"ratelimit:{endpoint_group}:{identifier}"
        now = time.time()

        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()

            count = results[2]
            allowed = count <= limit

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - count)),
                "X-RateLimit-Reset": str(int(now + window)),
            }

            if not allowed:
                headers["Retry-After"] = str(window)
                logger.warning(
                    "rate_limit.exceeded",
                    group=endpoint_group,
                    identifier=identifier[:20],
                    count=count,
                    limit=limit,
                )

            return allowed, headers

        except Exception:
            logger.warning("rate_limit.redis_error", group=endpoint_group)
            return True, {}  # Fail-open

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
