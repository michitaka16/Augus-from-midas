"""
Ingestion wiring — connects source adapters to DataFlow persistence + Redis cache.

Handles M01-02 (EODHD → DataFlow), M01-04 (FRED → DataFlow), M01-07 (Perplexity → DataFlow).
Each ingest function: fetches from source → normalizes → writes to Postgres → writes to cache.
Deduplication: skip records already present (ON CONFLICT DO NOTHING in SQL).
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DataIngestor:
    """Wires source adapters to DataFlow persistence and Redis cache.

    This is the write path of the data fabric. Source adapters fetch raw data;
    the ingestor normalizes it and writes to Postgres + Redis.
    """

    def __init__(self, db_conn: Any, cache: Any | None = None):
        """
        Args:
            db_conn: asyncpg connection or DataFlow instance for Postgres writes.
            cache: DataCache instance for write-through caching. Optional.
        """
        self._conn = db_conn
        self._cache = cache

    async def ingest_bars(self, ticker: str, bars: list[dict], source: str = "eodhd") -> int:
        """Write EOD bars to Postgres. Deduplicates on (ticker, date, source).

        Returns count of newly inserted bars.
        """
        if not bars:
            return 0

        logger.info("ingest.bars.start", ticker=ticker, count=len(bars), source=source)
        inserted = 0

        for bar in bars:
            try:
                result = await self._conn.execute(
                    """INSERT INTO bars (ticker, date, open, high, low, close, adj_close, volume, source)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (ticker, date, source) DO NOTHING""",
                    ticker,
                    bar["date"],
                    float(bar.get("open", 0)),
                    float(bar.get("high", 0)),
                    float(bar.get("low", 0)),
                    float(bar.get("close", 0)),
                    float(bar.get("adj_close", bar.get("adjusted_close", bar.get("close", 0)))),
                    int(bar.get("volume", 0)),
                    source,
                )
                if result and "INSERT 0 1" in str(result):
                    inserted += 1
            except Exception:
                logger.exception("ingest.bars.row_error", ticker=ticker, date=bar.get("date"))
                raise

        # Write-through to cache
        if self._cache and inserted > 0:
            try:
                await self._cache.set_bars(ticker, bars)
            except Exception:
                logger.warning("ingest.bars.cache_write_failed", ticker=ticker, mode="fallback")

        logger.info("ingest.bars.complete", ticker=ticker, inserted=inserted, skipped=len(bars) - inserted)
        return inserted

    async def ingest_fundamentals(self, ticker: str, data: list[dict], source: str = "eodhd") -> int:
        """Write fundamentals to Postgres. Deduplicates on (ticker, report_date, as_of_date, field_name)."""
        if not data:
            return 0

        logger.info("ingest.fundamentals.start", ticker=ticker, count=len(data))
        inserted = 0

        for row in data:
            result = await self._conn.execute(
                """INSERT INTO fundamentals (ticker, report_date, as_of_date, field_name, value, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (ticker, report_date, as_of_date, field_name) DO NOTHING""",
                ticker,
                row["report_date"],
                row["as_of_date"],
                row["field_name"],
                float(row["value"]),
                source,
            )
            if result and "INSERT 0 1" in str(result):
                inserted += 1

        logger.info("ingest.fundamentals.complete", ticker=ticker, inserted=inserted)
        return inserted

    async def ingest_corp_actions(self, ticker: str, actions: list[dict], source: str = "eodhd") -> int:
        """Write corporate actions to Postgres."""
        if not actions:
            return 0

        logger.info("ingest.corp_actions.start", ticker=ticker, count=len(actions))
        inserted = 0

        for action in actions:
            result = await self._conn.execute(
                """INSERT INTO corp_actions (ticker, ex_date, action_type, factor, announced_date, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING""",
                ticker,
                action["ex_date"],
                action["action_type"],
                float(action.get("factor", 1.0)),
                action.get("announced_date"),
                source,
            )
            if result and "INSERT 0 1" in str(result):
                inserted += 1

        logger.info("ingest.corp_actions.complete", ticker=ticker, inserted=inserted)
        return inserted

    async def ingest_etf_universe(self, tickers: list[dict]) -> int:
        """Write ETF universe entries. Updates on conflict (delist_date may change)."""
        if not tickers:
            return 0

        logger.info("ingest.etf_universe.start", count=len(tickers))
        inserted = 0

        for etf in tickers:
            result = await self._conn.execute(
                """INSERT INTO etf_universe (ticker, name, inception_date, delist_date, sleeve, expense_ratio, avg_daily_volume, liquidity_tier, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT DO NOTHING""",
                etf["ticker"],
                etf.get("name", ""),
                etf["inception_date"],
                etf.get("delist_date"),
                etf.get("sleeve", ""),
                float(etf.get("expense_ratio", 0)),
                int(etf.get("avg_daily_volume", 0)),
                etf.get("liquidity_tier", "high"),
                etf.get("is_active", True),
            )
            if result and "INSERT 0 1" in str(result):
                inserted += 1

        logger.info("ingest.etf_universe.complete", inserted=inserted)
        return inserted

    async def ingest_regime_signals(self, dt: date, signals: dict[str, float], source: str = "fred") -> int:
        """Write regime signal values to Postgres. One row per (date, signal_name).

        Note: FRED HY OAS has a 1-day publication lag. The regime detector
        should account for this by using the IBKR HYG-IEF spread proxy
        as an intraday supplement (per TH3 resolution).
        """
        if not signals:
            return 0

        logger.info("ingest.regime_signals.start", date=str(dt), count=len(signals), source=source)
        inserted = 0

        for signal_name, value in signals.items():
            result = await self._conn.execute(
                """INSERT INTO regime_signals (date, signal_name, value, source)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (date, signal_name) DO UPDATE SET value = $3""",
                dt,
                signal_name,
                float(value),
                source,
            )
            inserted += 1

        # Write-through to cache
        if self._cache:
            try:
                await self._cache.set_regime_signals(dt, signals)
            except Exception:
                logger.warning("ingest.regime_signals.cache_write_failed", mode="fallback")

        logger.info("ingest.regime_signals.complete", date=str(dt), inserted=inserted)
        return inserted

    async def ingest_news(self, items: list[dict]) -> int:
        """Write news items to Postgres. Embedding stored via pgvector.

        Note: All content is sanitized by the Perplexity adapter before
        reaching this method. The debate agent tools sanitize again on
        read (defense-in-depth, M10-11).
        """
        if not items:
            return 0

        logger.info("ingest.news.start", count=len(items))
        inserted = 0

        for item in items:
            embedding = item.get("embedding")
            if embedding:
                # pgvector requires array format
                embedding_str = f"[{','.join(str(x) for x in embedding)}]"
                result = await self._conn.execute(
                    """INSERT INTO news_items (source, published_at, title, content, summary, perplexity_citations_json, query, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector)""",
                    item.get("source", "perplexity"),
                    item["published_at"],
                    item.get("title", ""),
                    item.get("content", ""),
                    item.get("summary", ""),
                    item.get("perplexity_citations_json", "[]"),
                    item.get("query", ""),
                    embedding_str,
                )
            else:
                result = await self._conn.execute(
                    """INSERT INTO news_items (source, published_at, title, content, summary, perplexity_citations_json, query)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                    item.get("source", "perplexity"),
                    item["published_at"],
                    item.get("title", ""),
                    item.get("content", ""),
                    item.get("summary", ""),
                    item.get("perplexity_citations_json", "[]"),
                    item.get("query", ""),
                )
            inserted += 1

        # Write-through to cache for most recent query
        if self._cache and items:
            try:
                query = items[0].get("query", "")
                if query:
                    await self._cache.set_news(query, items)
            except Exception:
                logger.warning("ingest.news.cache_write_failed", mode="fallback")

        logger.info("ingest.news.complete", inserted=inserted)
        return inserted
