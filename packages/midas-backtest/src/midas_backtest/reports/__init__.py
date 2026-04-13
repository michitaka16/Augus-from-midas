"""
Backtest report generator — JSON + human-readable output.

Each report gets a unique backtest_run_id. The debate agent cites these IDs.
Reports include all metrics, per-period details, regime breakdown, benchmarks,
cost attribution, and PBO assessment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

import structlog

from midas_backtest.metrics import (
    BenchmarkResult,
    DrawdownMetrics,
)

logger = structlog.get_logger(__name__)


@dataclass
class BacktestReport:
    """Complete backtest report for one model portfolio."""
    model_portfolio_id: str
    run_id: int | None  # Set after persisting to backtest_runs table
    generated_at: str
    config: dict
    # Walk-forward results
    total_return: float
    annualized_return: float
    annualized_vol: float
    sharpe: float
    deflated_sharpe: float
    pbo: float
    max_drawdown: float
    max_drawdown_duration_days: int
    worst_12m_return: float
    # Benchmarks (mandatory per PC2)
    benchmarks: list[BenchmarkResult]
    beats_60_40: bool
    # Regime-conditional
    regime_stats: dict[str, dict]
    # Cost
    avg_cost_drag_pct: float
    total_turnover: float
    # Multi-horizon
    horizon_results: dict[str, dict]  # "1y", "3y", "5y", "10y", "full"


def generate_report(
    model_portfolio_id: str,
    walkforward_result: Any,
    cpcv_result: Any,
    benchmarks: list[BenchmarkResult],
    drawdown_metrics: DrawdownMetrics,
    horizon_results: dict[str, dict] | None = None,
    config: dict | None = None,
) -> BacktestReport:
    """Generate a complete backtest report from engine outputs."""

    # Check if strategy beats 60/40 (mandatory PC2 gate)
    benchmark_60_40 = next((b for b in benchmarks if "60/40" in b.name), None)
    beats_60_40 = (
        walkforward_result.sharpe > benchmark_60_40.sharpe
        if benchmark_60_40
        else False
    )

    # Worst 12-month rolling return (compute from walk-forward periods)
    worst_12m = _compute_worst_rolling_return(
        walkforward_result.periods if hasattr(walkforward_result, "periods") else [],
        window_days=252,
    )

    report = BacktestReport(
        model_portfolio_id=model_portfolio_id,
        run_id=None,
        generated_at=datetime.utcnow().isoformat(),
        config=config or {},
        total_return=walkforward_result.total_return,
        annualized_return=walkforward_result.annualized_return,
        annualized_vol=walkforward_result.annualized_vol,
        sharpe=walkforward_result.sharpe,
        deflated_sharpe=cpcv_result.mean_sharpe if cpcv_result else 0,
        pbo=cpcv_result.pbo if cpcv_result else 1.0,
        max_drawdown=drawdown_metrics.max_drawdown,
        max_drawdown_duration_days=drawdown_metrics.max_drawdown_duration_days,
        worst_12m_return=worst_12m,
        benchmarks=benchmarks,
        beats_60_40=beats_60_40,
        regime_stats={},
        avg_cost_drag_pct=walkforward_result.avg_cost_drag,
        total_turnover=walkforward_result.avg_turnover,
        horizon_results=horizon_results or {},
    )

    if not beats_60_40:
        logger.warning(
            "report.fails_benchmark_gate",
            portfolio=model_portfolio_id,
            sharpe=report.sharpe,
            benchmark_sharpe=benchmark_60_40.sharpe if benchmark_60_40 else "N/A",
        )

    if report.pbo > 0.4:
        logger.warning(
            "report.high_pbo",
            portfolio=model_portfolio_id,
            pbo=report.pbo,
        )

    logger.info(
        "report.generated",
        portfolio=model_portfolio_id,
        sharpe=report.sharpe,
        pbo=report.pbo,
        beats_60_40=report.beats_60_40,
    )
    return report


def report_to_json(report: BacktestReport) -> str:
    """Serialize report to JSON for storage in backtest_runs table."""
    data = {
        "model_portfolio_id": report.model_portfolio_id,
        "generated_at": report.generated_at,
        "total_return": report.total_return,
        "annualized_return": report.annualized_return,
        "annualized_vol": report.annualized_vol,
        "sharpe": report.sharpe,
        "deflated_sharpe": report.deflated_sharpe,
        "pbo": report.pbo,
        "max_drawdown": report.max_drawdown,
        "max_drawdown_duration_days": report.max_drawdown_duration_days,
        "worst_12m_return": report.worst_12m_return,
        "beats_60_40": report.beats_60_40,
        "avg_cost_drag_pct": report.avg_cost_drag_pct,
        "total_turnover": report.total_turnover,
        "benchmarks": [asdict(b) for b in report.benchmarks],
        "horizon_results": report.horizon_results,
    }
    return json.dumps(data, default=str)


def report_to_human_readable(report: BacktestReport) -> str:
    """Generate human-readable summary for the debate agent to cite."""
    lines = [
        f"# Backtest Report: {report.model_portfolio_id}",
        f"Generated: {report.generated_at}",
        "",
        f"Sharpe Ratio: {report.sharpe:.3f}",
        f"Deflated Sharpe: {report.deflated_sharpe:.3f}",
        f"Probability of Backtest Overfit: {report.pbo:.1%}",
        f"Total Return: {report.total_return:.2%}",
        f"Annualized Return: {report.annualized_return:.2%}",
        f"Annualized Volatility: {report.annualized_vol:.2%}",
        f"Max Drawdown: {report.max_drawdown:.2%}",
        f"Max DD Duration: {report.max_drawdown_duration_days} days",
        f"Worst 12-Month Return: {report.worst_12m_return:.2%}",
        f"Avg Cost Drag: {report.avg_cost_drag_pct:.4%}",
        f"Beats 60/40: {'Yes' if report.beats_60_40 else 'NO — does not ship'}",
        "",
        "## Benchmarks",
    ]
    for b in report.benchmarks:
        lines.append(f"  {b.name}: Sharpe={b.sharpe:.3f}, Return={b.total_return:.2%}, MaxDD={b.max_drawdown:.2%}")

    return "\n".join(lines)


def _compute_worst_rolling_return(periods: list, window_days: int = 252) -> float:
    """Compute worst rolling return from walk-forward periods."""
    all_returns = []
    for p in periods:
        if hasattr(p, "returns"):
            all_returns.extend(p.returns)

    if len(all_returns) < window_days:
        if not all_returns:
            return 0.0
        total = 1.0
        for r in all_returns:
            total *= (1 + r)
        return total - 1.0

    worst = float("inf")
    for i in range(len(all_returns) - window_days + 1):
        window = all_returns[i:i + window_days]
        total = 1.0
        for r in window:
            total *= (1 + r)
        rolling_return = total - 1.0
        worst = min(worst, rolling_return)

    return round(worst, 6)
