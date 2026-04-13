"""
Signal generation workflow — the core pipeline that produces portfolio signals.

Single workflow definition, two instantiation modes (backtest vs live).
The TimeSource is the ONLY variable. Every other component is byte-identical (ADR-005).

Pipeline: TimeSource → data fetch → regime detection → allocator → cost model → signal output

Generates signals for all 5 model portfolios per run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import structlog

from midas_strategy.allocator import allocate, AllocationResult, PORTFOLIO_VOL_TARGETS
from midas_strategy.allocator.blending import blend_momentum
from midas_strategy.cost import calculate_rebalance_cost, CostBreakdown
from midas_strategy.regime import RegimeDetector, RegimeLevel, RegimeState
from midas_strategy.signals.time_source import TimeSource
from midas_strategy.sleeves import SLEEVES, get_primary_tickers

logger = structlog.get_logger(__name__)


@dataclass
class SignalOutput:
    """Complete signal for one model portfolio at one point in time."""
    model_portfolio_id: str
    timestamp: datetime
    regime: RegimeState
    allocation: AllocationResult
    cost_breakdown: list[CostBreakdown]
    total_cost: float
    reasoning: dict[str, str]
    signal_values_snapshot: dict[str, float]


def compute_daily_returns(bars_by_sleeve: dict[str, list[dict]], window: int = 504) -> dict[str, list[float]]:
    """Convert bar data to daily return series per sleeve.

    Uses primary ticker's adj_close for each sleeve.
    Window defaults to 504 (2 years) for the longest horizon.
    """
    returns = {}
    for sleeve_id, bars in bars_by_sleeve.items():
        if len(bars) < 2:
            returns[sleeve_id] = []
            continue
        prices = [float(b.get("adj_close", b.get("close", 0))) for b in bars[-window:]]
        daily = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                daily.append((prices[i] - prices[i - 1]) / prices[i - 1])
            else:
                daily.append(0.0)
        returns[sleeve_id] = daily
    return returns


def compute_drawdown_from_peak(spy_bars: list[dict], lookback: int = 252) -> float:
    """Compute drawdown from 252-day trailing peak of SPY."""
    if len(spy_bars) < 2:
        return 0.0
    prices = [float(b.get("adj_close", b.get("close", 0))) for b in spy_bars[-lookback:]]
    if not prices:
        return 0.0
    peak = max(prices)
    current = prices[-1]
    if peak <= 0:
        return 0.0
    return (current - peak) / peak


def compute_spy_tlt_correlation(spy_bars: list[dict], tlt_bars: list[dict], window: int = 21) -> float:
    """Compute 21-day rolling correlation between SPY and TLT returns."""
    if len(spy_bars) < window + 1 or len(tlt_bars) < window + 1:
        return -0.3  # Default: assume negative correlation (normal)

    spy_prices = [float(b.get("adj_close", b.get("close", 0))) for b in spy_bars[-(window + 1):]]
    tlt_prices = [float(b.get("adj_close", b.get("close", 0))) for b in tlt_bars[-(window + 1):]]

    spy_ret = [(spy_prices[i] - spy_prices[i - 1]) / spy_prices[i - 1] for i in range(1, len(spy_prices)) if spy_prices[i - 1] > 0]
    tlt_ret = [(tlt_prices[i] - tlt_prices[i - 1]) / tlt_prices[i - 1] for i in range(1, len(tlt_prices)) if tlt_prices[i - 1] > 0]

    min_len = min(len(spy_ret), len(tlt_ret))
    if min_len < 5:
        return -0.3

    corr = np.corrcoef(spy_ret[:min_len], tlt_ret[:min_len])[0, 1]
    return float(corr) if np.isfinite(corr) else -0.3


def compute_regime_signals(
    regime_raw: dict[str, float],
    bars_by_sleeve: dict[str, list[dict]],
    spy_bars: list[dict],
) -> dict[str, float]:
    """Assemble the full set of regime signal inputs.

    Combines FRED data (HY OAS, VIX, yield curve) with computed signals
    (PC1, realized vol, SMA persistence).
    """
    signals = {}

    # Direct from FRED
    signals["hy_oas"] = regime_raw.get("hy_oas", 0)
    signals["vix_level"] = regime_raw.get("vix", 0)
    signals["yield_curve_3m10y"] = regime_raw.get("yield_10y", 0) - regime_raw.get("yield_3m", 0)

    # VIX3M backwardation
    vix = regime_raw.get("vix", 0)
    vix3m = regime_raw.get("vix3m", 0)
    signals["vix3m_backwardation"] = (vix / vix3m) if vix3m > 0 else 1.0

    # Realized volatility (21-day annualized)
    if spy_bars and len(spy_bars) > 21:
        spy_prices = [float(b.get("adj_close", b.get("close", 0))) for b in spy_bars[-22:]]
        spy_rets = [(spy_prices[i] - spy_prices[i - 1]) / spy_prices[i - 1] for i in range(1, len(spy_prices)) if spy_prices[i - 1] > 0]
        if spy_rets:
            import math
            signals["realized_vol_21d"] = float(np.std(spy_rets)) * math.sqrt(252) * 100  # as percentage
        else:
            signals["realized_vol_21d"] = 15.0
    else:
        signals["realized_vol_21d"] = 15.0

    # 200d SMA persistence
    if spy_bars and len(spy_bars) > 200:
        spy_prices = [float(b.get("adj_close", b.get("close", 0))) for b in spy_bars[-200:]]
        sma200 = sum(spy_prices) / len(spy_prices)
        current = spy_prices[-1]
        # Count consecutive days below SMA (negative = below = stress)
        days_below = 0
        for p in reversed(spy_prices):
            if p < sma200:
                days_below += 1
            else:
                break
        signals["sma200_persistence"] = -days_below if current < sma200 else days_below
    else:
        signals["sma200_persistence"] = 0

    # Cross-sector PC1 variance (simplified: variance of sector returns)
    sector_bars = bars_by_sleeve.get("equity_sector", [])
    if sector_bars and len(sector_bars) > 21:
        sector_prices = [float(b.get("adj_close", b.get("close", 0))) for b in sector_bars[-22:]]
        sector_rets = [(sector_prices[i] - sector_prices[i - 1]) / sector_prices[i - 1] for i in range(1, len(sector_prices)) if sector_prices[i - 1] > 0]
        signals["pc1_variance"] = float(np.var(sector_rets)) * 10000 if sector_rets else 0.4
    else:
        signals["pc1_variance"] = 0.4

    return signals


async def generate_signals(
    time_source: TimeSource,
    data_fabric: Any,
    old_weights: dict[str, dict[str, float]] | None = None,
) -> list[SignalOutput]:
    """Generate signals for all 5 model portfolios.

    This is the main entry point — called by both the backtest engine
    and the live signal scheduler.

    Args:
        time_source: Historical or live time source (the ONLY variable).
        data_fabric: DataFabric instance for reading bars and signals.
        old_weights: Optional dict of portfolio_id → previous weights (for turnover).

    Returns:
        List of SignalOutput, one per model portfolio.
    """
    current_date = time_source.get_current_date()
    start, end = time_source.get_bar_range(lookback_days=600)  # ~2.5 years for blending
    old_w = old_weights or {}

    logger.info("workflow.generate.start", date=str(current_date), mode=time_source.mode.value)

    # 1. Fetch bar data for all sleeves
    primary_tickers = get_primary_tickers()
    bars_by_sleeve: dict[str, list[dict]] = {}
    for sleeve_id, ticker in primary_tickers.items():
        bars_by_sleeve[sleeve_id] = await data_fabric.get_bars(ticker, start, end)

    # 2. Fetch regime signal inputs from FRED/data fabric
    regime_raw = await data_fabric.get_regime_signals(current_date)

    # 3. Compute derived signals
    spy_bars = bars_by_sleeve.get("equity_sector", [])
    tlt_bars = bars_by_sleeve.get("govt_bonds_long", [])
    regime_signals = compute_regime_signals(regime_raw, bars_by_sleeve, spy_bars)

    # 4. Detect regime
    drawdown = compute_drawdown_from_peak(spy_bars)
    spy_tlt_corr = compute_spy_tlt_correlation(spy_bars, tlt_bars)

    detector = RegimeDetector()
    regime_state = detector.detect(
        signals=regime_signals,
        drawdown_from_peak=drawdown,
        spy_tlt_correlation=spy_tlt_corr,
        current_date=current_date,
    )

    # 5. Compute daily returns for allocator
    returns = compute_daily_returns(bars_by_sleeve)

    # 6. Generate signal for each portfolio
    outputs = []
    for portfolio_id in PORTFOLIO_VOL_TARGETS:
        allocation = allocate(
            returns=returns,
            regime=regime_state.regime,
            model_portfolio_id=portfolio_id,
            old_weights=old_w.get(portfolio_id),
        )

        # 7. Compute transaction cost for the rebalance
        trades = []
        for sleeve_id, weight in allocation.weights.items():
            ticker = primary_tickers.get(sleeve_id, "SPY")
            # Estimate shares from weight (assume $100k portfolio for cost modeling)
            portfolio_value = 100_000
            target_value = weight * portfolio_value
            price = 100.0  # Placeholder — in wired version, comes from latest bar
            if price > 0:
                shares = int(target_value / price)
                if shares > 0:
                    old_weight = old_w.get(portfolio_id, {}).get(sleeve_id, 0.0)
                    direction = "buy" if weight > old_weight else "sell"
                    trades.append({
                        "ticker": ticker,
                        "shares": abs(shares),
                        "direction": direction,
                        "price": price,
                    })

        cost_breakdowns, total_cost = calculate_rebalance_cost(
            trades, regime=regime_state.regime.value
        )

        # 8. Build reasoning
        reasoning = {
            "regime": f"Regime: {regime_state.regime.value} (score: {regime_state.ensemble_score:.3f}, confidence: {regime_state.confidence:.1%})",
            "allocation": f"Selected {len(allocation.weights)} sleeves, vol target {allocation.vol_target:.0%}",
            "cost": f"Total rebalance cost: ${total_cost:.2f}",
        }
        if regime_state.overrides_active:
            reasoning["overrides"] = f"Active overrides: {', '.join(regime_state.overrides_active)}"
        if allocation.is_fallback:
            reasoning["fallback"] = "Using HRP fallback (momentum signal degenerate)"

        output = SignalOutput(
            model_portfolio_id=portfolio_id,
            timestamp=datetime.utcnow(),
            regime=regime_state,
            allocation=allocation,
            cost_breakdown=cost_breakdowns,
            total_cost=total_cost,
            reasoning=reasoning,
            signal_values_snapshot=regime_signals,
        )
        outputs.append(output)

    logger.info(
        "workflow.generate.complete",
        date=str(current_date),
        regime=regime_state.regime.value,
        portfolios=len(outputs),
    )
    return outputs
