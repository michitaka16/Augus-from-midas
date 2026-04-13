"""Sharpe ratio and Deflated Sharpe ratio."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def sharpe_ratio(returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    """Daily Sharpe ratio (not annualized)."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free_rate / 252 for r in returns]
    mean = sum(excess) / len(excess)
    std = (sum((x - mean) ** 2 for x in excess) / (len(excess) - 1)) ** 0.5
    if std == 0:
        return 0.0
    return mean / std


def annualized_sharpe(returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio (daily returns × √252)."""
    return sharpe_ratio(returns, risk_free_rate) * math.sqrt(252)


def deflated_sharpe(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """López de Prado's Deflated Sharpe Ratio.

    Adjusts the observed Sharpe for:
    - Multiple testing (n_trials)
    - Non-normal returns (skewness, excess kurtosis)

    Returns the probability that the observed Sharpe exceeds
    the expected maximum Sharpe under the null hypothesis.

    DSR < 0.5 = the strategy likely overfit.
    """
    if n_trials <= 0 or n_observations <= 0:
        return 0.0

    # Expected maximum Sharpe under null (Euler-Mascheroni)
    euler_mascheroni = 0.5772156649
    expected_max_sharpe = (
        (1 - euler_mascheroni) * _inverse_normal_cdf(1 - 1 / n_trials)
        + euler_mascheroni * _inverse_normal_cdf(1 - 1 / (n_trials * math.e))
    )

    # Standard error of Sharpe estimate
    excess_kurtosis = kurtosis - 3.0
    se_sharpe = math.sqrt(
        (1 - skewness * observed_sharpe + (excess_kurtosis / 4) * observed_sharpe ** 2)
        / (n_observations - 1)
    )

    if se_sharpe <= 0:
        return 0.0

    # Test statistic
    t_stat = (observed_sharpe - expected_max_sharpe) / se_sharpe

    # Convert to probability (standard normal CDF)
    return _normal_cdf(t_stat)


def _normal_cdf(x: float) -> float:
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _inverse_normal_cdf(p: float) -> float:
    """Approximate inverse normal CDF (probit function)."""
    if p <= 0:
        return -10.0
    if p >= 1:
        return 10.0
    # Rational approximation (Abramowitz and Stegun)
    if p < 0.5:
        t = math.sqrt(-2 * math.log(p))
    else:
        t = math.sqrt(-2 * math.log(1 - p))

    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    result = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)

    if p < 0.5:
        return -result
    return result
