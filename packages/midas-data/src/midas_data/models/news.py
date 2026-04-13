"""
News models — Perplexity-sourced news with pgvector embeddings.

News citations in the debate agent are marked "external, unverified"
per TH2 resolution — the grounding contract verifies Midas signal/backtest
IDs, not the accuracy of external news sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    """News article cached from Perplexity with semantic embedding.

    The embedding column uses pgvector VECTOR(1536) for semantic search.
    All content is sanitized on ingestion (M01-06) and again on read by
    the debate agent tools (M10-11) to prevent prompt injection.
    """

    id: int = field(default=0, metadata={"primary_key": True})
    source: str = field(default="perplexity", metadata={"max_length": 50})
    published_at: datetime = field(default_factory=datetime.utcnow, metadata={"index": True})
    title: str = field(default="", metadata={"max_length": 500})
    content: str = field(default="")
    summary: str = field(default="")
    perplexity_citations_json: str = field(default="[]")
    query: str = field(default="", metadata={"max_length": 500})
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    # embedding: pgvector VECTOR(1536) — handled via raw SQL extension, not ORM
    # pgvector index created in migration
