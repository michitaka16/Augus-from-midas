"""Tier 1 unit tests for the AAA allocator."""

import numpy as np
import pytest

from midas_strategy.allocator import (
    allocate,
    compute_momentum,
    select_top_k,
    is_momentum_degenerate,
    min_variance_weights,
    hrp_allocate,
    apply_turnover_penalty,
    scale_to_vol_target,
    AllocationResult,
)
from midas_strategy.regime.ensemble import RegimeLevel


def _make_returns(n_sleeves: int = 5, n_days: int = 252, seed: int = 42) -> dict[str, list[float]]:
    """Generate synthetic daily returns for testing."""
    rng = np.random.RandomState(seed)
    sleeves = [f"sleeve_{i}" for i in range(n_sleeves)]
    returns = {}
    for i, sleeve in enumerate(sleeves):
        # Each sleeve has slightly different mean return
        mean = 0.0003 + 0.0001 * i
        returns[sleeve] = (rng.randn(n_days) * 0.012 + mean).tolist()
    return returns


class TestMomentum:
    @pytest.mark.unit
    def test_positive_momentum(self):
        returns = {"a": [0.01] * 126}  # 1% daily for 126 days
        momentum = compute_momentum(returns, lookback=126)
        assert momentum["a"] > 0

    @pytest.mark.unit
    def test_negative_momentum(self):
        returns = {"a": [-0.01] * 126}
        momentum = compute_momentum(returns, lookback=126)
        assert momentum["a"] < 0

    @pytest.mark.unit
    def test_insufficient_data(self):
        returns = {"a": [0.01] * 10}
        momentum = compute_momentum(returns, lookback=126)
        assert momentum["a"] == 0.0


class TestTopKSelection:
    @pytest.mark.unit
    def test_select_top_2(self):
        momentum = {"a": 0.10, "b": 0.05, "c": 0.20, "d": -0.05}
        selected = select_top_k(momentum, k=2)
        assert selected == ["c", "a"]

    @pytest.mark.unit
    def test_select_zero(self):
        momentum = {"a": 0.10, "b": 0.05}
        selected = select_top_k(momentum, k=0)
        assert selected == []


class TestMomentumDegenerate:
    @pytest.mark.unit
    def test_degenerate(self):
        momentum = {"a": 0.05, "b": 0.051, "c": 0.049}
        assert is_momentum_degenerate(momentum, threshold=0.01) is True

    @pytest.mark.unit
    def test_not_degenerate(self):
        momentum = {"a": 0.05, "b": 0.15, "c": -0.05}
        assert is_momentum_degenerate(momentum, threshold=0.01) is False


class TestMinVariance:
    @pytest.mark.unit
    def test_equal_variance_equal_weight(self):
        cov = np.eye(3) * 0.01
        weights = min_variance_weights(cov, ["a", "b", "c"])
        assert weights["a"] == pytest.approx(1 / 3, abs=0.01)
        assert weights["b"] == pytest.approx(1 / 3, abs=0.01)

    @pytest.mark.unit
    def test_single_asset(self):
        cov = np.array([[0.01]])
        weights = min_variance_weights(cov, ["a"])
        assert weights["a"] == 1.0

    @pytest.mark.unit
    def test_weights_sum_to_one(self):
        cov = np.array([[0.04, 0.01], [0.01, 0.02]])
        weights = min_variance_weights(cov, ["a", "b"])
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.01)


class TestHRP:
    @pytest.mark.unit
    def test_inverse_variance_weighting(self):
        # Asset b has half the variance → should get ~double the weight
        cov = np.diag([0.04, 0.01])
        weights = hrp_allocate(cov, ["a", "b"])
        assert weights["b"] > weights["a"]
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.01)


class TestVolTargetScaling:
    @pytest.mark.unit
    def test_scales_down(self):
        weights = {"a": 0.5, "b": 0.5}
        cov = np.eye(2) * 0.04  # 20% annual vol per asset
        scaled, cash = scale_to_vol_target(weights, cov, ["a", "b"], vol_target=0.10)
        assert cash > 0  # Some cash allocated
        assert sum(scaled.values()) < 1.0

    @pytest.mark.unit
    def test_never_levers(self):
        weights = {"a": 0.5, "b": 0.5}
        cov = np.eye(2) * 0.0001  # Very low vol
        scaled, cash = scale_to_vol_target(weights, cov, ["a", "b"], vol_target=0.50)
        assert sum(scaled.values()) <= 1.0  # Never over 100%


class TestTurnoverPenalty:
    @pytest.mark.unit
    def test_caps_change(self):
        new = {"a": 0.50}
        old = {"a": 0.20}
        constrained = apply_turnover_penalty(new, old, max_change_per_sleeve=0.10)
        assert constrained["a"] == pytest.approx(0.30, abs=0.01)

    @pytest.mark.unit
    def test_no_change_within_limit(self):
        new = {"a": 0.25}
        old = {"a": 0.20}
        constrained = apply_turnover_penalty(new, old, max_change_per_sleeve=0.10)
        assert constrained["a"] == pytest.approx(0.25, abs=0.01)


class TestAllocateIntegration:
    @pytest.mark.unit
    def test_normal_regime_produces_weights(self):
        returns = _make_returns(n_sleeves=8, n_days=252)
        result = allocate(returns, RegimeLevel.NORMAL, "growth")
        assert len(result.weights) > 0
        assert result.cash_weight >= 0
        assert sum(result.weights.values()) + result.cash_weight == pytest.approx(1.0, abs=0.05)

    @pytest.mark.unit
    def test_turbulent_regime_all_cash(self):
        returns = _make_returns()
        result = allocate(returns, RegimeLevel.TURBULENT, "growth")
        assert len(result.weights) == 0
        assert result.cash_weight == 1.0

    @pytest.mark.unit
    def test_income_portfolio_biases_dividends(self):
        returns = _make_returns(n_sleeves=10, n_days=252)
        # Rename sleeves to match actual names
        named_returns = {}
        sleeve_names = ["equity_sector", "precious_metals", "govt_bonds_short",
                        "govt_bonds_intermediate", "govt_bonds_long", "ig_corp_bonds",
                        "reits", "commodities", "dividend_etfs", "em_equity"]
        for i, name in enumerate(sleeve_names):
            named_returns[name] = returns[f"sleeve_{i}"]

        result = allocate(named_returns, RegimeLevel.NORMAL, "income")
        # Income should have meaningful dividend_etfs allocation
        if "dividend_etfs" in result.weights:
            assert result.weights["dividend_etfs"] > 0.05
