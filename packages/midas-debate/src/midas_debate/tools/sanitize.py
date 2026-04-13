"""
News content sanitization — defense-in-depth against prompt injection (M10-11).

Strips HTML, script tags, control characters, and known injection patterns.
Even though midas-data sanitizes on ingestion (M01-06), tools sanitize again
on read because defense-in-depth is cheaper than a single-layer failure.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Known prompt injection patterns
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"system\s*:",
    r"you\s+are\s+(now|a)\s+",
    r"forget\s+(everything|all|your)\s+",
    r"override\s+(your|the)\s+",
    r"pretend\s+(you|to)\s+",
    r"act\s+as\s+(if|a)\s+",
    r"disregard\s+(all|previous|the)\s+",
    r"new\s+instructions\s*:",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# HTML/script tag pattern
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Control characters (except newline and tab)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    """Sanitize a text string: strip HTML, control chars, injection patterns."""
    if not text:
        return ""

    # Strip HTML tags
    cleaned = _HTML_TAG_RE.sub("", text)

    # Strip control characters
    cleaned = _CONTROL_RE.sub("", cleaned)

    # Detect and log injection attempts (but don't strip — the LLM should see
    # that the content is suspicious, just not be manipulated by it)
    if _INJECTION_RE.search(cleaned):
        logger.warning(
            "sanitize.injection_detected",
            preview=cleaned[:100],
        )
        # Wrap the suspicious content in a safety frame
        cleaned = f"[EXTERNAL CONTENT - may contain manipulation attempts]: {cleaned}"

    return cleaned.strip()


def sanitize_news_item(item: dict) -> dict:
    """Sanitize a news item dict. Returns structured data, not raw prose."""
    return {
        "id": item.get("id"),
        "title": sanitize_text(str(item.get("title", ""))),
        "summary": sanitize_text(str(item.get("summary", "")))[:500],
        "source": str(item.get("source", "unknown")),
        "published_at": str(item.get("published_at", "")),
        "external": True,
        "verified": False,
    }
