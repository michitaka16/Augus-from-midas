"""
Order submission — user-initiated, biometric-confirmed (M05-06).

Takes previewed orders and submits them to IBKR.
Market orders for ETFs (liquid — limit orders add complexity without benefit).
Polls until filled or cancelled. Writes result to audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncio
import structlog

logger = structlog.get_logger(__name__)

_POLL_INTERVAL = 2.0  # seconds
_MAX_POLL_ATTEMPTS = 30  # 60 seconds max


@dataclass
class OrderResult:
    ticker: str
    direction: str
    shares: int
    status: str  # "filled", "cancelled", "error", "timeout"
    fill_price: float | None
    fill_time: datetime | None
    order_id: str | None
    error: str | None


async def submit_orders(
    ibkr_client: Any,
    account_id: str,
    trades: list[dict],
    audit_trail: Any | None = None,
) -> list[OrderResult]:
    """Submit a batch of market orders to IBKR.

    Each trade: {"ticker": str, "direction": str, "shares": int}

    Biometric confirmation is handled by the frontend before calling this.
    """
    results = []

    for trade in trades:
        ticker = trade["ticker"]
        direction = trade["direction"]
        shares = trade["shares"]

        logger.info(
            "order.submit.start",
            ticker=ticker,
            direction=direction,
            shares=shares,
        )

        order = {
            "conid": 0,  # Would be resolved from ticker via IBKR contract search
            "orderType": "MKT",
            "side": "BUY" if direction == "buy" else "SELL",
            "quantity": shares,
            "tif": "DAY",
        }

        try:
            response = await ibkr_client.place_order(account_id, order)
            order_id = _extract_order_id(response)

            if order_id:
                fill = await _poll_for_fill(ibkr_client, order_id)
                result = OrderResult(
                    ticker=ticker,
                    direction=direction,
                    shares=shares,
                    status=fill["status"],
                    fill_price=fill.get("fill_price"),
                    fill_time=fill.get("fill_time"),
                    order_id=order_id,
                    error=None,
                )
            else:
                result = OrderResult(
                    ticker=ticker, direction=direction, shares=shares,
                    status="error", fill_price=None, fill_time=None,
                    order_id=None, error="No order ID returned",
                )

        except Exception as e:
            logger.exception("order.submit.error", ticker=ticker)
            result = OrderResult(
                ticker=ticker, direction=direction, shares=shares,
                status="error", fill_price=None, fill_time=None,
                order_id=None, error=str(e),
            )

        results.append(result)

        # Write to audit trail
        if audit_trail:
            await audit_trail.append(
                event_type="order_submitted" if result.status != "error" else "order_failed",
                payload={
                    "ticker": ticker,
                    "direction": direction,
                    "shares": shares,
                    "status": result.status,
                    "fill_price": result.fill_price,
                    "order_id": result.order_id,
                    "error": result.error,
                },
                actor="user",
            )

        logger.info(
            "order.submit.result",
            ticker=ticker,
            status=result.status,
            fill_price=result.fill_price,
        )

    return results


def _extract_order_id(response: Any) -> str | None:
    """Extract order ID from IBKR response (varies by format)."""
    if isinstance(response, list) and response:
        return str(response[0].get("order_id", response[0].get("id", "")))
    if isinstance(response, dict):
        return str(response.get("order_id", response.get("id", "")))
    return None


async def _poll_for_fill(ibkr_client: Any, order_id: str) -> dict:
    """Poll IBKR for order fill status."""
    for _ in range(_MAX_POLL_ATTEMPTS):
        try:
            status = await ibkr_client.get_order_status(order_id)
            order_status = status.get("order_status", "").lower()

            if order_status in ("filled", "inactive"):
                return {
                    "status": "filled",
                    "fill_price": status.get("avg_price"),
                    "fill_time": datetime.utcnow(),
                }
            elif order_status in ("cancelled", "error"):
                return {"status": order_status}

        except Exception:
            logger.warning("order.poll_error", order_id=order_id)

        await asyncio.sleep(_POLL_INTERVAL)

    return {"status": "timeout"}
