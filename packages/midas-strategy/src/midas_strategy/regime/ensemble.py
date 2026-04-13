"""
Regime detection ensemble — weighted multi-signal detector (ADR-003).

Signals and weights (from 02-strategy-methodology.md):
  HY OAS          0.25  — leading indicator, 2-4 weeks ahead of equity drawdown
  VIX3M backwdn   0.20  — term structure inversion = expected future vol
  Cross-sector PC1 0.20  — correlation breakdown = contagion
  VIX level        0.10  — classic but noisy
  200d SMA persist 0.10  — trend confirmation
  21d realized vol 0.10  — fast-acting immediate stress
  3m10y yield curve 0.05 — structural macro, slow-moving

Hard overrides:
  Drawdown >= 8%  → force cautious
  Drawdown >= 12% → force turbulent
  SPY/TLT 21d correlation > +0.3 → force cautious (bonds-as-hedge failure, PH4)

Hysteresis: 2-day confirmation before transition; 5-day max deadlock override (TH1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RegimeLevel(str, Enum):
    NORMAL = "normal"
    CAUTIOUS = "cautious"
    TURBULENT = "turbulent"


@dataclass
class SignalValue:
    """A single signal's contribution to the ensemble."""
    name: str
    raw_value: float
    normalized: float  # 0-1, where 1 = max stress
    weight: float
    contribution: float  # normalized * weight


@dataclass
class RegimeState:
    """Output of the regime detector."""
    regime: RegimeLevel
    confidence: float
    ensemble_score: float
    signal_values: list[SignalValue]
    overrides_active: list[str]
    date: date


# ── Signal Weights ──────────────────────────────────────────

SIGNAL_WEIGHTS = {
    "hy_oas": 0.25,
    "vix3m_backwardation": 0.20,
    "pc1_variance": 0.20,
    "vix_level": 0.10,
    "sma200_persistence": 0.10,
    "realized_vol_21d": 0.10,
    "yield_curve_3m10y": 0.05,
}

# ── Normalization Thresholds ────────────────────────────────
# Each signal is normalized to [0, 1] where 1 = maximum stress.
# These thresholds are based on historical percentiles (2000-present).

_NORM = {
    "hy_oas": {"low": 300, "high": 800},          # bps: 300=calm, 800=crisis
    "vix3m_backwardation": {"low": 0.95, "high": 1.15},  # VIX/VIX3M ratio: <1=contango, >1=backwardation
    "pc1_variance": {"low": 0.3, "high": 0.7},    # PC1 fraction of total variance
    "vix_level": {"low": 15, "high": 35},          # VIX absolute level
    "sma200_persistence": {"low": -20, "high": 20},  # days below 200d SMA (negative=below)
    "realized_vol_21d": {"low": 10, "high": 30},   # annualized %
    "yield_curve_3m10y": {"low": -0.5, "high": 1.5},  # spread in %; inverted=stress
}


def _normalize(name: str, raw: float) -> float:
    """Normalize a raw signal to [0, 1] where 1 = max stress."""
    params = _NORM.get(name)
    if not params:
        return 0.5

    low, high = params["low"], params["high"]

    # Special handling: yield curve inverts (lower = more stress)
    if name == "yield_curve_3m10y":
        # Invert: low spread = high stress
        normalized = 1.0 - (raw - low) / (high - low) if high != low else 0.5
    elif name == "sma200_persistence":
        # Negative = below SMA = stress
        normalized = (low - raw) / (low - high) if low != high else 0.5
    else:
        normalized = (raw - low) / (high - low) if high != low else 0.5

    return max(0.0, min(1.0, normalized))


# ── Regime Thresholds ───────────────────────────────────────

THRESHOLD_CAUTIOUS = 0.35
THRESHOLD_TURBULENT = 0.65

# Drawdown override thresholds (from 252-day trailing peak)
DRAWDOWN_SOFT_HALT = -0.08   # → force cautious
DRAWDOWN_HARD_HALT = -0.12   # → force turbulent

# Bonds-as-hedge failure (PH4): SPY/TLT 21-day rolling correlation
BOND_HEDGE_FAILURE_THRESHOLD = 0.30


