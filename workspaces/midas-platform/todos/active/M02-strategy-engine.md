# M02 — Strategy Engine

Dependency: M01 (data fabric must provide bars + regime signals)
Deliverable: D2
Package: `packages/midas-strategy`

## Todos

### M02-01: Build 8 asset sleeve definitions
`packages/midas-strategy/src/midas_strategy/sleeves/`
- Define each sleeve: name, ETF tickers (top 2–3 per sleeve), expense ratios, liquidity tier
- Sleeves: equity_sector, precious_metals, govt_bonds_short, govt_bonds_intermediate, govt_bonds_long, ig_corp_bonds, reits, commodities, dividend_etfs, em_equity
- Note: "all durations" for govt bonds means separate sleeves for short/intermediate/long
- Liquidity tier classification (high/medium/low ADV) — used by cost model

### M02-02: Build TimeSourceNode
`packages/midas-strategy/src/midas_strategy/signals/time_source.py`
- Core SDK custom node
- Two modes: historical (accepts date parameter) and live (uses system clock, snaps to last market close)
- Interface: `get_current_date() -> date`, `get_bar_window(ticker, lookback) -> DataFrame`
- This is the ONLY variable between backtest and live. Every other node is byte-identical.
- Candidate for upstream Kailash contribution (missing primitive per 06-framework-architecture.md)

### M02-03: Build regime detection ensemble
`packages/midas-strategy/src/midas_strategy/regime/`
- `ensemble.py`: weighted combination of 8 signals
  - HY OAS (0.25) — from FRED or IBKR HYG-IEF proxy
  - VIX3M backwardation (0.20) — VIX/VIX3M ratio
  - Cross-sector PC1 variance (0.20) — PCA on sector ETF returns
  - VIX level (0.10) — raw VIXCLS
  - 200d SMA persistence (0.10) — SPY above/below 200d SMA, how many days
  - 21d realized vol (0.10) — annualized rolling std of SPY
  - 3m10y yield curve (0.05) — DGS10 - DGS3MO
- `thresholds.py`: normal (<0.35), cautious (0.35–0.65), turbulent (>0.65)
- `hysteresis.py`: 2-day confirmation before regime transition; max 5-day deadlock override (per TH1)
- `overrides.py`: drawdown hard override (−8% soft → cautious, −12% hard → turbulent); bonds-as-hedge failure override (SPY/TLT 21d corr > +0.3 → force cautious) (per PH4)
- Output: `RegimeState(regime, confidence, signal_values, overrides_active)`

### M02-04: Wire regime detector to data fabric
- Regime detector calls `midas_data.fabric.get_regime_signals(date)` for FRED data
- Calls `midas_data.fabric.get_bars(ticker, window)` for PC1, realized vol, SMA, drawdown
- Snapshot input values into `signal_inputs` table before computing (per TC2 resolution)

### M02-05: Build TransactionCostNode
`packages/midas-strategy/src/midas_strategy/cost/`
- `ibkr_commissions.py`: IBKR Pro tiered schedule (per-share for US ETFs; min/max per order)
- `regulatory_fees.py`: SEC §31 fee (rate from .env, resets periodically), FINRA TAF ($0.000119/share, cap $5.95)
- `slippage.py`: half-spread model (bid-ask spread from historical data or estimate by liquidity tier)
- `market_impact.py`: Almgren-Chriss square-root impact model (σ × √(V/ADV) × temp_impact_coeff)
- `gap_risk.py`: overnight gap estimate (historical gap distribution per liquidity tier)
- `liquidity_check.py`: widen spread + impact for low-ADV ETFs; BLOCK rotation into illiquid sleeves when regime = turbulent (per PH1)
- Combined `TransactionCostNode`: Core SDK custom node, takes (ticker, shares, direction, regime) → cost breakdown
- Same node used in backtest AND live — zero parity drift

### M02-06: Build Adaptive Asset Allocation allocator
`packages/midas-strategy/src/midas_strategy/allocator/`
- `momentum.py`: 6-month return ranking across sleeves
- `selection.py`: top-K selection (K=6 normal, K=4 cautious, K=0 turbulent → cash)
- `min_variance.py`: minimum-variance optimization within selected sleeves (covariance from 63-day rolling window)
- `vol_target.py`: scale weights to regime-conditional vol target (18% Aggressive Growth, 14% Growth, 10% Balanced, 6% Conservative, 6% Income but dividend-biased)
- `turnover_penalty.py`: L1 penalty calibrated to TransactionCostNode output
- `constraints.py`: 10-day min-hold, 10%/week max weight change per sleeve, max 1x/week rebalance
- `aaa.py`: orchestrator that chains momentum → selection → min_variance → vol_target → turnover_penalty → constraints

### M02-07: Build HRP fallback allocator
`packages/midas-strategy/src/midas_strategy/allocator/hrp.py`
- Hierarchical Risk Parity on full sleeve set
- Same vol-target scaling as AAA
- Activated when AAA momentum signal is degenerate (all sleeves within 1% of each other)

### M02-08: Build signal generation workflow
`packages/midas-strategy/src/midas_strategy/signals/workflow.py`
- Core SDK workflow: TimeSourceNode → data fetch → regime detection → allocator → cost model → signal output
- Single workflow definition, two instantiation modes (backtest vs live)
- Output: `Signal(model_portfolio_id, timestamp, allocations, reasoning, cost_estimate, regime, signal_values_snapshot)`
- 5 model portfolios generated per run (one per vol target / style)

### M02-09: Wire signal workflow to data fabric + write to signals table
- Workflow reads from midas_data fabric
- Writes completed signals to `signals` table via DataFlow (model_portfolio_id, timestamp — NO user_id)
- Writes signal_inputs snapshot to `signal_inputs` table (immutable)
- Writes regime_signals to `regime_signals` table

### M02-10: Build multi-horizon signal blending
`packages/midas-strategy/src/midas_strategy/allocator/blending.py`
- Short (1–3 month momentum), medium (6–12 month), long (2–5 year trend)
- Hierarchical blend: long sets strategic tilt, medium sets tactical, short fine-tunes
- Turnover penalty increases for short-horizon signals (prevents whipsaw)

### M02-11: Test — strategy engine Tier 1 (unit)
- Regime ensemble: each signal independently, combined scoring, hysteresis logic, override logic
- Cost model: each fee component against known values, combined node
- Allocator: momentum ranking, min-variance on synthetic covariance, vol-target scaling, constraint enforcement
- TimeSourceNode: historical mode returns correct dates, live mode snaps to market close

### M02-12: Test — strategy engine Tier 2 (integration, real Postgres)
- Full workflow execution on real 2020 data: regime must flip turbulent within 5 trading days of Feb 20
- Full workflow on 2022 data: bonds-as-hedge override must trigger
- Cost model output for known historical rebalance matches IBKR statement ± 10%
- Signal generation produces valid JSON with all required fields, no user_id
