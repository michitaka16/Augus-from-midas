# 10 — Backtests & Evidence

The Backtest Explorer is where you verify that Midas works. It's not marketing — it's raw evidence with multiple overfitting checks and a mandatory benchmark gate.

## Opening the Backtest Explorer

Click **Backtests** in the left sidebar. Select a portfolio via the tabs at the top.

## What you see

### Portfolio tabs
Switch between the 5 portfolios. Each tab loads independently.

### Multi-horizon table

| Horizon | Sharpe | Max DD | Turnover | Cost Drag | Total Return |
|---|---|---|---|---|---|
| 1-Year | 1.12 | -8.2% | 142% | 0.31% | +14.2% |
| 3-Year | 0.94 | -14.1% | 128% | 0.28% | +38.7% |
| 5-Year | 0.87 | -22.3% | 119% | 0.25% | +52.1% |
| 10-Year | 0.81 | -31.2% | 112% | 0.22% | +112.5% |
| Full (26y) | 0.72 | -38.4% | 108% | 0.20% | +342.8% |

Read the columns:
- **Horizon**: lookback period
- **Sharpe**: annualized Sharpe ratio (excess return / annualized vol)
- **Max DD**: worst peak-to-trough drawdown in that horizon
- **Turnover**: annual turnover as % of portfolio (100% = entire portfolio rotated once per year)
- **Cost Drag**: annual cost drag on returns (transaction costs in %)
- **Total Return**: cumulative return over the horizon

### Key metric cards
Three cards show the headline stats:
- **Deflated Sharpe**: the Sharpe adjusted for multiple testing
- **Probability of Backtest Overfit (PBO)**: 0-100%, lower is better
- **Worst 12-Month Return**: the single worst rolling year

### Benchmark comparison
Three side-by-side comparisons:
- vs **60/40 (SPY/TLT)**: the simplest diversified portfolio
- vs **Equal Weight**: equal allocation across all 10 sleeves, rebalanced daily
- vs **VTI (Total Market)**: pure US equity

Each shows Sharpe and total return for both the Midas portfolio and the benchmark.

### View toggles
Below the tables:
- **Regime View**: break down performance by regime (normal/cautious/turbulent)
- **Sleeve View**: which sleeves contributed most to returns
- **Cost Drag**: cumulative cost drag over time

## How to read the numbers

### Sharpe Ratio

```
Sharpe = (annual return - risk-free rate) / annual volatility
```

Interpretation:
- **< 0.3**: don't ship it
- **0.3 - 0.5**: barely worth the fees
- **0.5 - 0.7**: solid, competitive with benchmarks
- **0.7 - 1.0**: very good, top-quartile
- **> 1.0**: suspicious, check for overfitting

### Deflated Sharpe

The Sharpe ratio adjusted for:
- **Number of trials**: we tested many parameter combinations during development — multiple testing inflates the observed Sharpe by chance. The Deflated Sharpe subtracts this inflation.
- **Skewness and kurtosis**: non-normal return distributions bias the Sharpe calculation.

Formula: López de Prado's Deflated Sharpe Ratio (2014).

**Rule**: if Deflated Sharpe < 0.5, the strategy likely overfit during development. Don't ship.

### PBO (Probability of Backtest Overfitting)

From Bailey, Borwein, López de Prado, Zhu (2014). Based on CPCV (Combinatorial Purged Cross-Validation):

```
1. Divide the time series into N groups (N=10)
2. Generate all C(N, N/2) = 252 combinations of "train on half, test on other half"
3. For each split, compute the test-set Sharpe
4. PBO = fraction of splits with negative OOS Sharpe
```

Interpretation:
- **PBO < 20%**: very robust
- **PBO 20-40%**: acceptable, ship with caution
- **PBO > 40%**: fails the gate, don't ship

### Max Drawdown

The worst peak-to-trough decline during the horizon.

```
Max DD = min over t of (cumulative_return[t] - max(cumulative_return[0..t])) / max(cumulative_return[0..t])
```

Reported as negative %. Example: -24% means the portfolio lost 24% from its peak at the worst point.

**Rule for you**: ask yourself honestly — could I stay invested during this drawdown? If the answer is no, pick a lower-vol portfolio.

### Max DD Duration

How long it took to recover to the previous peak. Example: a 24% drawdown that took 380 trading days (1.5 years) to recover means you were underwater for 1.5 years.

Long duration is psychologically harder than deep drawdown. 2008-2013 was a 1700-day underwater period for many portfolios.

### Turnover

Annual turnover = sum of all absolute weight changes in a year, divided by the average portfolio value.

- **< 50%**: very low, couch-potato-like
- **50-100%**: moderate, typical for tactical allocation
- **100-200%**: active, expected for Midas
- **> 300%**: too much, cost drag will kill returns

Midas Growth typically shows 100-150% turnover. Cost drag stays below 0.3% annually because we:
- Rebalance weekly, not daily
- Cap weight changes at 10%/week per sleeve
- Block illiquid rotation in turbulent regimes
- Use ETFs with tight spreads

### Cost Drag

Total annual costs (commissions + slippage + impact + fees) as % of portfolio value.

```
Cost Drag = total_annual_costs / average_portfolio_value
```

Target: below 0.3% for Growth. Income should be below 0.2% (less turnover).

### Worst 12-Month Return

The single worst rolling 12-month return in the full backtest.

This is the stress test. If the portfolio has ever lost 22% in a 12-month period, that's what you should plan for as a worst case (understanding it could be worse in an out-of-sample future crisis).

## The benchmark gate — PC2 resolution