class RegimeDetector:
    """Weighted multi-signal ensemble regime detector."""

    def __init__(self):
        self._hysteresis = HysteresisTracker()

    def detect(
        self,
        signals: dict[str, float],
        drawdown_from_peak: float = 0.0,
        spy_tlt_correlation: float = -0.3,
        current_date: date | None = None,
    ) -> RegimeState:
        """Run the ensemble detector on a set of signal values.

        Args:
            signals: Dict of signal_name → raw value. Keys should match SIGNAL_WEIGHTS.
            drawdown_from_peak: Current drawdown from 252-day trailing peak (negative = loss).
            spy_tlt_correlation: 21-day rolling correlation between SPY and TLT returns.
            current_date: Date for hysteresis tracking.

        Returns:
            RegimeState with regime level, confidence, and all signal details.
        """
        dt = current_date or date.today()

        # 1. Normalize and weight each signal
        signal_values = []
        ensemble_score = 0.0

        for name, weight in SIGNAL_WEIGHTS.items():
            raw = signals.get(name, 0.0)
            if raw is None or (isinstance(raw, float) and not math.isfinite(raw)):
                raw = 0.0
                logger.warning("regime.signal_invalid", signal=name, raw_value=raw)

            normalized = _normalize(name, raw)
            contribution = normalized * weight
            ensemble_score += contribution

            signal_values.append(SignalValue(
                name=name,
                raw_value=raw,
                normalized=round(normalized, 4),
                weight=weight,
                contribution=round(contribution, 4),
            ))

        # 2. Determine raw regime from ensemble score
        if ensemble_score >= THRESHOLD_TURBULENT:
            raw_regime = RegimeLevel.TURBULENT
        elif ensemble_score >= THRESHOLD_CAUTIOUS:
            raw_regime = RegimeLevel.CAUTIOUS
        else:
            raw_regime = RegimeLevel.NORMAL

        # 3. Apply hard overrides
        overrides = []

        if drawdown_from_peak <= DRAWDOWN_HARD_HALT:
            raw_regime = RegimeLevel.TURBULENT
            overrides.append(f"drawdown_hard_halt({drawdown_from_peak:.1%})")
        elif drawdown_from_peak <= DRAWDOWN_SOFT_HALT:
            if raw_regime == RegimeLevel.NORMAL:
                raw_regime = RegimeLevel.CAUTIOUS
            overrides.append(f"drawdown_soft_halt({drawdown_from_peak:.1%})")

        if spy_tlt_correlation > BOND_HEDGE_FAILURE_THRESHOLD:
            if raw_regime == RegimeLevel.NORMAL:
                raw_regime = RegimeLevel.CAUTIOUS
            overrides.append(f"bond_hedge_failure(corr={spy_tlt_correlation:.2f})")

        # 4. Apply hysteresis (2-day confirmation, 5-day deadlock override)
        final_regime = self._hysteresis.apply(raw_regime, dt)

        # 5. Compute confidence
        if final_regime == RegimeLevel.TURBULENT:
            confidence = min(1.0, ensemble_score / THRESHOLD_TURBULENT)
        elif final_regime == RegimeLevel.CAUTIOUS:
            confidence = min(1.0, (ensemble_score - THRESHOLD_CAUTIOUS) / (THRESHOLD_TURBULENT - THRESHOLD_CAUTIOUS))
        else:
            confidence = 1.0 - (ensemble_score / THRESHOLD_CAUTIOUS) if THRESHOLD_CAUTIOUS > 0 else 1.0

        state = RegimeState(
            regime=final_regime,
            confidence=round(max(0.0, min(1.0, confidence)), 3),
            ensemble_score=round(ensemble_score, 4),
            signal_values=signal_values,
            overrides_active=overrides,
            date=dt,
        )

        logger.info(
            "regime.detected",
            regime=state.regime.value,
            score=state.ensemble_score,
            confidence=state.confidence,
            overrides=overrides,
            date=str(dt),
        )
        return state


class HysteresisTracker:
    """Prevents regime oscillation at boundaries.

    2-day confirmation: regime must persist for 2 consecutive days before switching.
    5-day deadlock override: if stuck in hysteresis band > 5 days, force transition (TH1).
    """

    def __init__(self):
        self._current_regime: RegimeLevel = RegimeLevel.NORMAL
        self._pending_regime: RegimeLevel | None = None
        self._pending_days: int = 0
        self._hysteresis_days: int = 0

    CONFIRMATION_DAYS = 2
    MAX_HYSTERESIS_DAYS = 5

    def apply(self, raw_regime: RegimeLevel, dt: date) -> RegimeLevel:
        """Apply hysteresis to a raw regime detection."""
        if raw_regime == self._current_regime:
            # No change — reset pending
            self._pending_regime = None
            self._pending_days = 0
            self._hysteresis_days = 0
            return self._current_regime

        # Raw regime differs from current
        if raw_regime == self._pending_regime:
            self._pending_days += 1
            self._hysteresis_days += 1
        else:
            self._pending_regime = raw_regime
            self._pending_days = 1
            self._hysteresis_days += 1

        # Check confirmation threshold
        if self._pending_days >= self.CONFIRMATION_DAYS:
            old = self._current_regime
            self._current_regime = raw_regime
            self._pending_regime = None
            self._pending_days = 0
            self._hysteresis_days = 0
            logger.info(
                "regime.transition",
                from_regime=old.value,
                to_regime=raw_regime.value,
                confirmation_days=self.CONFIRMATION_DAYS,
            )
            return self._current_regime

        # Check deadlock override (TH1)
        if self._hysteresis_days >= self.MAX_HYSTERESIS_DAYS:
            old = self._current_regime
            self._current_regime = raw_regime
            self._pending_regime = None
            self._pending_days = 0
            self._hysteresis_days = 0
            logger.warning(
                "regime.deadlock_override",
                from_regime=old.value,
                to_regime=raw_regime.value,
                stuck_days=self.MAX_HYSTERESIS_DAYS,
            )
            return self._current_regime

        # Still in hysteresis — keep current
        return self._current_regime
