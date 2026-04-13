"""Tier 1 unit tests for backtest metrics."""

import math

import pytest

from midas_backtest.metrics.sharpe import sharpe_ratio, annualized_sharpe, deflated_sharpe
from midas_backtest.metrics.drawdown import max_drawdown_from_returns, compute_drawdown_metrics
from midas_backtest.metrics.benchmark import benchmark_60_40, benchmark_vti


class TestSharpe:
    @pytest.mark.unit
    def test_positive_sharpe(self):
        # Varying positive returns (constant returns have zero std → Sharpe=0)
        import random
        rng = random.Random(42)
        returns = [0.001 + rng.gauss(0, 0.005) for _ in range(252)]
        sr = annualized_sharpe(returns)
        assert sr > 0

    @pytest.mark.unit
    def test_zero_returns(self):
        returns = [0.0] * 100
        sr = sharpe_ratio(returns)
        assert sr == 0.0

    @pytest.mark.unit
    def test_single_return(self):
        assert sharpe_ratio([0.01]) == 0.0

    @pytest.mark.unit
    def test_empty_returns(self):
        assert sharpe_ratio([]) == 0.0

    @pytest.mark.unit
    def test_annualized_scales_by_sqrt_252(self):
        returns = [0.001, -0.001] * 126
        daily = sharpe_ratio(returns)
        annual = annualized_sharpe(returns)
        assert annual == pytest.approx(daily * math.sqrt(252), abs=0.01)


class TestDeflatedSharpe:
    @pytest.mark.unit
    def test_high_trials_deflates(self):
        # More trials = lower deflated Sharpe (multiple testing penalty)
        dsr_few = deflated_sharpe(1.5, n_trials=5, n_observations=252)
        dsr_many = deflated_sharpe(1.5, n_trials=100, n_observations=252)
        assert dsr_few > dsr_many

    @pytest.mark.unit
    def test_zero_trials_returns_zero(self):
        assert deflated_sharpe(1.5, n_trials=0, n_observations=252) == 0.0

    @pytest.mark.unit
    def test_returns_probability(self):
        dsr = deflated_sharpe(2.0, n_trials=10, n_observations=1000)
        assert 0 <= dsr <= 1


class TestDrawdown:
    @pytest.mark.unit
    def test_no_drawdown(self):
        returns = [0.01] * 10
        assert max_drawdown_from_returns(returns) == 0.0

    @pytest.mark.unit
    def test_full_loss(self):
        returns = [-0.5]
        dd = max_drawdown_from_returns(returns)
        assert dd == pytest.approx(-0.5, abs=0.01)

    @pytest.mark.unit
    def test_recovery(self):
        # Up, down, up — drawdown should capture the down
        returns = [0.10, -0.20, 0.15]
        dd = max_drawdown_from_returns(returns)
        assert dd < 0  # There was a drawdown

    @pytest.mark.unit
    def test_drawdown_metrics_duration(self):
        # 5 days of decline
        returns = [-0.01] * 5 + [0.10]
        metrics = compute_drawdown_metrics(returns)
        assert metrics.max_drawdown_duration_days == 5

    @pytest.mark.unit
    def test_empty_returns(self):
        assert max_drawdown_from_returns([]) == 0.0


class TestBenchmarks:
    @pytest.mark.unit
    def test_60_40_blends_correctly(self):
        import random
        rng = random.Random(42)
        spy = [0.01 + rng.gauss(0, 0.005) for _ in range(100)]
        tlt = [0.005 + rng.gauss(0, 0.003) for _ in range(100)]
        result = benchmark_60_40(spy, tlt)
        assert result.sharpe > 0
        assert result.total_return > 0
        assert result.name == "60/40 (SPY/TLT)"

    @pytest.mark.unit
    def test_vti_uses_spy(self):
        spy = [0.01] * 50
        result = benchmark_vti(spy)
        assert result.total_return > 0
        assert "VTI" in result.name

    @pytest.mark.unit
    def test_empty_returns(self):
        result = benchmark_60_40([], [])
        assert result.total_return == 0