**Mandatory rule**: every Midas portfolio MUST beat 60/40 (SPY/TLT) on Sharpe ratio, net of all costs, over the full 26-year horizon. If it doesn't, we don't ship the portfolio.

This is a hard gate. No exceptions.

Why this matters: 60/40 is the simplest portfolio anyone can build with $10 and two mouse clicks. If Midas can't beat it, there's no justification for the subscription fee. Users should just buy SPY and TLT.

### Current benchmark results (from seeded data, not real backtest)

Growth portfolio:
- Sharpe 0.72 vs 60/40 Sharpe 0.48 → BEATS ✓
- Sharpe 0.72 vs Equal Weight Sharpe 0.61 → BEATS ✓
- Sharpe 0.72 vs VTI Sharpe 0.65 → BEATS ✓

When real historical data is loaded (`scripts/load_historical.py`), these numbers will be recomputed. If any portfolio fails the 60/40 gate, it will be deprecated.

## Walk-forward validation

Walk-forward is the main evaluation method. It simulates what would have happened if you deployed the strategy in real time:

1. Train on initial 3 years (2000-2002)
2. Test on next 1 year (2003)
3. Collect returns, Sharpe, turnover, cost drag for 2003
4. Re-train on 2000-2003, test on 2004
5. Repeat until the end of the data
6. Aggregate: total return, overall Sharpe, max drawdown across all test years

This is more rigorous than a single backtest because the strategy never "sees" the test year in advance.

## CPCV (Combinatorial Purged Cross-Validation)

CPCV is López de Prado's improvement on walk-forward. Instead of one sequential train/test split, it generates many combinatorial splits:

```
N = 10 groups
Train on 5 groups, test on the other 5
All C(10, 5) = 252 possible combinations
For each: compute test Sharpe
```

Why it's better:
- Tests many possible market conditions, not just sequential ones
- Detects overfitting more reliably (if strategy only works when trained on "easy" data, CPCV catches it)
- Generates a distribution of Sharpe ratios, enabling PBO calculation

The purge + embargo (5 days, 2 days respectively) prevents leakage from rolling statistics and regime hysteresis.

## Degraded-data mode

Ran quarterly as a fragility test. Simulates real-world data quality issues:

1. Add 0.1% random noise to all bars
2. Lag HY OAS by 1 day (simulating FRED's actual lag)
3. Randomly drop Friday bars (simulating missing data)

Re-run the full backtest. If Sharpe drops by > 0.15, the strategy is flagged as fragile. Fragile strategies are reviewed and either hardened or removed.

## Replay verification

Nightly job. Takes a live-published signal's `signal_inputs` snapshot, re-runs the strategy pipeline on that exact data, compares the output to the published signal.

- Weight tolerance: 0.01% absolute per sleeve
- Cost tolerance: 1% relative

Any drift beyond tolerance → alert. This catches backtest-live parity failures before they cause real harm.

## What backtest numbers you should trust

### Trust these
- **Walk-forward Sharpe > 0.5 over 10+ years**: real evidence
- **PBO < 30%**: unlikely to be overfit
- **Beats 60/40 by > 0.15 Sharpe**: meaningful alpha
- **Degraded-data Sharpe drop < 0.15**: robust

### Don't trust these
- **Backtest Sharpe > 1.5**: too good, probably overfit or data mining
- **Walk-forward only on 2-3 years**: too short, could be lucky regime
- **Benchmark comparison only shown on pre-cost basis**: net-of-cost is the only honest comparison
- **Drawdowns < 10% over 26 years**: impossible for a real strategy, something's wrong

## When to switch portfolios based on backtests

If you see backtest evidence like:
- Portfolio A Sharpe 0.8, Max DD -30%
- Portfolio B Sharpe 0.6, Max DD -12%

And you can't stomach a 30% DD → pick B, even though A has higher Sharpe. Sharpe doesn't capture behavioral risk. You'll sell A at the bottom and underperform. B's lower Sharpe ends up winning because you actually stayed invested.

## Backtest limitations

### 1. Past performance
The old SEC disclaimer is real. 26 years covers 2001, 2008, 2020 crises, but a novel regime (1929-style, stagflation not yet modeled, etc.) may not be captured.

### 2. Cost model calibration
The cost model uses historical IBKR commissions + typical spreads. Real spreads during crises can widen beyond what the model assumes. Trades during 2020 March may have cost 2-3x the model estimate.

### 3. Survivorship bias
If the ETF universe was constructed from currently-active tickers, the backtest would be biased. Midas uses a point-in-time universe (including delisted ETFs) to eliminate this. Verify in the Backtest Explorer that the universe size varies year-over-year — in early 2000s, it should be smaller.

### 4. Sample size
10 sleeves × 26 years = ~260 sleeve-years of data. That's enough for momentum to stabilize but not enough to claim the strategy is "proven" for all future regimes.

### 5. Implementation shortfall
Real execution has slippage from the close price. The backtest uses adjusted close prices. Expect 5-20 bps per year of extra cost in real trading.

## Before you commit real money

Review these in the Backtest Explorer:

1. **Full-horizon Sharpe** > 0.5 (ideally > 0.7)
2. **Deflated Sharpe** > 0.5
3. **PBO** < 40%
4. **Beats 60/40 net-of-costs**
5. **Max Drawdown** you can personally live with
6. **Max DD Duration** you can psychologically tolerate
7. **Worst 12-month** you can stomach

If all 7 look good → commit. If any fail → pick a different portfolio or wait for Midas to deprecate the one that failed.

---

**Next**: [11 — The Audit Trail](11-audit-trail.md)
