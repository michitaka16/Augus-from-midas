"""
Midas Data Fabric — unified API for all data access.

The fabric is the single entry point for reading and writing market data,
regime signals, news, and ETF universe information. It combines:
- Redis hot cache (cache.py)
- Postgres via asyncpg (primary store)
- pgvector for semantic news search
- Point-in-time ETF universe (pit_universe.py)
- Write-through ingestion (ingest.py)

Usage:
    fabric = DataFabric()
    await fabric.initialize()
    bars = await fabric.get_bars("SPY", date(2024, 1, 1), date(2024, 12, 31))
    await fabric.close()
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import structlog

from midas_data.fabric.cache import DataCache
from midas_data.fabric.ingest import DataIngestor
from midas_data.fabric.pit_universe import PITUniverseManager

logger = structlog.get_logger(__name__)

__all__ = ["DataFabric", "DataCache", "DataIngestor", "PITUniverseManager"]


class DataFabric:
    """Unified data access layer — cache + Postgres + pgvector + PIT universe."""

    def __init__(
        self,
        database_url: str | None = None,
        redis_url: str | None = None,
    ):
        self._database_url = database_url or os.environ.get("DATABASE_URL")
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._conn: Any = None
        self._cache: DataCache | None = None
        self._ingestor: DataIngestor | None = None
        self._pit: PITUniverseManager | None = None

    async def initialize(self) -> None:
        """Initialize connections to Postgres and Redis."""
        try:
            import asyncpg
        except ImportError as exc:
            raise ImportError("asyncpg required. Install with: pip install asyncpg") from exc

        if not self._database_url:
            raise ValueError("DATABASE_URL must be set in .env or passed to constructor")

        self._conn = await asyncpg.connect(self._database_url)
        self._cache = DataCache(self._redis_url)
        self._ingestor = DataIngestor(self._conn, self._cache)
        self._pit = PITUniverseManager(self._conn)

        logger.info("fabric.initialized", database="connected", cache="connected")

    # ── Read API ────────────────────────────────────────────

    async def get_bars(self, ticker: str, start: date, end: date) -> list[dict]:
        """Fetch bars — try cache first, fall through to Postgres."""
        if self._cache:
            cached = await self._cache.get_bars(ticker, start, end)
            if cached:
                return cached

        rows = await self._conn.fetch(
            """SELECT ticker, date, open, high, low, close, adj_close, volume, source
               FROM bars
               WHERE ticker = $1 AND date >= $2 AND date <= $3
               ORDER BY date""",
            ticker, start, end,
        )
        result = [dict(row) for row in rows]
        logger.info("fabric.get_bars", ticker=ticker, count=len(result), mode="postgres")

        # Write-through to cache
        if self._cache and result:
            await self._cache.set_bars(ticker, result, confirmed=True)

        return result

    async def get_regime_signals(self, dt: date) -> dict:
        """Fetch all regime signal values for a date."""
        if self._cache:
            cached = await self._cache.get_regime_signals(dt)
            if cached:
                return cached

        rows = await self._conn.fetch(
            "SELECT signal_name, value FROM regime_signals WHERE date = $1",
            dt,
        )
        result = {row["signal_name"]: row["value"] for row in rows}
        logger.info("fabric.get_regime_signals", date=str(dt), count=len(result), mode="postgres")

        if self._cache and result:
            await self._cache.set_regime_signals(dt, result)

        return result

    async def get_news(self, query: str, k: int = 5) -> list[dict]:
        """Fetch news — try cache, fall through to pgvector semantic search."""
        if self._cache:
            cached = await self._cache.get_news(query)
            if cached:
                return cached[:k]

        # pgvector semantic search requires an embedding of the query
        # For now, fall back to keyword search; embedding integration in M01-07 wire step
        rows = await self._conn.fetch(
            """SELECT id, source, published_at, title, summary, perplexity_citations_json
               FROM news_items
               WHERE title ILIKE $1 OR content ILIKE $1
               ORDER BY published_at DESC
               LIMIT $2""",
            f"%{query}%", k,
        )
        result = [dict(row) for row in rows]
        logger.info("fabric.get_news", query=query[:50], count=len(result), mode="postgres")

        if self._cache and result:
            await self._cache.set_news(query, result)

        return result

    async def get_pit_universe(self, dt: date, sleeve: str | None = None) -> list[dict]:
        """Get point-in-time ETF universe for a date."""
        if not self._pit:
            raise RuntimeError("DataFabric not initialized. Call initialize() first.")
        return await self._pit.get_universe(dt, sleeve)

    async def get_signal(self, signal_id: int) -> dict | None:
        """Fetch a specific signal by ID (for debate agent citations)."""
        row = await self._conn.fetchrow("SELECT * FROM signals WHERE id = $1", signal_id)
        return dict(row) if row else None

    async def get_latest_signal(self, model_portfolio_id: str) -> dict | None:
        """Fetch the most recent published signal for a model portfolio."""
        row = await self._conn.fetchrow(
            """SELECT * FROM signals
               WHERE model_portfolio_id = $1 AND published = TRUE
               ORDER BY timestamp DESC LIMIT 1""",
            model_portfolio_id,
        )
        return dict(row) if row else None

    async def get_backtest_run(self, run_id: int) -> dict | None:
        """Fetch a specific backtest run by ID (for debate agent citations)."""
        row = await self._conn.fetchrow("SELECT * FROM backtest_runs WHERE id = $1", run_id)
        return dict(row) if row else None

    # ── Write API (delegates to ingestor) ───────────────────

    async def ingest_bars(self, ticker: str, bars: list[dict], source: str = "eodhd") -> int:
        if not self._ingestor:
            raise RuntimeError("DataFabric not initialized.")
        return await self._ingestor.ingest_bars(ticker, bars, source)

    async def ingest_regime_signals(self, dt: date, signals: dict[str, float], source: str = "fred") -> int:
        if not self._ingestor:
            raise RuntimeError("DataFabric not initialized.")
        return await self._ingestor.ingest_regime_signals(dt, signals, source)

    async def ingest_news(self, items: list[dict]) -> int:
        if not self._ingestor:
            raise RuntimeError("DataFabric not initialized.")
        return await self._ingestor.ingest_news(items)

    async def ingest_etf_universe(self, tickers: list[dict]) -> int:
        if not self._ingestor:
            raise RuntimeError("DataFabric not initialized.")
        return await self._ingestor.ingest_etf_universe(tickers)

    # ── Lifecycle ───────────────────────────────────────────

    async def close(self) -> None:
        """Clean up all connections."""
        if self._cache:
            await self._cache.close()
        if self._conn:
            await self._conn.close()
        logger.info("fabric.closed")
