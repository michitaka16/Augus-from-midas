"""Tier 1 unit tests for the transaction cost model."""

import pytest

from midas_strategy.cost import (
    ibkr_commission,
    sec_fee,
    finra_taf,
    slippage_cost,
    market_impact,
    gap_risk_cost,
    check_liquidity,
    calculate_trade_cost,
    calculate_rebalance_cost,
)


class TestIBKRCommission:
    @pytest.mark.unit
    def test_minimum_commission(self):
        # 10 shares × $0.0035 = $0.035 → min $0.35
        assert ibkr_commission(10) == 0.35

    @pytest.mark.unit
    def test_standard_commission(self):
        # 1000 shares × $0.0035 = $3.50
        assert ibkr_commission(1000) == 3.50

    @pytest.mark.unit
    def test_large_order(self):
        assert ibkr_commission(10000) == 35.0


class TestRegulatoryFees:
    @pytest.mark.unit
    def test_sec_fee_on_sell(self):
        # $100,000 sale × $8.00/million = $0.80
        fee = sec_fee(100_000)
        assert fee == pytest.approx(0.80, abs=0.01)

    @pytest.mark.unit
    def test_sec_fee_zero_on_buy(self):
        assert sec_fee(0) == 0.0

    @pytest.mark.unit
    def test_finra_taf(self):
        # 10000 shares × $0.000119 = $1.19
        assert finra_taf(10000) == pytest.approx(1.19, abs=0.01)

    @pytest.mark.unit
    def test_finra_taf_cap(self):
        # Very large: should cap at $5.95
        assert finra_taf(100_000) == 5.95


class TestSlippage:
    @pytest.mark.unit
    def test_high_liquidity(self):
        # $100 × 1000 shares × 0.0002 = $20
        cost = slippage_cost(100.0, 1000, "high")
        assert cost == pytest.approx(20.0, abs=0.01)

    @pytest.mark.unit
    def test_medium_liquidity_higher(self):
        cost_high = slippage_cost(100.0, 1000, "high")
        cost_medium = slippage_cost(100.0, 1000, "medium")
        assert cost_medium > cost_high


class TestMarketImpact:
    @pytest.mark.unit
    def test_zero_volume(self):
        assert market_impact(100, 100, 0, 0.015) == 0.0

    @pytest.mark.unit
    def test_small_trade_low_impact(self):
        # 100 shares in 10M ADV = tiny participation
        impact = market_impact(100.0, 100, 10_000_000, 0.015)
        assert impact < 1.0

    @pytest.mark.unit
    def test_large_trade_higher_impact(self):
        small = market_impact(100.0, 100, 1_000_000, 0.015)
        large = market_impact(100.0, 10000, 1_000_000, 0.015)
        assert large > small


class TestLiquidityCheck:
    @pytest.mark.unit
    def test_high_liquidity_always_allowed(self):
        allowed, _ = check_liquidity("SPY", "turbulent", "high")
        assert allowed is True

    @pytest.mark.unit
    def test_low_liquidity_blocked_in_turbulent(self):
        allowed, reason = check_liquidity("TINY", "turbulent", "low")
        assert allowed is False
        assert "blocked" in reason.lower()

    @pytest.mark.unit
    def test_low_liquidity_allowed_in_normal(self):
        allowed, _ = check_liquidity("TINY", "normal", "low")
        assert allowed is True


class TestCombinedCost:
    @pytest.mark.unit
    def test_buy_trade_no_sec_fee(self):
        cost = calculate_trade_cost("SPY", 100, "buy", 450.0)
        assert cost.sec_fee == 0.0
        assert cost.finra_taf == 0.0
        assert cost.total > 0

    @pytest.mark.unit
    def test_sell_trade_includes_sec_fee(self):
        cost = calculate_trade_cost("SPY", 100, "sell", 450.0)
        assert cost.sec_fee > 0
        assert cost.finra_taf > 0

    @pytest.mark.unit
    def test_turbulent_regime_widens_spread(self):
        normal = calculate_trade_cost("DJP", 100, "buy", 25.0, regime="normal", liquidity_tier="medium")
        turbulent = calculate_trade_cost("DJP", 100, "buy", 25.0, regime="turbulent", liquidity_tier="medium")
        assert turbulent.slippage > normal.slippage

    @pytest.mark.unit
    def test_zero_shares_returns_zero(self):
        cost = calculate_trade_cost("SPY", 0, "buy", 450.0)
        assert cost.total == 0.0


class TestRebalanceCost:
    @pytest.mark.unit
    def test_multiple_trades(self):
        trades = [
            {"ticker": "SPY", "shares": 100, "direction": "buy", "price": 450.0},
            {"ticker": "TLT", "shares": 50, "direction": "sell", "price": 95.0},
        ]
        breakdowns, total = calculate_rebalance_cost(trades, regime="normal")
        assert len(breakdowns) == 2
        assert total > 0
        assert total == pytest.approx(sum(b.total for b in breakdowns), abs=0.01)
