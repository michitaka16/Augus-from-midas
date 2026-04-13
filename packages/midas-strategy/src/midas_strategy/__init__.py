"""
Midas Strategy Engine — regime detection, allocation, cost modeling, signal generation.

The strategy engine is pure computation. It reads from the data fabric
and produces signals. It NEVER imports from midas-broker or midas-debate.
"""

from midas_strategy.regime import RegimeDetector, RegimeLevel, RegimeState
from midas_strategy.cost import CostBreakdown, calculate_trade_cost, calculate_rebalance_cost
from midas_strategy.allocator import allocate, AllocationResult
from midas_strategy.signals.time_source import TimeSource
from midas_strategy.signals.workflow import generate_signals, SignalOutput

__all__ = [
    "RegimeDetector",
    "RegimeLevel",
    "RegimeState",
    "CostBreakdown",
    "calculate_trade_cost",
    "calculate_rebalance_cost",
    "allocate",
    "AllocationResult",
    "TimeSource",
    "generate_signals",
    "SignalOutput",
]
