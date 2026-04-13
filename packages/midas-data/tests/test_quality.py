"""Tier 1 unit tests for data quality checks."""

from datetime import date

import pytest

from midas_data.quality.checks import DataQualityChecker, TradingCalendar


class TestTradingCalendar:
    """Test NYSE trading calendar."""

    def setup_method(self):
        self.cal = TradingCalendar("NYSE")

    @pytest.mark.unit
    def test_weekday_is_trading_day(self):
        # Wednesday 2024-01-03
        assert self.cal.is_trading_day(date(2024, 1, 3)) is True

    @pytest.mark.unit
    def test_saturday_not_trading_day(self):
        assert self.cal.is_trading_day(date(2024, 1, 6)) is False

    @pytest.mark.unit
    def test_sunday_not_trading_day(self):
        assert self.cal.is_trading_day(date(2024, 1, 7)) is False

    @pytest.mark.unit
    def test_new_years_day_not_trading(self):
        assert self.cal.is_trading_day(date(2024, 1, 1)) is False

    @pytest.mark.unit
    def test_christmas_not_trading(self):
        assert self.cal.is_trading_day(date(2024, 12, 25)) is False

    @pytest.mark.unit
    def test_independence_day_not_trading(self):
        assert self.cal.is_trading_day(date(2024, 7, 4)) is False

    @pytest.mark.unit
    def test_good_friday_not_trading(self):
        # Good Friday 2024 = March 29
        assert self.cal.is_trading_day(date(2024, 3, 29)) is False

    @pytest.mark.unit
    def test_mlk_day_not_trading(self):
        # MLK Day 2024 = Jan 15 (third Monday of January)
        assert self.cal.is_trading_day(date(2024, 1, 15)) is False

    @pytest.mark.unit
    def test_trading_days_range(self):
        days = self.cal.trading_days(date(2024, 1, 1), date(2024, 1, 7))
        # Jan 1 = holiday, Jan 2 = Tue, Jan 3 = Wed, Jan 4 = Thu, Jan 5 = Fri
        # Jan 6 = Sat, Jan 7 = Sun
        assert len(days) == 4
        assert date(2024, 1, 2) in days
        assert date(2024, 1, 5) in days

    @pytest.mark.unit
    def test_approximately_252_trading_days_per_year(self):
        days = self.cal.trading_days(date(2024, 1, 1), date(2024, 12, 31))
        assert 248 <= len(days) <= 254


class TestDataQualityChecker:
    """Test data quality checks."""

    def setup_method(self):
        self.checker = DataQualityChecker()

    @pytest.mark.unit
    def test_detect_gaps_finds_missing_day(self):
        bars = [
            {"date": date(2024, 1, 2), "close": 100},
            {"date": date(2024, 1, 3), "close": 101},
            # Missing Jan 4 (Thursday)
            {"date": date(2024, 1, 5), "close": 103},
        ]
        gaps = self.checker.detect_gaps("SPY", bars)
        assert date(2024, 1, 4) in gaps

    @pytest.mark.unit
    def test_detect_gaps_no_gaps(self):
        bars = [
            {"date": date(2024, 1, 2), "close": 100},
            {"date": date(2024, 1, 3), "close": 101},
            {"date": date(2024, 1, 4), "close": 102},
            {"date": date(2024, 1, 5), "close": 103},
        ]
        gaps = self.checker.detect_gaps("SPY", bars)
        assert len(gaps) == 0

    @pytest.mark.unit
    def test_detect_gaps_empty_bars(self):
        gaps = self.checker.detect_gaps("SPY", [])
        assert len(gaps) == 0

    @pytest.mark.unit
    def test_detect_bad_ticks(self):
        bars = [
            {"date": date(2024, 1, 2), "close": 100},
            {"date": date(2024, 1, 3), "close": 125},  # +25% = bad tick
        ]
        flagged = self.checker.detect_bad_ticks(bars, threshold=0.20)
        assert len(flagged) == 1
        assert flagged[0]["return"] == 0.25

    @pytest.mark.unit
    def test_detect_bad_ticks_normal_returns(self):
        bars = [
            {"date": date(2024, 1, 2), "close": 100},
            {"date": date(2024, 1, 3), "close": 101},  # +1%
            {"date": date(2024, 1, 4), "close": 99},   # -2%
        ]
        flagged = self.checker.detect_bad_ticks(bars, threshold=0.20)
        assert len(flagged) == 0

    @pytest.mark.unit
    def test_reconcile_sources_within_threshold(self):
        eodhd = [{"date": date(2024, 1, 2), "close": 100.00}]
        yahoo = [{"date": date(2024, 1, 2), "close": 100.04}]  # 0.04% diff
        disagreements = self.checker.reconcile_sources(eodhd, yahoo, threshold=0.005)
        assert len(disagreements) == 0

    @pytest.mark.unit
    def test_reconcile_sources_beyond_threshold(self):
        eodhd = [{"date": date(2024, 1, 2), "close": 100.00}]
        yahoo = [{"date": date(2024, 1, 2), "close": 101.00}]  # 1% diff
        disagreements = self.checker.reconcile_sources(eodhd, yahoo, threshold=0.005)
        assert len(disagreements) == 1
        assert disagreements[0]["pct_diff"] == pytest.approx(0.01, abs=0.001)
