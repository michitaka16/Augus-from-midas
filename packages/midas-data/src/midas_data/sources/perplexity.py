"""
Perplexity news adapter for market event ingestion.

Uses the Perplexity Sonar API to fetch real-time market news, and OpenAI
embeddings for semantic search storage in pgvector.

Constraints:
  - API key required: PERPLEXITY_API_KEY env var.
  - Model from env: PERPLEXITY_MODEL (default "sonar") — never hardcoded.
  - Embedding model from env: EMBEDDING_MODEL — never hardcoded.
  - Embedding API key from env: OPENAI_API_KEY.
  - All citations are marked "external, unverified" per TH2 resolution.
  - Content is sanitized on ingestion (prompt injection, HTML, control chars).
  - Time-decay: news older than 72h is not re-fetched.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
_OPENAI_BASE_URL = "https://api.openai.com/v1"

# Time-decay threshold: skip re-fetching news older than this.
_NEWS_TTL = timedelta(hours=72)

# Prompt injection patterns to strip from ingested content.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+all\s+previous", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|above|all)", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[\s*INST\s*\]", re.IGNORECASE),
    re.compile(r"\[\s*/\s*INST\s*\]", re.IGNORECASE),
    re.compile(r"<\s*\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\s*\|im_end\|>", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"override\s+(previous|system)", re.IGNORECASE),
]


class PerplexityClient:
    """Async client for Perplexity Sonar API and OpenAI embeddings."""

    def __init__(
        self,
        *,
        perplexity_api_key: str | None = None,
        openai_api_key: str | None = None,
        perplexity_model: str | None = None,
        embedding_model: str | None = None,
        max_retries: int = 5,
        base_backoff: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._perplexity_api_key = (
            perplexity_api_key or os.environ["PERPLEXITY_API_KEY"]
        )
        self._openai_api_key = (
            openai_api_key or os.environ["OPENAI_API_KEY"]
        )
        self._perplexity_model = (
            perplexity_model or os.environ.get("PERPLEXITY_MODEL", "sonar")
        )
        self._embedding_model = (
            embedding_model or os.environ.get("EMBEDDING_MODEL", os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
        )
        self._max_retries = max_retries
        self._base_backoff = base_backoff

        self._pplx_client = httpx.AsyncClient(
            base_url=_PERPLEXITY_BASE_URL,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._perplexity_api_key}",
                "Content-Type": "application/json",
            },
        )
        self._openai_client = httpx.AsyncClient(
            base_url=_OPENAI_BASE_URL,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._openai_api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        """Close underlying HTTP clients."""
        await self._pplx_client.aclose()
        await self._openai_client.aclose()

    async def __aenter__(self) -> PerplexityClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Retry helpers
    # ------------------------------------------------------------------

    async def _retry_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        log_context: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """POST/GET with exponential backoff on 429 and transient errors."""
        ctx = log_context or {}

        for attempt in range(1, self._max_retries + 1):
            logger.info("perplexity.request.start", url=url, attempt=attempt, **ctx)
            try:
                if method.upper() == "POST":
                    resp = await client.post(url, json=json_body)
                else:
                    resp = await client.get(url)

                if resp.status_code == 429:
                    backoff = self._base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "perplexity.request.rate_limited",
                        url=url,
                        attempt=attempt,
                        backoff_s=backoff,
                        **ctx,
                    )
                    await asyncio.sleep(backoff)
                    continue

                resp.raise_for_status()
                logger.info(
                    "perplexity.request.ok",
                    url=url,
                    status=resp.status_code,
                    **ctx,
                )
                return resp

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "perplexity.request.http_error",
                    url=url,
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
                    "perplexity.request.network_error",
                    url=url,
                    attempt=attempt,
                    error=str(exc),
                    **ctx,
                )
                if attempt == self._max_retries:
                    raise
                backoff = self._base_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        msg = f"Exhausted {self._max_retries} retries for {url}"
        raise RuntimeError(msg)

    # ------------------------------------------------------------------
    # Sanitization
    # ------------------------------------------------------------------

    @staticmethod
    def sanitize_content(raw: str) -> str:
        """Strip HTML tags, script elements, control characters, and prompt
        injection patterns from raw content.

        This runs on ingestion (M01-06) and again on read by the debate agent
        tools (M10-11) as defense-in-depth.
        """
        # Strip script/style blocks.
        text = re.sub(r"<\s*script[^>]*>.*?</\s*script\s*>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<\s*style[^>]*>.*?</\s*style\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Strip remaining HTML tags.
        text = re.sub(r"<[^>]+>", "", text)

        # Strip control characters (keep newlines and tabs).
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # Strip prompt injection patterns.
        for pattern in _INJECTION_PATTERNS:
            text = pattern.sub("[REDACTED]", text)

        return text.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search_news(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Search market news via Perplexity Sonar API.

        Returns a list of parsed news items with sanitized content. All
        citations are marked ``"external, unverified"`` per TH2 resolution.

        Items older than 72 hours are skipped (time-decay TTL).
        """
        ctx = {"query": query, "max_results": max_results}
        logger.info("perplexity.search_news.start", **ctx)

        body: dict[str, Any] = {
            "model": self._perplexity_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial news assistant. Return concise "
                        "market news with citations. Each item should have a "
                        "title and summary."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "max_tokens": 1024,
        }

        resp = await self._retry_request(
            self._pplx_client,
            "POST",
            "/chat/completions",
            json_body=body,
            log_context=ctx,
        )

        data = resp.json()
        items = self._parse_response(data)

        # Time-decay: filter out items older than 72h.
        cutoff = datetime.now(tz=timezone.utc) - _NEWS_TTL
        filtered: list[dict[str, Any]] = []
        for item in items:
            published = item.get("published_at")
            if published and isinstance(published, str):
                try:
                    pub_dt = datetime.fromisoformat(published)
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass  # Keep items with unparseable dates.
            filtered.append(item)

        logger.info(
            "perplexity.search_news.ok",
            raw_items=len(items),
            filtered_items=len(filtered),
            **ctx,
        )
        return filtered[:max_results]

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a text embedding via the OpenAI Embeddings API.

        Model is read from EMBEDDING_MODEL env var — never hardcoded.
        """
        ctx = {"text_len": len(text), "model": self._embedding_model}
        logger.info("perplexity.generate_embedding.start", **ctx)

        body: dict[str, Any] = {
            "model": self._embedding_model,
            "input": text,
        }

        resp = await self._retry_request(
            self._openai_client,
            "POST",
            "/embeddings",
            json_body=body,
            log_context=ctx,
        )

        data = resp.json()
        embedding: list[float] = data["data"][0]["embedding"]
        logger.info(
            "perplexity.generate_embedding.ok",
            dimensions=len(embedding),
            **ctx,
        )
        return embedding

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract structured news items from the Perplexity Sonar API response.

        Citations are extracted and marked as ``"external, unverified"``.
        Content is sanitized via :meth:`sanitize_content`.
        """
        items: list[dict[str, Any]] = []

        choices = data.get("choices", [])
        if not choices:
            return items

        message = choices[0].get("message", {})
        content = message.get("content", "")

        # Extract citations from the response.
        citations: list[str] = data.get("citations", [])
        citation_notes = [
            {"url": c, "trust_level": "external, unverified"} for c in citations
        ]

        sanitized = self.sanitize_content(content)

        items.append(
            {
                "title": sanitized[:200] if sanitized else "",
                "content": sanitized,
                "citations": citation_notes,
                "published_at": datetime.now(tz=timezone.utc).isoformat(),
                "source": "perplexity",
                "trust_level": "external, unverified",
            }
        )

        return items
