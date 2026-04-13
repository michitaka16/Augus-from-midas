"""
TimeSourceNode — the ONLY variable between backtest and live.

In backtest mode: accepts a date parameter, returns historical data.
In live mode: uses system clock, snaps to last market close.

Every other node in the strategy workflow is byte-identical between
backtest and live runs. This is the backtest↔live parity guarantee (ADR-005).

Candidate for upstream Kailash contribution (missing primitive per
06-framework-architecture.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any


class TimeSourceMode(str, Enum):
    HISTORICAL = "historical"
    LIVE = "live"


# NYSE market close: 4:00 PM Eastern
_NYSE_CLOSE_HOUR = 16
_NYSE_CLOSE_MINUTE = 0
# Eastern timezone offset (simplified — doesn't handle DST perfectly,
# but sufficient for snapping to last close date)
_ET_OFFSET = timezone(timedelta(hours=-5))


@dataclass
class TimeSource:
    """Provides the current date and bar windows for the strategy workflow.

    In historical mode, the date is fixed and bars come from stored data.
    In live mode, the date snaps to the most recent market close.
    """

    mode: TimeSourceMode
    _fixed_date: date | None = None

    @classmethod
    def historical(cls, dt: date) -> TimeSource:
        """Create a historical time source pinned to a specific date."""
        return cls(mode=TimeSourceMode.HISTORICAL, _fixed_date=dt)

    @classmethod
    def live(cls) -> TimeSource:
        """Create a live time source that tracks the system clock."""
        return cls(mode=TimeSourceMode.LIVE)

    def get_current_date(self) -> date:
        """Get the current date for the strategy workflow.

        Historical: returns the fixed date.
        Live: returns the most recent market close date.
        """
        if self.mode == TimeSourceMode.HISTORICAL:
            if self._fixed_date is None:
                raise ValueError("Historical mode requires a fixed date")
            return self._fixed_date

        # Live mode: snap to last market close
        now_et = datetime.now(_ET_OFFSET)
        today = now_et.date()

        # If before market close today, use yesterday
        market_close = time(_NYSE_CLOSE_HOUR, _NYSE_CLOSE_MINUTE)
        if now_et.time() < market_close:
            today = today - timedelta(days=1)

        # Skip weekends
        while today.weekday() >= 5:
            today = today - timedelta(days=1)

        return today

    def get_lookback_start(self, lookback_days: int) -> date:
        """Get the start date for a lookback window from the current date."""
        current = self.get_current_date()
        return current - timedelta(days=lookback_days)

    def get_bar_range(self, lookback_days: int) -> tuple[date, date]:
        """Get (start, end) date range for bar queries."""
        end = self.get_current_date()
        start = end - timedelta(days=lookback_days)
        return start, end

    def is_historical(self) -> bool:
        return self.mode == TimeSourceMode.HISTORICAL

    def is_live(self) -> bool:
        return self.mode == TimeSourceMode.LIVE
