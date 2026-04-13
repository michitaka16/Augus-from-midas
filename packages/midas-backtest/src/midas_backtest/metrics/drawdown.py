"""Drawdown metrics — max drawdown, duration, underwater curve."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class DrawdownMetrics:
    max_drawdown: float
    max_drawdown_duration_days: int
    avg_drawdown_duration_days: float
    underwater_curve: list[float]


def max_drawdown_from_returns(returns: Sequence[float]) -> float:
    """Compute maximum drawdown from a return series."""
    if not returns:
        return 0.0
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        cumulative *= (1 + r)
        peak = max(peak, cumulative)
        dd = (cumulative - peak) / peak
        max_dd = min(max_dd, dd)
    return max_dd  # Negative number


def compute_drawdown_metrics(returns: Sequence[float]) -> DrawdownMetrics:
    """Full drawdown analysis including duration and underwater curve."""
    if not returns:
        return DrawdownMetrics(0, 0, 0, [])

    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    underwater: list[float] = []
    durations: list[int] = []
    current_dd_length = 0

    for r in returns:
        cumulative *= (1 + r)
        peak = max(peak, cumulative)
        dd = (cumulative - peak) / peak
        underwater.append(dd)
        max_dd = min(max_dd, dd)

        if dd < 0:
            current_dd_length += 1
        else:
            if current_dd_length > 0:
                durations.append(current_dd_length)
            current_dd_length = 0

    if current_dd_length > 0:
        durations.append(current_dd_length)

    max_duration = max(durations) if durations else 0
    avg_duration = sum(durations) / len(durations) if durations else 0

    return DrawdownMetrics(
        max_drawdown=round(max_dd, 6),
        max_drawdown_duration_days=max_duration,
        avg_drawdown_duration_days=round(avg_duration, 1),
        underwater_curve=[round(u, 6) for u in underwater],
    )
