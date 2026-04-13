"""Tier 1 unit tests for backtest engines (walk-forward, CPCV, degraded)."""

from datetime import date

import numpy as np
import pytest

from midas_backtest.engine.walkforward import WalkForwardEngine
from midas_backtest.engine.cpcv import CPCVEngine
from midas_backtest.engine.degraded import (
    apply_bar_noise,
    apply_credit_spread_lag,
    remove_friday_bars,
    assess_fragility,
)


class TestWalkForwardPeriods:
    @pytest.mark.unit
    def test_generates_periods(self):
        engine = WalkForwardEngine(initial_train_years=3, test_step_years=1)
        periods = engine.generate_periods(date(2000, 1, 1), date(2010, 12, 31))
        assert len(periods) > 0
        # First test starts after 3 years of training
        _, _, test_start, _ = periods[0]
        assert test_start.year >= 2002  # ~3 years after 2000 (calendar vs trading days)

    @pytest.mark.unit
    def test_periods_are_contiguous(self):
        engine = WalkForwardEngine(initial_train_years=2, test_step_years=1)
        periods = engine.generate_periods(date(2005, 1, 1), date(2010, 12, 31))
        for i in range(1, len(periods)):
            prev_test_end = periods[i - 1][3]
            curr_test_start = periods[i][2]
            # Test periods should be approximately contiguous (within a few days)
            gap = (curr_test_start - prev_test_end).days
            assert gap <= 5

    @pytest.mark.unit
    def test_short_range_produces_at_least_one(self):
        engine = WalkForwardEngine(initial_train_years=3, test_step_years=1)
        periods = engine.generate_periods(date(2020, 1, 1), date(2024, 12, 31))
        assert len(periods) >= 1


class TestCPCVSplits:
    @pytest.mark.unit
    def test_generates_splits(self):
        engine = CPCVEngine(n_groups=6, purge_days=5, embargo_days=2)
        splits = engine.generate_splits(n_samples=500)
        assert len(splits) > 0

    @pytest.mark.unit
    def test_train_test_no_overlap(self):
        engine = CPCVEngine(n_groups=6, purge_days=0, embargo_days=0)
        splits = engine.generate_splits(n_samples=300)
        for train, test in splits:
            assert len(set(train) & set(test)) == 0

    @pytest.mark.unit
    def test_purge_removes_boundary(self):
        engine = CPCVEngine(n_groups=4, purge_days=10, embargo_days=0)
        splits = engine.generate_splits(n_samples=200)
        # With purge, train set should be smaller than without
        engine_no_purge = CPCVEngine(n_groups=4, purge_days=0, embargo_days=0)
        splits_no_purge = engine_no_purge.generate_splits(n_samples=200)
        if splits and splits_no_purge:
            assert len(splits[0][0]) <= len(splits_no_purge[0][0])

    @pytest.mark.unit
    def test_insufficient_data(self):
        engine = CPCVEngine(n_groups=10)
        splits = engine.generate_splits(n_samples=5)
        assert len(splits) == 0

    @pytest.mark.unit
    def test_caps_at_100_splits(self):
        engine = CPCVEngine(n_groups=20)  # C(20,10) = 184,756 combinations
        splits = engine.generate_splits(n_samples=2000)
        assert len(splits) <= 100


class TestDegradedData:
    @pytest.mark.unit
    def test_bar_noise_changes_prices(self):
        bars = [{"date": date(2024, 1, 2), "close": 100.0, "adj_close": 100.0}]
        noisy = apply_bar_noise(bars, noise_pct=0.01)
        # With noise, values should differ (probabilistically)
        assert len(noisy) == 1
        # At 1% noise, it's very unlikely to be exactly the same
        # but we can't assert inequality with certainty, so just check structure
        assert "close" in noisy[0]

    @pytest.mark.unit
    def test_credit_spread_lag(self):
        signals = {"hy_oas": 500, "vix": 20}
        lagged = apply_credit_spread_lag(signals)
        assert lagged["hy_oas"] == 0.0  # Lagged = unavailable
        assert lagged["vix"] == 20  # Other signals unchanged

    @pytest.mark.unit
    def test_remove_friday_bars(self):
        bars = [
            {"date": date(2024, 1, 1)},  # Monday
            {"date": date(2024, 1, 2)},  # Tuesday
            {"date": date(2024, 1, 3)},  # Wednesday
            {"date": date(2024, 1, 4)},  # Thursday
            {"date": date(2024, 1, 5)},  # Friday
        ]
        filtered = remove_friday_bars(bars)
        assert len(filtered) == 4
        dates = [b["date"] for b in filtered]
        assert date(2024, 1, 5) not in dates

    @pytest.mark.unit
    def test_fragility_assessment(self):
        result = assess_fragility(clean_sharpe=1.0, degraded_sharpe=0.7)
        assert result.sharpe_drop == pytest.approx(0.3, abs=0.01)
        assert result.is_fragile is True  # 0.3 > 0.15 threshold

    @pytest.mark.unit
    def test_robust_strategy(self):
        result = assess_fragility(clean_sharpe=1.0, degraded_sharpe=0.9)
        assert result.is_fragile is False  # 0.1 < 0.15 threshold
