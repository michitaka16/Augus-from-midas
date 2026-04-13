# M03 — Backtest Engine

Dependency: M02 (strategy engine provides the workflow to backtest)
Deliverable: D3
Package: `packages/midas-backtest`

## Todos

### M03-01: Build walk-forward validation engine
`packages/midas-backtest/src/midas_backtest/engine/walkforward.py`
- Expanding window: train on [start, t], test on [t, t+step], advance
- Configurable: initial train period (3y default), test step (1y default), retrain frequency
- Uses the SAME Core SDK workflow as live (via TimeSourceNode in historical mode)
- Collects per-period: returns, turnover, cost drag, regime calls

### M03-02: Build CPCV (Combinatorial Purged Cross-Validation) engine
`packages/midas-backtest/src/midas_backtest/engine/cpcv.py`
- López de Prado's CPCV: all combinatorial train/test splits with purge + embargo
- Purge window: 5 trading days (prevents look-ahead from rolling statistics)
- Embargo window: 2 trading days (prevents leakage from regime hysteresis)
- Returns distribution of Sharpe ratios across all splits

### M03-03: Build metrics suite
`packages/midas-backtest/src/midas_backtest/metrics/`
- `sharpe.py`: annualized Sharpe ratio (excess over risk-free from FRED)
- `deflated_sharpe.py`: López de Prado's Deflated Sharpe (adjusts for number of trials, skewness, kurtosis)
- `pbo.py`: Probability of Backtest Overfitting (from CPCV distribution)
- `drawdown.py`: max drawdown, max drawdown duration, underwater curve
- `regime_conditional.py`: Sharpe/return/vol split by regime (normal/cautious/turbulent)
- `cost_attribution.py`: cumulative cost drag over time (commissions, slippage, impact, gap)
- `benchmark.py`: side-by-side vs static 60/40, equal-weight 8-sleeve, VTI-only (per PC2 resolution — mandatory)
- `turnover.py`: annual turnover rate, max weekly turnover

### M03-04: Build nightly replay job
`packages/midas-backtest/src/midas_backtest/replay/`
- Takes a live signal's `signal_inputs` snapshot (from `signal_inputs` table)
- Replays the workflow with the EXACT snapshot data (not current corrected data — per TC2)
- Compares replay output to the published signal
- Tolerance: allocation weights within 0.01% absolute; cost estimate within 1%
- Variance beyond tolerance → alert

### M03-05: Build degraded-data mode
`packages/midas-backtest/src/midas_backtest/engine/degraded.py`
- Simulates data-quality issues: 1-day lag on credit spreads, 0.1% noise on bars, missing Friday bars
- Run quarterly on the full backtest
- If degraded performance drops Sharpe by > 0.15, strategy is flagged as fragile

### M03-06: Build report generator
`packages/midas-backtest/src/midas_backtest/reports/`
- JSON output: all metrics, per-period details, regime breakdown, cost attribution
- Human-readable summary (for debate agent to cite)
- Each report gets a unique `backtest_run_id` stored in `backtest_runs` table
- The debate agent cites these IDs

### M03-07: Wire backtest engine to data fabric + strategy workflow
- Backtest engine instantiates the strategy workflow with TimeSourceNode in historical mode
- Reads bars/signals from midas_data fabric (PIT universe enforced)
- Writes results to `backtest_runs` table via DataFlow

### M03-08: Run validation backtests
- 60/40 benchmark must reproduce published returns ± 50bps (sanity check)
- All 5 model portfolios backtested 2000-present
- Walk-forward + CPCV for each
- Gate: Sharpe > 0.5, PBO < 0.4, beat 60/40 net-of-costs over full horizon
- Worst 12-month rolling period documented

### M03-09: Wire backtest regression to CI
- `.github/workflows/backtest-regression.yml`: run a fixed backtest on every PR
- Compare to golden hash (deterministic given same data + same code)
- Golden hash update requires explicit approval
- PBO threshold check: any model portfolio with PBO > 0.4 fails CI

### M03-10: Test — backtest engine Tier 1 (unit)
- Walk-forward window logic
- CPCV combinatorial split generation, purge + embargo
- Each metric function against known inputs
- Replay comparison logic

### M03-11: Test — backtest engine Tier 2 (integration, real Postgres)
- Full backtest run on 2015-2020 subset: all metrics compute, report generates
- Replay job on a synthetic signal: replay matches exactly
- Degraded-data mode: noise injection works, fragility flag triggers
