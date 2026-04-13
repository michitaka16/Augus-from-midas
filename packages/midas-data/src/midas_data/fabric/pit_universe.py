"""
Point-in-time ETF universe manager.

For any historical date, returns the set of ETFs that existed and were tradeable.
Critical for survivorship-free backtests — using the current universe to backtest
inflates results because delisted losers are excluded.

Uses the etf_universe table: WHERE inception_date <= dt AND (delist_date IS NULL OR delist_date > dt).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class PITUniverseManager:
    """Point-in-time ETF universe lookups."""

    def __init__(self, conn: Any):
        """
        Args:
            conn: asyncpg connection for Postgres queries.
        """
        self._conn = conn

    async def get_universe(self, dt: date, sleeve: str | None = None) -> list[dict]:
        """Return ETFs that were tradeable on the given date.

        Args:
            dt: The historical date to query.
            sleeve: Optional sleeve filter (e.g., 'equity_sector', 'precious_metals').

        Returns:
            List of ETF dicts with ticker, name, sleeve, expense_ratio, etc.
        """
        if sleeve:
            rows = await self._conn.fetch(
                """SELECT ticker, name, inception_date, delist_date, sleeve,
                          expense_ratio, avg_daily_volume, liquidity_tier, is_active
                   FROM etf_universe
                   WHERE inception_date <= $1
                     AND (delist_date IS NULL OR delist_date > $1)
                     AND sleeve = $2
                   ORDER BY ticker""",
                dt, sleeve,
            )
        else:
            rows = await self._conn.fetch(
                """SELECT ticker, name, inception_date, delist_date, sleeve,
                          expense_ratio, avg_daily_volume, liquidity_tier, is_active
                   FROM etf_universe
                   WHERE inception_date <= $1
                     AND (delist_date IS NULL OR delist_date > $1)
                   ORDER BY ticker""",
                dt,
            )

        result = [dict(row) for row in rows]
        logger.debug(
            "pit_universe.query",
            date=str(dt),
            sleeve=sleeve,
            count=len(result),
        )
        return result

    async def get_all_sleeves(self) -> list[str]:
        """Return all distinct sleeve values in the universe."""
        rows = await self._conn.fetch(
            "SELECT DISTINCT sleeve FROM etf_universe ORDER BY sleeve"
        )
        return [row["sleeve"] for row in rows]

    async def validate_backtest_universe(self, tickers: list[str], dt: date) -> list[str]:
        """Return tickers that were NOT in the PIT universe on the given date.

        These represent survivorship bias violations — the backtest is using
        tickers that didn't exist yet or had already been delisted.
        """
        if not tickers:
            return []

        universe = await self.get_universe(dt)
        valid_tickers = {etf["ticker"] for etf in universe}
        violations = [t for t in tickers if t not in valid_tickers]

        if violations:
            logger.warning(
                "pit_universe.survivorship_violations",
                date=str(dt),
                violations=violations,
                count=len(violations),
            )
        return violations
