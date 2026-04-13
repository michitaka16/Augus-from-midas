"""Benchmark comparison — mandatory per PC2 resolution.

Every backtest report includes side-by-side comparison against:
- Static 60/40 (SPY/TLT)
- Equal-weight 8-sleeve
- VTI-only (total market)

If any model portfolio fails to beat 60/40 net-of-costs, we do not ship it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from midas_backtest.metrics.sharpe import annualized_sharpe
from midas_backtest.metrics.drawdown import max_drawdown_from_returns


@dataclass
class BenchmarkResult:
    name: str
    total_return: float
    annualized_return: float
    sharpe: float
    max_drawdown: float
    cost_drag_pct: float


def benchmark_60_40(spy_returns: list[float], tlt_returns: list[float]) -> BenchmarkResult:
    """Static 60% SPY / 40% TLT benchmark."""
    if not spy_returns or not tlt_returns:
        return BenchmarkResult("60/40", 0, 0, 0, 0, 0)

    min_len = min(len(spy_returns), len(tlt_returns))
    blended = [0.6 * spy_returns[i] + 0.4 * tlt_returns[i] for i in range(min_len)]

    total = 1.0
    for r in blended:
        total *= (1 + r)
    total -= 1.0

    ann = (1 + total) ** (252 / max(min_len, 1)) - 1 if min_len > 0 else 0

    return BenchmarkResult(
        name="60/40 (SPY/TLT)",
        total_return=round(total, 6),
        annualized_return=round(ann, 6),
        sharpe=round(annualized_sharpe(blended), 4),
        max_drawdown=round(max_drawdown_from_returns(blended), 6),
        cost_drag_pct=0.0,  # Static = no rebalance cost
    )


def benchmark_equal_weight(
    sleeve_returns: dict[str, list[float]],
) -> BenchmarkResult:
    """Equal-weight across all sleeves, rebalanced daily (theoretical)."""
    if not sleeve_returns:
        return BenchmarkResult("Equal Weight", 0, 0, 0, 0, 0)

    n_sleeves = len(sleeve_returns)
    weight = 1.0 / n_sleeves
    min_len = min(len(r) for r in sleeve_returns.values())

    blended = []
    for i in range(min_len):
        daily = sum(
            weight * returns[i]
            for returns in sleeve_returns.values()
        )
        blended.append(daily)

    total = 1.0
    for r in blended:
        total *= (1 + r)
    total -= 1.0

    ann = (1 + total) ** (252 / max(min_len, 1)) - 1 if min_len > 0 else 0

    return BenchmarkResult(
        name=f"Equal Weight ({n_sleeves} sleeves)",
        total_return=round(total, 6),
        annualized_return=round(ann, 6),
        sharpe=round(annualized_sharpe(blended), 4),
        max_drawdown=round(max_drawdown_from_returns(blended), 6),
        cost_drag_pct=0.001,  # Minimal rebalance cost
    )


def benchmark_vti(spy_returns: list[float]) -> BenchmarkResult:
    """VTI-only (total market, approximated by SPY)."""
    if not spy_returns:
        return BenchmarkResult("VTI", 0, 0, 0, 0, 0)

    total = 1.0
    for r in spy_returns:
        total *= (1 + r)
    total -= 1.0

    n = len(spy_returns)
    ann = (1 + total) ** (252 / max(n, 1)) - 1 if n > 0 else 0

    return BenchmarkResult(
        name="VTI (Total Market)",
        total_return=round(total, 6),
        annualized_return=round(ann, 6),
        sharpe=round(annualized_sharpe(spy_returns), 4),
        max_drawdown=round(max_drawdown_from_returns(spy_returns), 6),
        cost_drag_pct=0.0,
    )
