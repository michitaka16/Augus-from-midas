"""
Multi-horizon signal blending — combines short, medium, and long momentum.

Hierarchy:
  Long (2-5y trend)   → sets strategic tilt (which sleeves to favor)
  Medium (6-12m)      → sets tactical allocation (relative sizing)
  Short (1-3m)        → fine-tunes (small adjustments)

Turnover penalty increases for short-horizon signals to prevent whipsaw.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# Horizon definitions (in trading days)
HORIZONS = {
    "short": {"lookback": 63, "weight": 0.20, "turnover_penalty": 2.0},    # ~3 months
    "medium": {"lookback": 189, "weight": 0.50, "turnover_penalty": 1.0},   # ~9 months
    "long": {"lookback": 504, "weight": 0.30, "turnover_penalty": 0.5},     # ~2 years
}


def blend_momentum(returns: dict[str, list[float]]) -> dict[str, float]:
    """Compute blended momentum across multiple horizons.

    Returns sleeve_id → blended momentum score.
    The blended score weights medium-horizon momentum most heavily (0.50)
    because it captures trend following without the whipsaw of short horizons
    or the staleness of very long horizons.
    """
    from midas_strategy.allocator import compute_momentum

    blended = {}
    all_sleeves = set(returns.keys())

    # Initialize to zero
    for sleeve in all_sleeves:
        blended[sleeve] = 0.0

    for horizon_name, config in HORIZONS.items():
        lookback = config["lookback"]
        weight = config["weight"]

        momentum = compute_momentum(returns, lookback=lookback)

        for sleeve, score in momentum.items():
            blended[sleeve] += score * weight

    logger.debug(
        "blending.result",
        sleeves=len(blended),
        top_sleeve=max(blended, key=blended.get) if blended else "none",
    )
    return blended


def get_horizon_turnover_penalty(horizon: str) -> float:
    """Get the turnover penalty multiplier for a given horizon.

    Short-horizon signals get 2x penalty to prevent whipsaw.
    Long-horizon signals get 0.5x (allowed to be more aggressive since they change slowly).
    """
    config = HORIZONS.get(horizon, HORIZONS["medium"])
    return config["turnover_penalty"]
