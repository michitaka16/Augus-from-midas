"""
Dumb data tools for the debate agent (M10-03).

Each tool is a PURE DATA ENDPOINT. Fetch, return, no decisions.
The LLM decides which tools to call. Tools contain ZERO decision logic.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DebateTools:
    """Collection of dumb data endpoints for the debate agent.

    Each method fetches data and returns it. No conditionals on input content.
    No routing. No classification. Pure data operations.
    """

    def __init__(self, data_fabric: Any):
        self._fabric = data_fabric

    async def fetch_signal(self, signal_id: int) -> dict | None:
        """Fetch a published signal by ID."""
        logger.info("tool.fetch_signal", signal_id=signal_id)
        return await self._fabric.get_signal(signal_id)

    async def fetch_current_recommendation(self, portfolio_id: str) -> dict | None:
        """Fetch the latest published signal for a portfolio."""
        logger.info("tool.fetch_recommendation", portfolio_id=portfolio_id)
        return await self._fabric.get_latest_signal(portfolio_id)

    async def fetch_backtest_run(self, run_id: int) -> dict | None:
        """Fetch a specific backtest run by ID."""
        logger.info("tool.fetch_backtest", run_id=run_id)
        return await self._fabric.get_backtest_run(run_id)

    async def fetch_cost_model(self, ticker: str, shares: int, direction: str) -> dict:
        """Compute transaction cost for a trade."""
        from midas_strategy.cost import calculate_trade_cost

        logger.info("tool.fetch_cost", ticker=ticker, shares=shares, direction=direction)
        cost = calculate_trade_cost(ticker, shares, direction, price=100.0)
        return {
            "ticker": cost.ticker,
            "shares": cost.shares,
            "direction": cost.direction,
            "commission": cost.commission,
            "slippage": cost.slippage,
            "market_impact": cost.market_impact,
            "total": cost.total,
        }

    async def fetch_regime_state(self) -> dict:
        """Fetch current regime + all signal values."""
        from datetime import date

        logger.info("tool.fetch_regime")
        today = date.today()
        signals = await self._fabric.get_regime_signals(today)
        return {"date": str(today), "signals": signals}

    async def fetch_news_by_id(self, news_id: int) -> dict | None:
        """Fetch a cached news item by ID."""
        from midas_debate.tools.sanitize import sanitize_news_item

        logger.info("tool.fetch_news", news_id=news_id)
        row = await self._fabric._conn.fetchrow(
            "SELECT id, title, summary, source, published_at FROM news_items WHERE id = $1",
            news_id,
        )
        if not row:
            return None
        item = dict(row)
        return sanitize_news_item(item)

    async def search_news(self, query: str, k: int = 5) -> list[dict]:
        """Semantic search over cached news."""
        from midas_debate.tools.sanitize import sanitize_news_item

        logger.info("tool.search_news", query=query[:50], k=k)
        items = await self._fabric.get_news(query, k=k)
        return [sanitize_news_item(item) for item in items]

    async def fetch_regime_history(self, limit: int = 20) -> list[dict]:
        """Fetch past regime transitions."""
        logger.info("tool.fetch_regime_history", limit=limit)
        rows = await self._fabric._conn.fetch(
            """SELECT date, ensemble_score, regime
               FROM regime_signals
               WHERE regime IS NOT NULL
               ORDER BY date DESC LIMIT $1""",
            limit,
        )
        return [{"date": str(r["date"]), "regime": r["regime"], "score": r["ensemble_score"]} for r in rows]

    def as_dict(self) -> dict[str, Any]:
        """Return tools as a name→callable dict for the agent."""
        return {
            "fetch_signal": self.fetch_signal,
            "fetch_current_recommendation": self.fetch_current_recommendation,
            "fetch_backtest_run": self.fetch_backtest_run,
            "fetch_cost_model": self.fetch_cost_model,
            "fetch_regime_state": self.fetch_regime_state,
            "fetch_news_by_id": self.fetch_news_by_id,
            "search_news": self.search_news,
            "fetch_regime_history": self.fetch_regime_history,
        }
