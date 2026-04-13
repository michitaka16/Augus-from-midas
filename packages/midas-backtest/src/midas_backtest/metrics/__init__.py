"""Backtest metrics — Sharpe, drawdown, benchmarks, cost attribution."""

from midas_backtest.metrics.sharpe import (
    sharpe_ratio,
    annualized_sharpe,
    deflated_sharpe,
)
from midas_backtest.metrics.drawdown import (
    max_drawdown_from_returns,
    compute_drawdown_metrics,
    DrawdownMetrics,
)
from midas_backtest.metrics.benchmark import (
    benchmark_60_40,
    benchmark_equal_weight,
    benchmark_vti,
    BenchmarkResult,
)

__all__ = [
    "sharpe_ratio",
    "annualized_sharpe",
    "deflated_sharpe",
    "max_drawdown_from_returns",
    "compute_drawdown_metrics",
    "DrawdownMetrics",
    "benchmark_60_40",
    "benchmark_equal_weight",
    "benchmark_vti",
    "BenchmarkResult",
]
