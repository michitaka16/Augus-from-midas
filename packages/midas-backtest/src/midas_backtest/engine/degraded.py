"""
Degraded-data mode — tests strategy robustness to real-world data quality issues.

Simulates: 1-day lag on credit spreads, 0.1% noise on bars, missing Friday bars.
If degraded performance drops Sharpe by > 0.15, the strategy is too fragile for live.
Run quarterly on the full backtest.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Sequence

import structlog

logger = structlog.get_logger(__name__)

SHARPE_DEGRADATION_THRESHOLD = 0.15


@dataclass
class DegradedResult:
    clean_sharpe: float
    degraded_sharpe: float
    sharpe_drop: float
    is_fragile: bool
    degradations_applied: list[str]


def apply_bar_noise(bars: list[dict], noise_pct: float = 0.001, seed: int = 42) -> list[dict]:
    """Add random noise to bar prices (simulates data provider inconsistencies)."""
    rng = random.Random(seed)
    noisy = []
    for bar in bars:
        noisy_bar = dict(bar)
        for field in ("open", "high", "low", "close", "adj_close"):
            if field in noisy_bar and noisy_bar[field]:
                val = float(noisy_bar[field])
                noise = val * rng.gauss(0, noise_pct)
                noisy_bar[field] = round(val + noise, 4)
        noisy.append(noisy_bar)
    return noisy


def apply_credit_spread_lag(
    signals: dict[str, float],
    lag_days: int = 1,
) -> dict[str, float]:
    """Simulate FRED HY OAS 1-day publication lag by zeroing the current value."""
    lagged = dict(signals)
    if "hy_oas" in lagged:
        # Replace with previous day's value (caller provides, or we use 0 as worst case)
        lagged["hy_oas"] = 0.0  # Simulates "not yet published"
    return lagged


def remove_friday_bars(bars: list[dict]) -> list[dict]:
    """Remove Friday bars to simulate missing end-of-week data."""
    filtered = []
    for bar in bars:
        bar_date = bar.get("date")
        if isinstance(bar_date, date) and bar_date.weekday() == 4:
            continue  # Skip Fridays
        filtered.append(bar)
    return filtered


def assess_fragility(clean_sharpe: float, degraded_sharpe: float) -> DegradedResult:
    """Compare clean vs degraded Sharpe to assess strategy fragility."""
    drop = clean_sharpe - degraded_sharpe
    is_fragile = drop > SHARPE_DEGRADATION_THRESHOLD

    result = DegradedResult(
        clean_sharpe=round(clean_sharpe, 4),
        degraded_sharpe=round(degraded_sharpe, 4),
        sharpe_drop=round(drop, 4),
        is_fragile=is_fragile,
        degradations_applied=["bar_noise_0.1%", "credit_spread_lag_1d", "missing_friday_bars"],
    )

    if is_fragile:
        logger.warning(
            "degraded.fragile",
            clean=clean_sharpe,
            degraded=degraded_sharpe,
            drop=drop,
        )
    else:
        logger.info(
            "degraded.robust",
            clean=clean_sharpe,
            degraded=degraded_sharpe,
            drop=drop,
        )

    return result
