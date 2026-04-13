"""
Adaptive Asset Allocation (AAA) — primary allocator for Midas (ADR-004).

Pipeline: momentum ranking → top-K selection → min-variance optimization →
vol-target scaling → turnover penalty → constraint enforcement.

Fallback: HRP when momentum signal is degenerate (all sleeves within 1%).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import structlog

from midas_strategy.regime.ensemble import RegimeLevel

logger = structlog.get_logger(__name__)


# ── Portfolio Definitions ───────────────────────────────────

PORTFOLIO_VOL_TARGETS = {
    "aggressive_growth": 0.18,
    "growth": 0.14,
    "balanced": 0.10,
    "conservative": 0.06,
    "income": 0.06,
}

# Income portfolio biases toward dividend sleeves
INCOME_BIAS = {
    "dividend_etfs": 0.30,
    "ig_corp_bonds": 0.20,
    "reits": 0.15,
}

# Top-K selection per regime
TOP_K = {
    RegimeLevel.NORMAL: 6,
    RegimeLevel.CAUTIOUS: 4,
    RegimeLevel.TURBULENT: 0,  # All cash
}


@dataclass
class AllocationResult:
    """Output of the allocator."""
    weights: dict[str, float]  # sleeve_id → weight (0-1, sums to ~1)
    regime: RegimeLevel
    model_portfolio_id: str
    vol_target: float
    realized_vol: float
    turnover: float
    cash_weight: float
    selected_sleeves: list[str]
    is_fallback: bool  # True if HRP was used instead of AAA


# ── Momentum Ranking ────────────────────────────────────────

def compute_momentum(returns: dict[str, list[float]], lookback: int = 126) -> dict[str, float]:
    """Compute 6-month (126 trading days) total return per sleeve.

    Args:
        returns: sleeve_id → list of daily returns (most recent last)
        lookback: Number of trading days for momentum calculation

    Returns:
        sleeve_id → cumulative return over lookback period
    """
    momentum = {}
    for sleeve_id, daily_rets in returns.items():
        if len(daily_rets) < lookback:
            momentum[sleeve_id] = 0.0
            continue
        window = daily_rets[-lookback:]
        cum_return = 1.0
        for r in window:
            cum_return *= (1 + r)
        momentum[sleeve_id] = cum_return - 1.0
    return momentum


def select_top_k(momentum: dict[str, float], k: int) -> list[str]:
    """Select top-K sleeves by momentum. Returns sleeve IDs."""
    if k <= 0:
        return []
    sorted_sleeves = sorted(momentum.items(), key=lambda x: x[1], reverse=True)
    return [sleeve_id for sleeve_id, _ in sorted_sleeves[:k]]


def is_momentum_degenerate(momentum: dict[str, float], threshold: float = 0.01) -> bool:
    """Check if momentum signal is degenerate (all sleeves within threshold)."""
    values = list(momentum.values())
    if len(values) < 2:
        return True
    return (max(values) - min(values)) < threshold


# ── Minimum Variance Optimization ───────────────────────────

def min_variance_weights(
    cov_matrix: np.ndarray,
    sleeve_ids: list[str],
) -> dict[str, float]:
    """Compute minimum-variance portfolio weights.

    Uses closed-form solution: w = (Σ^-1 @ 1) / (1' @ Σ^-1 @ 1)
    Falls back to equal weight if covariance is singular.
    """
    n = len(sleeve_ids)
    if n == 0:
        return {}
    if n == 1:
        return {sleeve_ids[0]: 1.0}

    try:
        inv_cov = np.linalg.inv(cov_matrix)
        ones = np.ones(n)
        raw_weights = inv_cov @ ones
        total = ones @ raw_weights
        if total <= 0 or not np.isfinite(total):
            raise np.linalg.LinAlgError("Non-positive weight sum")
        weights = raw_weights / total
        # Clip negative weights to 0 (long-only constraint)
        weights = np.maximum(weights, 0.0)
        weight_sum = weights.sum()
        if weight_sum > 0:
            weights /= weight_sum
        return {sleeve_ids[i]: float(weights[i]) for i in range(n)}
    except np.linalg.LinAlgError:
        logger.warning("allocator.min_var_singular_fallback", n=n)
        equal = 1.0 / n
        return {sid: equal for sid in sleeve_ids}


def compute_covariance(returns: dict[str, list[float]], window: int = 63) -> tuple[np.ndarray, list[str]]:
    """Compute covariance matrix from daily returns (63-day rolling window).

    Returns (cov_matrix, sleeve_ids) where sleeve_ids maps column indices to sleeve IDs.
    """
    sleeve_ids = sorted(returns.keys())
    n = len(sleeve_ids)
    if n == 0:
        return np.array([[]]), []

    # Build return matrix: rows = days, cols = sleeves
    min_len = min(len(returns[sid]) for sid in sleeve_ids)
    use_len = min(min_len, window)
    if use_len < 5:
        # Not enough data — return identity (equal risk)
        return np.eye(n) * 0.0004, sleeve_ids  # ~2% daily vol

    matrix = np.zeros((use_len, n))
    for j, sid in enumerate(sleeve_ids):
        matrix[:, j] = returns[sid][-use_len:]

    cov = np.cov(matrix, rowvar=False)
    return cov, sleeve_ids


# ── Vol-Target Scaling ──────────────────────────────────────

def scale_to_vol_target(
    weights: dict[str, float],
    cov_matrix: np.ndarray,
    sleeve_ids: list[str],
    vol_target: float,
) -> tuple[dict[str, float], float]:
    """Scale portfolio weights to achieve a target annualized volatility.

    Returns (scaled_weights, cash_weight) where cash_weight fills the gap.
    """
    if not weights or vol_target <= 0:
        return weights, 0.0

    # Compute portfolio volatility
    w = np.array([weights.get(sid, 0.0) for sid in sleeve_ids])
    port_var = w @ cov_matrix @ w
    port_vol = math.sqrt(max(port_var, 0.0)) * math.sqrt(252)  # Annualize

    if port_vol <= 0:
        return weights, 0.0

    # Scale factor
    scale = vol_target / port_vol
    scale = min(scale, 1.0)  # Never lever up (long-only, no margin)

    scaled = {sid: weights.get(sid, 0.0) * scale for sid in sleeve_ids}
    invested = sum(scaled.values())
    cash = max(0.0, 1.0 - invested)

    return scaled, cash


# ── Turnover Penalty ────────────────────────────────────────

def apply_turnover_penalty(
    new_weights: dict[str, float],
    old_weights: dict[str, float],
    max_change_per_sleeve: float = 0.10,
) -> dict[str, float]:
    """Cap weight changes per sleeve to max_change_per_sleeve per week (10% default).

    This prevents excessive turnover and the associated transaction costs.
    """
    constrained = {}
    for sleeve_id, new_w in new_weights.items():
        old_w = old_weights.get(sleeve_id, 0.0)
        delta = new_w - old_w
        if abs(delta) > max_change_per_sleeve:
            constrained[sleeve_id] = old_w + math.copysign(max_change_per_sleeve, delta)
        else:
            constrained[sleeve_id] = new_w

    # Renormalize (keep cash implicit)
    total = sum(constrained.values())
    if total > 1.0:
        for sid in constrained:
            constrained[sid] /= total

    return constrained


# ── HRP Fallback ────────────────────────────────────────────

def hrp_allocate(
    cov_matrix: np.ndarray,
    sleeve_ids: list[str],
) -> dict[str, float]:
    """Hierarchical Risk Parity allocation (simplified).

    Uses inverse-variance weighting as a practical approximation of the
    full López de Prado HRP algorithm. The full implementation with
    hierarchical clustering is planned for a future iteration.
    """
    n = len(sleeve_ids)
    if n == 0:
        return {}
    if n == 1:
        return {sleeve_ids[0]: 1.0}

    # Inverse variance weighting
    variances = np.diag(cov_matrix)
    inv_var = np.where(variances > 0, 1.0 / variances, 0.0)
    total_inv_var = inv_var.sum()

    if total_inv_var <= 0:
        equal = 1.0 / n
        return {sleeve_ids[i]: equal for i in range(n)}

    weights = inv_var / total_inv_var
    return {sleeve_ids[i]: float(weights[i]) for i in range(n)}


# ── AAA Orchestrator ────────────────────────────────────────

def allocate(
    returns: dict[str, list[float]],
    regime: RegimeLevel,
    model_portfolio_id: str,
    old_weights: dict[str, float] | None = None,
    momentum_lookback: int = 126,
    cov_window: int = 63,
) -> AllocationResult:
    """Run the full Adaptive Asset Allocation pipeline.

    1. Compute momentum → rank sleeves
    2. Select top-K based on regime
    3. Min-variance optimization on selected sleeves
    4. Scale to vol-target for the portfolio
    5. Apply turnover penalty
    6. Return weights

    Falls back to HRP if momentum is degenerate.
    """
    vol_target = PORTFOLIO_VOL_TARGETS.get(model_portfolio_id, 0.10)
    old_w = old_weights or {}

    # Turbulent = all cash
    if regime == RegimeLevel.TURBULENT:
        logger.info("allocator.turbulent_cash", portfolio=model_portfolio_id)
        return AllocationResult(
            weights={},
            regime=regime,
            model_portfolio_id=model_portfolio_id,
            vol_target=vol_target,
            realized_vol=0.0,
            turnover=sum(old_w.values()),
            cash_weight=1.0,
            selected_sleeves=[],
            is_fallback=False,
        )

    # 1. Momentum
    momentum = compute_momentum(returns, lookback=momentum_lookback)

    # 2. Check for degenerate signal → HRP fallback
    use_fallback = is_momentum_degenerate(momentum)

    # 3. Covariance
    cov_matrix, cov_sleeve_ids = compute_covariance(returns, window=cov_window)

    if use_fallback:
        logger.info("allocator.hrp_fallback", reason="degenerate_momentum")
        raw_weights = hrp_allocate(cov_matrix, cov_sleeve_ids)
        selected = cov_sleeve_ids
    else:
        # Top-K selection
        k = TOP_K.get(regime, 6)
        selected = select_top_k(momentum, k)

        # Filter covariance to selected sleeves
        sel_indices = [cov_sleeve_ids.index(s) for s in selected if s in cov_sleeve_ids]
        sel_cov = cov_matrix[np.ix_(sel_indices, sel_indices)]
        sel_ids = [cov_sleeve_ids[i] for i in sel_indices]

        raw_weights = min_variance_weights(sel_cov, sel_ids)

    # 4. Income portfolio bias
    if model_portfolio_id == "income":
        for sleeve_id, bias in INCOME_BIAS.items():
            if sleeve_id in raw_weights:
                raw_weights[sleeve_id] = max(raw_weights[sleeve_id], bias)
        # Renormalize
        total = sum(raw_weights.values())
        if total > 0:
            raw_weights = {k: v / total for k, v in raw_weights.items()}

    # 5. Vol-target scaling
    # Rebuild cov for selected sleeves
    sel_ids_for_vol = sorted(raw_weights.keys())
    sel_idx = [cov_sleeve_ids.index(s) for s in sel_ids_for_vol if s in cov_sleeve_ids]
    if sel_idx:
        sel_cov_vol = cov_matrix[np.ix_(sel_idx, sel_idx)]
    else:
        sel_cov_vol = np.eye(len(sel_ids_for_vol)) * 0.0004

    scaled_weights, cash_weight = scale_to_vol_target(
        raw_weights, sel_cov_vol, sel_ids_for_vol, vol_target
    )

    # 6. Turnover penalty
    constrained = apply_turnover_penalty(scaled_weights, old_w)

    # Compute realized vol
    w_arr = np.array([constrained.get(sid, 0.0) for sid in sel_ids_for_vol])
    port_var = w_arr @ sel_cov_vol @ w_arr if len(sel_idx) > 0 else 0.0
    realized_vol = math.sqrt(max(port_var, 0.0)) * math.sqrt(252)

    # Compute turnover
    all_sleeves = set(list(constrained.keys()) + list(old_w.keys()))
    turnover = sum(abs(constrained.get(s, 0.0) - old_w.get(s, 0.0)) for s in all_sleeves)

    result = AllocationResult(
        weights={k: round(v, 6) for k, v in constrained.items() if v > 0.001},
        regime=regime,
        model_portfolio_id=model_portfolio_id,
        vol_target=vol_target,
        realized_vol=round(realized_vol, 4),
        turnover=round(turnover, 4),
        cash_weight=round(max(0, 1.0 - sum(constrained.values())), 4),
        selected_sleeves=selected,
        is_fallback=use_fallback,
    )

    logger.info(
        "allocator.result",
        portfolio=model_portfolio_id,
        regime=regime.value,
        n_sleeves=len(result.weights),
        vol=result.realized_vol,
        cash=result.cash_weight,
        turnover=result.turnover,
        fallback=result.is_fallback,
    )
    return result
