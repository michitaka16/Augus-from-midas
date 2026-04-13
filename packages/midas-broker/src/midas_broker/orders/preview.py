"""
Order preview — compute trade deltas from signal + current positions (M05-05).

This computation happens CLIENT-SIDE in v1 (publisher exemption).
The server provides impersonal signals; the client fetches positions
from IBKR and computes the delta locally.

Feature-flagged pending legal opinion (PC3 resolution, ADR-012).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TradePreview:
    ticker: str
    direction: str  # "buy" or "sell"
    shares: int
    estimated_value: float
    estimated_commission: float


def compute_order_delta(
    target_allocations: dict[str, float],
    current_positions: list[dict],
    portfolio_value: float,
    primary_tickers: dict[str, str],
) -> list[TradePreview]:
    """Compute the trades needed to move from current to target allocation.

    Args:
        target_allocations: sleeve_id → target weight (0-1)
        current_positions: List of Position dicts with ticker, quantity, market_value
        portfolio_value: Total portfolio value in USD
        primary_tickers: sleeve_id → primary ETF ticker

    Returns:
        List of TradePreview — what to buy/sell to reach the target.
    """
    # Build current weight by ticker
    current_by_ticker = {}
    for pos in current_positions:
        ticker = pos.get("ticker", "")
        value = float(pos.get("market_value", 0))
        current_by_ticker[ticker] = value

    trades = []
    for sleeve_id, target_weight in target_allocations.items():
        ticker = primary_tickers.get(sleeve_id)
        if not ticker:
            continue

        target_value = target_weight * portfolio_value
        current_value = current_by_ticker.get(ticker, 0)
        delta_value = target_value - current_value

        if abs(delta_value) < 50:  # Skip trades under $50
            continue

        # Estimate shares (would use real-time price in wired version)
        estimated_price = current_value / float(max(1, abs(
            next((p.get("quantity", 1) for p in current_positions if p.get("ticker") == ticker), 1)
        ))) if current_value > 0 else 100.0

        if estimated_price <= 0:
            estimated_price = 100.0

        shares = int(abs(delta_value) / estimated_price)
        if shares <= 0:
            continue

        trades.append(TradePreview(
            ticker=ticker,
            direction="buy" if delta_value > 0 else "sell",
            shares=shares,
            estimated_value=round(abs(delta_value), 2),
            estimated_commission=max(0.35, shares * 0.0035),
        ))

    logger.info("preview.computed", trade_count=len(trades))
    return trades
