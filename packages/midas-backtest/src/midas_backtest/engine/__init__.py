"""Backtest engines — walk-forward and CPCV."""

from midas_backtest.engine.walkforward import WalkForwardEngine, WalkForwardResult
from midas_backtest.engine.cpcv import CPCVEngine, CPCVResult
from midas_backtest.engine.degraded import (
    apply_bar_noise,
    apply_credit_spread_lag,
    remove_friday_bars,
    assess_fragility,
    DegradedResult,
)

__all__ = [
    "WalkForwardEngine",
    "WalkForwardResult",
    "CPCVEngine",
    "CPCVResult",
    "apply_bar_noise",
    "apply_credit_spread_lag",
    "remove_friday_bars",
    "assess_fragility",
    "DegradedResult",
]
