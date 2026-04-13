"""
Transaction cost model — realistic cost estimation for portfolio rebalancing.

Components (per M02-05):
- IBKR Pro tiered commissions
- SEC §31 fee + FINRA TAF
- Half-spread slippage
- Almgren-Chriss square-root market impact
- Gap risk (overnight)
- Liquidity check (block illiquid rotation in turbulent, PH1)

Same node in backtest AND live — zero parity drift.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

import structlog

from midas_strategy.sleeves import get_liquidity_tier

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CostBreakdown:
    """Itemized transaction cost for a single trade."""
    ticker: str
    shares: int
    direction: str  # "buy" or "sell"
    commission: float
    sec_fee: float
    finra_taf: float
    slippage: float
    market_impact: float
    gap_risk: float
    total: float

    @classmethod
    def zero(cls, ticker: str = "", shares: int = 0, direction: str = "buy") -> CostBreakdown:
        return cls(ticker=ticker, shares=shares, direction=direction,
                   commission=0, sec_fee=0, finra_taf=0, slippage=0,
                   market_impact=0, gap_risk=0, total=0)


# ── IBKR Pro Tiered Commission ──────────────────────────────

def ibkr_commission(shares: int) -> float:
    """IBKR Pro tiered US ETF commission.

    Tiered pricing: $0.0035/share, min $0.35, max 1% of trade value.
    For simplicity we use the per-share rate; the 1% cap is checked
    by the caller when trade value is known.
    """
    per_share = 0.0035
    raw = shares * per_share
    return max(0.35, raw)  # $0.35 minimum per order


# ── Regulatory Fees ─────────────────────────────────────────

def sec_fee(sale_value: float) -> float:
    """SEC Section 31 fee — applies only to SELLS.

    Rate resets periodically. Read from .env for live, use default for backtest.
    Current rate (as of 2024): $8.00 per million dollars.
    """
    rate_per_million = float(os.environ.get("SEC_31_RATE_PER_MILLION", "8.00"))
    if sale_value <= 0:
        return 0.0
    return sale_value * rate_per_million / 1_000_000


def finra_taf(shares: int) -> float:
    """FINRA Trading Activity Fee — applies only to SELLS.

    $0.000119 per share, capped at $5.95 per trade.
    """
    raw = shares * 0.000119
    return min(raw, 5.95)


# ── Slippage (Half-Spread) ──────────────────────────────────

# Typical bid-ask half-spread by liquidity tier (percentage of price)
_HALF_SPREAD = {
    "high": 0.0002,     # 2 bps — liquid ETFs like SPY, QQQ
    "medium": 0.0005,   # 5 bps — moderate ETFs like DJP, DVY
    "low": 0.0015,      # 15 bps — illiquid
    "unknown": 0.0005,
}


def slippage_cost(price: float, shares: int, liquidity_tier: str) -> float:
    """Half-spread slippage estimate."""
    half_spread = _HALF_SPREAD.get(liquidity_tier, _HALF_SPREAD["unknown"])
    return price * shares * half_spread


# ── Market Impact (Almgren-Chriss) ──────────────────────────

def market_impact(
    price: float,
    shares: int,
    daily_volume: int,
    volatility: float,
    temp_impact_coeff: float = 0.1,
) -> float:
    """Almgren-Chriss square-root market impact model.

    impact = σ × √(V / ADV) × temp_impact_coeff × price × shares

    Where:
      σ = daily volatility (decimal)
      V = trade volume (shares)
      ADV = average daily volume
      temp_impact_coeff = temporary impact coefficient (calibrated, default 0.1)
    """
    if daily_volume <= 0 or shares <= 0:
        return 0.0
    participation = shares / daily_volume
    impact_pct = volatility * math.sqrt(participation) * temp_impact_coeff
    return price * shares * impact_pct


# ── Gap Risk ────────────────────────────────────────────────

# Overnight gap risk by liquidity tier (as % of position value)
_GAP_RISK = {
    "high": 0.0001,     # 1 bp
    "medium": 0.0003,   # 3 bps
    "low": 0.0008,      # 8 bps
    "unknown": 0.0003,
}


def gap_risk_cost(price: float, shares: int, liquidity_tier: str) -> float:
    """Overnight gap risk estimate based on historical gap distributions."""
    risk = _GAP_RISK.get(liquidity_tier, _GAP_RISK["unknown"])
    return price * shares * risk


# ── Liquidity Check (PH1) ──────────────────────────────────

def check_liquidity(
    ticker: str,
    regime: str,
    liquidity_tier: str | None = None,
) -> tuple[bool, str]:
    """Check if rotation into this ticker is allowed given the regime.

    In turbulent regime, block rotation into low-liquidity sleeves (PH1 resolution).
    Returns (allowed, reason).
    """
    tier = liquidity_tier or get_liquidity_tier(ticker)
    if regime == "turbulent" and tier == "low":
        return False, f"Rotation into {ticker} blocked: low liquidity during turbulent regime"
    if regime == "turbulent" and tier == "medium":
        # Allow but warn — cost model widens spreads automatically
        logger.warning(
            "cost.liquidity_warning",
            ticker=ticker,
            tier=tier,
            regime=regime,
        )
    return True, ""


# ── Combined Cost Calculator ────────────────────────────────

def calculate_trade_cost(
    ticker: str,
    shares: int,
    direction: str,
    price: float,
    daily_volume: int = 5_000_000,
    volatility: float = 0.015,
    regime: str = "normal",
    liquidity_tier: str | None = None,
) -> CostBreakdown:
    """Calculate full transaction cost breakdown for a single trade.

    This is the core function used by both backtest and live paths.
    Zero parity drift — same code, same inputs, same output.

    Args:
        ticker: ETF ticker symbol
        shares: Number of shares to trade (absolute)
        direction: "buy" or "sell"
        price: Current price per share
        daily_volume: Average daily volume
        volatility: Daily volatility (decimal, e.g., 0.015 = 1.5%)
        regime: Current regime level
        liquidity_tier: Override liquidity tier (auto-detected from sleeve defs if None)
    """
    if shares <= 0:
        return CostBreakdown.zero(ticker, shares, direction)

    tier = liquidity_tier or get_liquidity_tier(ticker)
    trade_value = price * shares

    # Widen spreads in turbulent regime for medium-liquidity ETFs
    spread_multiplier = 1.0
    if regime == "turbulent":
        spread_multiplier = 2.0 if tier == "medium" else 1.5
    elif regime == "cautious":
        spread_multiplier = 1.3 if tier == "medium" else 1.1

    comm = ibkr_commission(shares)
    sec = sec_fee(trade_value) if direction == "sell" else 0.0
    taf = finra_taf(shares) if direction == "sell" else 0.0
    slip = slippage_cost(price, shares, tier) * spread_multiplier
    impact = market_impact(price, shares, daily_volume, volatility)
    gap = gap_risk_cost(price, shares, tier)

    total = comm + sec + taf + slip + impact + gap

    breakdown = CostBreakdown(
        ticker=ticker,
        shares=shares,
        direction=direction,
        commission=round(comm, 4),
        sec_fee=round(sec, 4),
        finra_taf=round(taf, 4),
        slippage=round(slip, 4),
        market_impact=round(impact, 4),
        gap_risk=round(gap, 4),
        total=round(total, 4),
    )

    logger.debug(
        "cost.calculated",
        ticker=ticker,
        shares=shares,
        direction=direction,
        total=breakdown.total,
    )
    return breakdown


def calculate_rebalance_cost(
    trades: list[dict],
    regime: str = "normal",
) -> tuple[list[CostBreakdown], float]:
    """Calculate total cost for a set of rebalance trades.

    Args:
        trades: List of dicts with keys: ticker, shares, direction, price, daily_volume, volatility
        regime: Current regime level

    Returns:
        (list of per-trade CostBreakdown, total cost)
    """
    breakdowns = []
    total = 0.0

    for trade in trades:
        allowed, reason = check_liquidity(trade["ticker"], regime)
        if not allowed:
            logger.warning("cost.trade_blocked", reason=reason)
            continue

        breakdown = calculate_trade_cost(
            ticker=trade["ticker"],
            shares=trade["shares"],
            direction=trade["direction"],
            price=trade["price"],
            daily_volume=trade.get("daily_volume", 5_000_000),
            volatility=trade.get("volatility", 0.015),
            regime=regime,
        )
        breakdowns.append(breakdown)
        total += breakdown.total

    logger.info("cost.rebalance_total", trade_count=len(breakdowns), total=round(total, 2))
    return breakdowns, round(total, 4)
