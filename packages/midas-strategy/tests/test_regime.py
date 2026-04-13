"""Tier 1 unit tests for the regime detection ensemble."""

from datetime import date

import pytest

from midas_strategy.regime.ensemble import (
    RegimeDetector,
    RegimeLevel,
    HysteresisTracker,
    _normalize,
    THRESHOLD_CAUTIOUS,
    THRESHOLD_TURBULENT,
)


class TestNormalization:
    @pytest.mark.unit
    def test_hy_oas_low_is_calm(self):
        assert _normalize("hy_oas", 300) == pytest.approx(0.0, abs=0.01)

    @pytest.mark.unit
    def test_hy_oas_high_is_stress(self):
        assert _normalize("hy_oas", 800) == pytest.approx(1.0, abs=0.01)

    @pytest.mark.unit
    def test_hy_oas_mid(self):
        val = _normalize("hy_oas", 550)
        assert 0.3 < val < 0.7

    @pytest.mark.unit
    def test_vix_level_low(self):
        assert _normalize("vix_level", 12) < 0.1

    @pytest.mark.unit
    def test_vix_level_high(self):
        assert _normalize("vix_level", 40) == pytest.approx(1.0, abs=0.01)

    @pytest.mark.unit
    def test_yield_curve_inverted_is_stress(self):
        # Negative spread = inverted = stress = high normalized value
        val = _normalize("yield_curve_3m10y", -0.5)
        assert val > 0.8

    @pytest.mark.unit
    def test_yield_curve_steep_is_calm(self):
        val = _normalize("yield_curve_3m10y", 1.5)
        assert val < 0.2

    @pytest.mark.unit
    def test_clamps_to_0_1(self):
        assert _normalize("hy_oas", 0) == 0.0
        assert _normalize("hy_oas", 2000) == 1.0


class TestRegimeDetector:
    def setup_method(self):
        self.detector = RegimeDetector()

    @pytest.mark.unit
    def test_calm_signals_produce_normal(self):
        signals = {
            "hy_oas": 350,
            "vix3m_backwardation": 0.90,
            "pc1_variance": 0.35,
            "vix_level": 14,
            "sma200_persistence": 10,
            "realized_vol_21d": 12,
            "yield_curve_3m10y": 1.2,
        }
        state = self.detector.detect(signals, current_date=date(2024, 6, 15))
        assert state.regime == RegimeLevel.NORMAL

    @pytest.mark.unit
    def test_crisis_signals_produce_turbulent(self):
        signals = {
            "hy_oas": 900,
            "vix3m_backwardation": 1.2,
            "pc1_variance": 0.8,
            "vix_level": 40,
            "sma200_persistence": -30,
            "realized_vol_21d": 35,
            "yield_curve_3m10y": -0.3,
        }
        # Need 2 days for hysteresis
        state1 = self.detector.detect(signals, current_date=date(2024, 3, 1))
        state2 = self.detector.detect(signals, current_date=date(2024, 3, 2))
        assert state2.regime == RegimeLevel.TURBULENT

    @pytest.mark.unit
    def test_drawdown_hard_override(self):
        calm_signals = {
            "hy_oas": 350,
            "vix3m_backwardation": 0.90,
            "pc1_variance": 0.35,
            "vix_level": 14,
            "sma200_persistence": 10,
            "realized_vol_21d": 12,
            "yield_curve_3m10y": 1.2,
        }
        # Even with calm signals, -12% drawdown forces turbulent
        state1 = self.detector.detect(calm_signals, drawdown_from_peak=-0.12, current_date=date(2024, 3, 1))
        state2 = self.detector.detect(calm_signals, drawdown_from_peak=-0.12, current_date=date(2024, 3, 2))
        assert state2.regime == RegimeLevel.TURBULENT
        assert any("drawdown_hard_halt" in o for o in state2.overrides_active)

    @pytest.mark.unit
    def test_bond_hedge_failure_override(self):
        calm_signals = {
            "hy_oas": 350,
            "vix3m_backwardation": 0.90,
            "pc1_variance": 0.35,
            "vix_level": 14,
            "sma200_persistence": 10,
            "realized_vol_21d": 12,
            "yield_curve_3m10y": 1.2,
        }
        state = self.detector.detect(calm_signals, spy_tlt_correlation=0.4, current_date=date(2024, 3, 1))
        assert any("bond_hedge_failure" in o for o in state.overrides_active)

    @pytest.mark.unit
    def test_ensemble_score_in_range(self):
        signals = {k: 500 for k in ["hy_oas", "vix3m_backwardation", "pc1_variance",
                                      "vix_level", "sma200_persistence", "realized_vol_21d",
                                      "yield_curve_3m10y"]}
        state = self.detector.detect(signals, current_date=date(2024, 1, 1))
        assert 0.0 <= state.ensemble_score <= 1.0

    @pytest.mark.unit
    def test_nan_signal_handled(self):
        signals = {"hy_oas": float("nan")}
        state = self.detector.detect(signals, current_date=date(2024, 1, 1))
        assert state.regime in (RegimeLevel.NORMAL, RegimeLevel.CAUTIOUS, RegimeLevel.TURBULENT)


class TestHysteresis:
    @pytest.mark.unit
    def test_requires_2_days_confirmation(self):
        tracker = HysteresisTracker()
        # Day 1: pending
        result1 = tracker.apply(RegimeLevel.CAUTIOUS, date(2024, 1, 1))
        assert result1 == RegimeLevel.NORMAL  # Still normal
        # Day 2: confirmed
        result2 = tracker.apply(RegimeLevel.CAUTIOUS, date(2024, 1, 2))
        assert result2 == RegimeLevel.CAUTIOUS  # Now switched

    @pytest.mark.unit
    def test_reset_on_return_to_current(self):
        tracker = HysteresisTracker()
        tracker.apply(RegimeLevel.CAUTIOUS, date(2024, 1, 1))
        # Return to normal before confirmation
        result = tracker.apply(RegimeLevel.NORMAL, date(2024, 1, 2))
        assert result == RegimeLevel.NORMAL

    @pytest.mark.unit
    def test_deadlock_override_at_5_days(self):
        tracker = HysteresisTracker()
        # Oscillate for 5 days (never confirms)
        tracker.apply(RegimeLevel.CAUTIOUS, date(2024, 1, 1))
        tracker.apply(RegimeLevel.TURBULENT, date(2024, 1, 2))
        tracker.apply(RegimeLevel.CAUTIOUS, date(2024, 1, 3))
        tracker.apply(RegimeLevel.TURBULENT, date(2024, 1, 4))
        # Day 5: deadlock override
        result = tracker.apply(RegimeLevel.TURBULENT, date(2024, 1, 5))
        assert result == RegimeLevel.TURBULENT
