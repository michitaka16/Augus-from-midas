"""Signal generation — TimeSource + workflow."""

from midas_strategy.signals.time_source import TimeSource, TimeSourceMode
from midas_strategy.signals.workflow import generate_signals, SignalOutput

__all__ = ["TimeSource", "TimeSourceMode", "generate_signals", "SignalOutput"]
