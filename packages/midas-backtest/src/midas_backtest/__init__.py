"""
Midas Backtest Engine — walk-forward, CPCV, metrics, replay, reports.

Uses the SAME strategy workflow as live (ADR-005). Only TimeSourceNode differs.
"""

from midas_backtest.engine import WalkForwardEngine, CPCVEngine
from midas_backtest.metrics import annualized_sharpe, deflated_sharpe, max_drawdown_from_returns
from midas_backtest.reports import BacktestReport, generate_report

__all__ = [
    "WalkForwardEngine",
    "CPCVEngine",
    "annualized_sharpe",
    "deflated_sharpe",
    "max_drawdown_from_returns",
    "BacktestReport",
    "generate_report",
]
