"""
Walk-forward validation engine.

Expanding window: train on [start, t], test on [t, t+step], advance.
Uses the SAME strategy workflow as live (via TimeSourceNode in historical mode).
Collects per-period: returns, turnover, cost drag, regime calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog

from midas_strategy.signals.time_source import TimeSource

logger = structlog.get_logger(__name__)


@dataclass
class WalkForwardPeriod:
    """Results for one test period in the walk-forward."""
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    returns: list[float]
    total_return: float
    annualized_return: float
    volatility: float
    sharpe: float
    max_drawdown: float
    turnover: float
    cost_drag: float
    regime_calls: dict[str, int]  # regime_level → count of days


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward validation results."""
    periods: list[WalkForwardPeriod]
    total_return: float
    annualized_return: float
    annualized_vol: float
    sharpe: float
    max_drawdown: float
    avg_turnover: float
    avg_cost_drag: float
    n_periods: int


class WalkForwardEngine:
    """Expanding-window walk-forward validation.

    For each test period, the strategy is given all data up to the test start
    (expanding window), then evaluated on the test period. This prevents
    look-ahead bias while testing how the strategy adapts over time.
    """

    def __init__(
        self,
        initial_train_years: int = 3,
        test_step_years: int = 1,
    ):
        self.initial_train_days = initial_train_years * 252
        self.test_step_days = test_step_years * 252

    def generate_periods(
        self,
        start: date,
        end: date,
    ) -> list[tuple[date, date, date, date]]:
        """Generate (train_start, train_end, test_start, test_end) tuples."""
        periods = []
        train_start = start
        test_start = start + timedelta(days=self.initial_train_days * 365 // 252)

        while test_start < end:
            test_end = min(
                test_start + timedelta(days=self.test_step_days * 365 // 252),
                end,
            )
            periods.append((train_start, test_start - timedelta(days=1), test_start, test_end))
            test_start = test_end + timedelta(days=1)

        logger.info(
            "walkforward.periods_generated",
            n_periods=len(periods),
            start=str(start),
            end=str(end),
        )
        return periods

    async def run(
        self,
        data_fabric: Any,
        model_portfolio_id: str,
        start: date,
        end: date,
    ) -> WalkForwardResult:
        """Run walk-forward validation over the given date range.

        For each period, instantiates the strategy workflow with a
        historical TimeSource and collects performance metrics.
        """
        from midas_strategy.signals.workflow import generate_signals
        from midas_backtest.metrics.sharpe import annualized_sharpe
        from midas_backtest.metrics.drawdown import max_drawdown_from_returns

        periods_spec = self.generate_periods(start, end)
        periods: list[WalkForwardPeriod] = []
        all_returns: list[float] = []
        old_weights: dict[str, float] = {}

        for train_start, train_end, test_start, test_end in periods_spec:
            logger.info(
                "walkforward.period.start",
                train=f"{train_start}..{train_end}",
                test=f"{test_start}..{test_end}",
            )

            # Generate signal at test_start using data up to train_end
            time_source = TimeSource.historical(train_end)
            signals = await generate_signals(
                time_source=time_source,
                data_fabric=data_fabric,
                old_weights={model_portfolio_id: old_weights},
            )

            # Find signal for this portfolio
            signal = next(
                (s for s in signals if s.model_portfolio_id == model_portfolio_id),
                None,
            )
            if not signal:
                logger.warning("walkforward.period.no_signal", portfolio=model_portfolio_id)
                continue

            # Collect test-period returns (simplified: use primary tickers)
            period_returns = await self._collect_period_returns(
                data_fabric, signal.allocation.weights, test_start, test_end,
            )

            if not period_returns:
                continue

            total_ret = 1.0
            for r in period_returns:
                total_ret *= (1 + r)
            total_ret -= 1.0

            n_days = len(period_returns)
            ann_ret = (1 + total_ret) ** (252 / max(n_days, 1)) - 1 if n_days > 0 else 0
            vol = _std(period_returns) * (252 ** 0.5) if period_returns else 0
            sharpe = annualized_sharpe(period_returns) if period_returns else 0
            mdd = max_drawdown_from_returns(period_returns)

            # Track regime calls
            regime_calls = {"normal": 0, "cautious": 0, "turbulent": 0}
            regime_calls[signal.regime.regime.value] = n_days

            period = WalkForwardPeriod(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                returns=period_returns,
                total_return=round(total_ret, 6),
                annualized_return=round(ann_ret, 6),
                volatility=round(vol, 6),
                sharpe=round(sharpe, 4),
                max_drawdown=round(mdd, 6),
                turnover=round(signal.allocation.turnover, 4),
                cost_drag=round(signal.total_cost / 100_000 if signal.total_cost else 0, 6),
                regime_calls=regime_calls,
            )
            periods.append(period)
            all_returns.extend(period_returns)
            old_weights = signal.allocation.weights

        # Aggregate
        if not all_returns:
            return WalkForwardResult(
                periods=[], total_return=0, annualized_return=0,
                annualized_vol=0, sharpe=0, max_drawdown=0,
                avg_turnover=0, avg_cost_drag=0, n_periods=0,
            )

        total = 1.0
        for r in all_returns:
            total *= (1 + r)
        total -= 1.0

        n_days = len(all_returns)
        ann_ret = (1 + total) ** (252 / max(n_days, 1)) - 1
        vol = _std(all_returns) * (252 ** 0.5)

        result = WalkForwardResult(
            periods=periods,
            total_return=round(total, 6),
            annualized_return=round(ann_ret, 6),
            annualized_vol=round(vol, 6),
            sharpe=round(annualized_sharpe(all_returns), 4),
            max_drawdown=round(max_drawdown_from_returns(all_returns), 6),
            avg_turnover=round(sum(p.turnover for p in periods) / len(periods), 4) if periods else 0,
            avg_cost_drag=round(sum(p.cost_drag for p in periods) / len(periods), 6) if periods else 0,
            n_periods=len(periods),
        )

        logger.info(
            "walkforward.complete",
            portfolio=model_portfolio_id,
            n_periods=result.n_periods,
            sharpe=result.sharpe,
            total_return=result.total_return,
        )
        return result

    async def _collect_period_returns(
        self,
        data_fabric: Any,
        weights: dict[str, float],
        start: date,
        end: date,
    ) -> list[float]:
        """Collect weighted portfolio daily returns for the test period."""
        from midas_strategy.sleeves import get_primary_tickers

        primary = get_primary_tickers()
        sleeve_bars = {}
        for sleeve_id in weights:
            ticker = primary.get(sleeve_id)
            if ticker:
                bars = await data_fabric.get_bars(ticker, start, end)
                sleeve_bars[sleeve_id] = bars

        if not sleeve_bars:
            return []

        # Find common dates across all sleeves
        all_dates = None
        date_bars = {}
        for sleeve_id, bars in sleeve_bars.items():
            date_bars[sleeve_id] = {str(b["date"]): b for b in bars}
            dates = set(date_bars[sleeve_id].keys())
            all_dates = dates if all_dates is None else all_dates & dates

        if not all_dates:
            return []

        sorted_dates = sorted(all_dates)
        portfolio_returns = []

        for i in range(1, len(sorted_dates)):
            prev_date = sorted_dates[i - 1]
            curr_date = sorted_dates[i]
            daily_return = 0.0

            for sleeve_id, weight in weights.items():
                if sleeve_id not in date_bars:
                    continue
                prev = date_bars[sleeve_id].get(prev_date, {})
                curr = date_bars[sleeve_id].get(curr_date, {})
                prev_price = float(prev.get("adj_close", prev.get("close", 0)))
                curr_price = float(curr.get("adj_close", curr.get("close", 0)))
                if prev_price > 0:
                    daily_return += weight * (curr_price - prev_price) / prev_price

            portfolio_returns.append(daily_return)

        return portfolio_returns


def _std(values: list[float]) -> float:
    """Standard deviation of a list of floats."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return var ** 0.5
