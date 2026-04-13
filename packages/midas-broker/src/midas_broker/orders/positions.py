"""
Position sync — read-only fetch of current IBKR positions (M05-04).

This data NEVER leaves the client in v1 (publisher exemption).
The server provides signals; the client overlays them on locally-fetched
positions to compute order deltas. The API never joins these.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Position:
    ticker: str
    quantity: float
    market_value: float
    avg_cost: float
    unrealized_pnl: float
    currency: str


async def fetch_positions(ibkr_client: Any, account_id: str) -> list[Position]:
    """Fetch current positions from IBKR. Returns normalized Position list."""
    raw_positions = await ibkr_client.get_positions(account_id)

    positions = []
    for pos in raw_positions:
        positions.append(Position(
            ticker=pos.get("contractDesc", pos.get("ticker", "")),
            quantity=float(pos.get("position", 0)),
            market_value=float(pos.get("mktValue", 0)),
            avg_cost=float(pos.get("avgCost", 0)),
            unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
            currency=pos.get("currency", "USD"),
        ))

    logger.info("positions.fetched", account_id=account_id, count=len(positions))
    return positions
