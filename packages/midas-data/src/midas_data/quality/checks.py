"""
Data quality checks — gap detection, bad-tick filter, reconciliation, corp action verification.

All methods are synchronous pure computation (no IO). Called by the fabric
layer after fetching data from Postgres.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Sequence

import structlog

logger = structlog.get_logger(__name__)

# ── Trading Calendar ────────────────────────────────────────

# US market holidays (fixed dates or rules)
_US_FIXED_HOLIDAYS = {
    (1, 1),    # New Year's Day
    (7, 4),    # Independence Day
    (12, 25),  # Christmas Day
}


class TradingCalendar:
    """NYSE trading calendar for gap detection."""

    def __init__(self, exchange: str = "NYSE"):
        self.exchange = exchange
        # Good Friday dates 2000-2030 (Easter-dependent, pre-computed)
        self._good_fridays: set[date] = _compute_good_fridays(2000, 2030)

    def is_trading_day(self, dt: date) -> bool:
        """Check if a date is a trading day on the exchange."""
        if dt.weekday() >= 5:  # Saturday/Sunday
            return False
        if (dt.month, dt.day) in _US_FIXED_HOLIDAYS:
            return False
        if dt in self._good_fridays:
            return False
        # Floating holidays (approximate via weekday rules)
        if _is_mlk_day(dt) or _is_presidents_day(dt) or _is_memorial_day(dt):
            return False
        if _is_labor_day(dt) or _is_thanksgiving(dt):
            return False
        return True

    def trading_days(self, start: date, end: date) -> list[date]:
        """Return all trading days in the range [start, end] inclusive."""
        days = []
        current = start
        while current <= end:
            if self.is_trading_day(current):
                days.append(current)
            current += timedelta(days=1)
        return days


def _is_mlk_day(dt: date) -> bool:
    """Third Monday of January."""
    return dt.month == 1 and dt.weekday() == 0 and 15 <= dt.day <= 21


def _is_presidents_day(dt: date) -> bool:
    """Third Monday of February."""
    return dt.month == 2 and dt.weekday() == 0 and 15 <= dt.day <= 21


def _is_memorial_day(dt: date) -> bool:
    """Last Monday of May."""
    return dt.month == 5 and dt.weekday() == 0 and dt.day >= 25


def _is_labor_day(dt: date) -> bool:
    """First Monday of September."""
    return dt.month == 9 and dt.weekday() == 0 and dt.day <= 7


def _is_thanksgiving(dt: date) -> bool:
    """Fourth Thursday of November."""
    return dt.month == 11 and dt.weekday() == 3 and 22 <= dt.day <= 28


def _compute_good_fridays(start_year: int, end_year: int) -> set[date]:
    """Compute Good Friday dates using the Anonymous Gregorian algorithm."""
    fridays = set()
    for year in range(start_year, end_year + 1):
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = (h + l - 7 * m + 114) % 31 + 1
        easter = date(year, month, day)
        good_friday = easter - timedelta(days=2)
        fridays.add(good_friday)
    return fridays


# ── Data Quality Checker ────────────────────────────────────


class DataQualityChecker:
    """Stateless data quality checks."""

    def __init__(self, calendar: TradingCalendar | None = None):
        self.calendar = calendar or TradingCalendar()

    def detect_gaps(self, ticker: str, bars: list[dict]) -> list[date]:
        """Find missing trading days in a bar series."""
        if not bars:
            return []
        bar_dates = {
            b["date"] if isinstance(b["date"], date) else date.fromisoformat(str(b["date"]))
            for b in bars
        }
        start = min(bar_dates)
        end = max(bar_dates)
        expected = set(self.calendar.trading_days(start, end))
        missing = sorted(expected - bar_dates)
        if missing:
            logger.warning(
                "quality.gaps_detected",
                ticker=ticker,
                gap_count=len(missing),
                first_gap=str(missing[0]),
                last_gap=str(missing[-1]),
            )
        return missing

    def detect_bad_ticks(self, bars: list[dict], threshold: float = 0.20) -> list[dict]:
        """Flag bars with |daily_return| > threshold."""
        flagged = []
        for i in range(1, len(bars)):
            prev_close = bars[i - 1].get("close", 0) or bars[i - 1].get("adj_close", 0)
            curr_close = bars[i].get("close", 0) or bars[i].get("adj_close", 0)
            if prev_close == 0:
                continue
            daily_return = (curr_close - prev_close) / prev_close
            if abs(daily_return) > threshold:
                flagged.append({
                    "date": bars[i].get("date"),
                    "ticker": bars[i].get("ticker", ""),
                    "return": round(daily_return, 4),
                    "prev_close": prev_close,
                    "curr_close": curr_close,
                })
        if flagged:
            logger.warning("quality.bad_ticks", count=len(flagged))
        return flagged

    def reconcile_sources(
        self,
        eodhd_bars: list[dict],
        yahoo_bars: list[dict],
        threshold: float = 0.005,
    ) -> list[dict]:
        """Find dates where EODHD and Yahoo close prices disagree beyond threshold."""
        yahoo_by_date = {}
        for b in yahoo_bars:
            d = b["date"] if isinstance(b["date"], date) else date.fromisoformat(str(b["date"]))
            yahoo_by_date[d] = b

        disagreements = []
        for b in eodhd_bars:
            d = b["date"] if isinstance(b["date"], date) else date.fromisoformat(str(b["date"]))
            yb = yahoo_by_date.get(d)
            if not yb:
                continue
            eodhd_close = float(b.get("close", 0))
            yahoo_close = float(yb.get("close", 0))
            if eodhd_close == 0:
                continue
            pct_diff = abs(eodhd_close - yahoo_close) / eodhd_close
            if pct_diff > threshold:
                disagreements.append({
                    "date": d,
                    "eodhd_close": eodhd_close,
                    "yahoo_close": yahoo_close,
                    "pct_diff": round(pct_diff, 6),
                })

        if disagreements:
            logger.warning(
                "quality.reconciliation_disagreements",
                count=len(disagreements),
                threshold=threshold,
            )
        return disagreements

    def verify_corp_actions(self, bars: list[dict], actions: list[dict]) -> list[dict]:
        """Check that adj_close reflects known splits/dividends around action dates."""
        issues = []
        action_dates = {}
        for a in actions:
            d = a["ex_date"] if isinstance(a["ex_date"], date) else date.fromisoformat(str(a["ex_date"]))
            action_dates[d] = a

        bars_by_date = {}
        for b in bars:
            d = b["date"] if isinstance(b["date"], date) else date.fromisoformat(str(b["date"]))
            bars_by_date[d] = b

        for action_date, action in action_dates.items():
            prev_date = action_date - timedelta(days=1)
            while prev_date not in bars_by_date and prev_date > action_date - timedelta(days=7):
                prev_date -= timedelta(days=1)

            if prev_date not in bars_by_date or action_date not in bars_by_date:
                continue

            prev = bars_by_date[prev_date]
            curr = bars_by_date[action_date]
            factor = float(action.get("factor", 1.0))

            if factor != 1.0 and action["action_type"] in ("split", "reverse_split"):
                expected_ratio = factor
                actual_ratio = float(curr.get("close", 1)) / float(prev.get("close", 1))
                if abs(actual_ratio - expected_ratio) / expected_ratio > 0.1:
                    adj_prev = float(prev.get("adj_close", 0))
                    adj_curr = float(curr.get("adj_close", 0))
                    if adj_prev > 0:
                        adj_ratio = adj_curr / adj_prev
                        if abs(adj_ratio - 1.0) > 0.5:
                            issues.append({
                                "date": action_date,
                                "action": action["action_type"],
                                "factor": factor,
                                "raw_ratio": round(actual_ratio, 4),
                                "adj_ratio": round(adj_ratio, 4),
                            })

        if issues:
            logger.warning("quality.corp_action_issues", count=len(issues))
        return issues
