# 06 — Signals Explained

A "signal" in Midas is the output of the weekly strategy run. It's the specific allocation for a model portfolio at a specific point in time.

## Anatomy of a signal

When you open the Signals page, you see the latest published signal. Here's what every field means:

```json
{
  "id": 42,
  "model_portfolio_id": "growth",
  "timestamp": "2026-04-13T23:00:00Z",
  "regime": "normal",
  "allocations": {
    "equity_sector": 0.25,
    "precious_metals": 0.15,
    "govt_bonds_long": 0.10,
    "reits": 0.10,
    "ig_corp_bonds": 0.10,
    "em_equity": 0.15,
    "dividend_etfs": 0.10,
    "commodities": 0.05
  },
  "reasoning": {
    "regime": "Normal (score 0.28, confidence 82%)",
    "allocation": "Selected 8 sleeves, vol target 14%",
    "cost": "Total rebalance cost: $4.52",
    "overrides": null,
    "fallback": null
  },
  "cost_estimate": {
    "total": 4.52,
    "commission": 2.10,
    "slippage": 1.42,
    "impact": 0.80,
    "fees": 0.20
  },
  "ensemble_score": 0.28
}
```

### `id`
Unique signal ID. When you debate this signal with the AI, citations will reference `[cite: signal_42]`.

### `model_portfolio_id`
Which of the 5 portfolios this signal is for. You only see signals for your subscribed portfolio, but all portfolios' signals are public (no user_id attached).

### `timestamp`
When the signal was generated. Signals publish Sunday 7 PM ET in normal operation. In turbulent regimes, can publish immediately upon regime flip.

### `regime`
`normal`, `cautious`, or `turbulent`. This drives the allocation pipeline:
- **normal** → K=6 top momentum sleeves
- **cautious** → K=4 top momentum sleeves
- **turbulent** → K=0 (all cash)

### `allocations`
Dict of sleeve_id → target weight. Weights are decimals (0.25 = 25%). The sum plus cash = 100%. If the sum is 0.82, cash is 18%.

### `reasoning`
Human-readable explanation. Designed for the debate agent to cite and for you to read directly. Five fields:
- `regime`: what regime was detected and how confident
- `allocation`: how many sleeves and what vol target
- `cost`: total estimated cost
- `overrides`: if any hard overrides fired (drawdown, bond hedge failure)
- `fallback`: if HRP fallback was used instead of AAA

### `cost_estimate`
Breakdown of rebalance cost:
- **commission**: IBKR tiered commission ($0.0035/share, min $0.35 per order)
- **slippage**: half-spread estimate based on liquidity tier (2bp/5bp/15bp for high/medium/low)
- **impact**: Almgren-Chriss square-root market impact
- **fees**: SEC §31 (on sells, ~$8/million) + FINRA TAF (~$0.000119/share, capped $5.95)
- **total**: sum of all components

These costs are **widened 1.5-2x in turbulent regimes** for medium-liquidity ETFs (defensive buffer).

### `ensemble_score`
The underlying regime score (0.0 to 1.0+). Thresholds:
- `< 0.35`: normal
- `0.35 - 0.65`: cautious
- `> 0.65`: turbulent

The score is the weighted sum of 8 normalized signals.

## How a signal is generated

Every signal goes through this 8-step pipeline:

### Step 1: TimeSource
The TimeSource is the ONLY thing that differs between backtest and live. In backtest mode, it's a fixed historical date. In live mode, it's the most recent market close (weekdays after 4pm ET).

Every other step in the pipeline is byte-identical between backtest and live. This is the **backtest-live parity guarantee** (ADR-005).

### Step 2: Fetch market data
From the data fabric:
- Last 600 days of adjusted OHLCV bars for every primary ticker (SPY, GLD, TLT, VNQ, LQD, VWO, etc.)
- Current regime signal values (HY OAS, VIX, yield curve) from FRED
- If intraday and regime is borderline, HYG-IEF spread from IBKR as HY OAS proxy (FRED's HY OAS has a 1-day lag)

### Step 3: Compute derived signals
Several signals are derived from bars:
- **Cross-sector PC1 variance**: variance of SPY sector returns (a proxy for correlation breakdown)
- **21-day realized volatility**: annualized std dev of SPY daily returns
- **200-day SMA persistence**: how many consecutive days SPY is above/below its 200d SMA
- **Drawdown from 252-day peak**: `(current_price - peak) / peak`
- **SPY/TLT 21-day correlation**: rolling correlation for bond-as-hedge check

### Step 4: Detect regime
The `RegimeDetector` runs the 8-signal ensemble:

```
score = 0.25 * norm(HY_OAS)
      + 0.20 * norm(VIX3M_backwardation)
      + 0.20 * norm(PC1_variance)
      + 0.10 * norm(VIX_level)
      + 0.10 * norm(SMA200_persistence)
      + 0.10 * norm(realized_vol_21d)
      + 0.05 * norm(yield_curve_3m10y)
```

Where `norm()` maps each signal to [0,1] based on historical percentiles.

Then applies:
- **Hard overrides**: drawdown ≤ -12% → turbulent; SPY/TLT corr > 0.3 → cautious
- **Hysteresis**: 2-day confirmation before switching regime
- **Deadlock override**: if stuck in hysteresis band for 5 days, force the transition

### Step 5: Compute momentum
For each of the 10 sleeves, compute 6-month total return (126 trading days):

```
momentum[sleeve] = cumulative_return(last 126 days)
```

If all sleeves are within 1% of each other, the signal is **degenerate** and the system falls back to HRP (Hierarchical Risk Parity) for this cycle.

### Step 6: Top-K selection
Based on regime:
- Normal: top 6 sleeves by momentum
- Cautious: top 4 sleeves
- Turbulent: 0 sleeves (all cash)

Income portfolio has floors: dividend_etfs ≥ 30%, ig_corp_bonds ≥ 20%, reits ≥ 15%. These sleeves are included even if their momentum is weak.

### Step 7: Optimize within selected sleeves
- **63-day rolling covariance matrix** of daily returns across selected sleeves
- **Minimum-variance weights**: `w = (Σ⁻¹ × 1) / (1' × Σ⁻¹ × 1)`, clipped to long-only (no shorts)
- **Vol-target scaling**: multiply weights by `vol_target / realized_vol`, capped at 1.0 (no leverage). Remainder goes to cash.
- **Turnover penalty**: cap weight change per sleeve to 10% per week. If a sleeve wants to go from 5% to 20%, it actually goes to 15%.

### Step 8: Write signal + inputs snapshot
The signal is written to the `signals` table.

**Critical**: All 8 signal values at the time of generation are snapshotted to `signal_inputs`. This enables the **replay job** (ADR-005) — a nightly verification that the backtest code, fed the same inputs, produces the same output. If there's drift between backtest and live, we catch it here.

The signal is marked `published=TRUE` and included in the CDN-cacheable `/signals/latest` response.

## When signals are generated

### Weekly (normal cadence)
Every Sunday 7 PM ET. The scheduler:
1. Checks if a signal for this ISO week already exists (idempotency)
2. If not, runs the full pipeline for each of the 5 portfolios
3. Writes 5 signals + 5 input snapshots in one transaction
4. Sends push notifications (if enabled) to each portfolio's subscribers

### Triggered (regime flip to turbulent)
When the regime detector flips from cautious → turbulent mid-week, the scheduler is triggered immediately. A defensive signal publishes (cash + short bonds). All subscribers are notified.

### Manual (ops only)
An ops user can trigger a manual signal generation with `scripts/generate_signals.py`. This is used during development, after a data correction, or to regenerate a signal that failed publication.

## Reading the Signals page

The Signals page shows:

### Top bar
Latest signal for your portfolio, with regime banner.

### Allocation table
Sortable by sleeve name, ticker, weight, previous weight, change. Example:

| Sleeve | Ticker | Weight | Prev | Change | Reasoning |
|---|---|---|---|---|---|
| Equity Sectors | SPY | 25% | 23% | +2% | Strong 6m momentum |
| Precious Metals | GLD | 15% | 12% | +3% | Safe haven + momentum |
| EM Equity | VWO | 15% | 18% | -3% | Reduced: cooling momentum |
| Gov Bonds (Long) | TLT | 10% | 12% | -2% | Duration trim |
| REITs | VNQ | 10% | 10% | 0% | Stable |

**Read the "Change" column**. Big positive changes = sleeves being added or grown. Big negative = reduction. Zeros = stable, no rebalance needed for this sleeve.

### Summary footer
```
Cash: 18%  |  Total cost: $4.52  |  Turnover: 8.2%
```

Turnover is the sum of absolute weight changes. If turnover is > 30%, that's an unusual signal — investigate via Debate.

## Signal history

Click "History" on the Signals page to see the last 52 weekly signals. Each row shows:
- Date
- Regime at generation
- Ensemble score
- Total cost

This is useful for checking if the system has been oscillating (too many cautious ↔ normal flips) or stable.

## What happens if a signal fails to publish?

The scheduler has strict atomicity:
- All 5 portfolios succeed → all published
- Any portfolio fails → NONE published, alert ops

The reasoning: partial publication creates inconsistency. If Growth publishes and Balanced doesn't, users start asking "why is my Balanced signal stale?" — better to fail loudly and republish once fixed.

## Signal timezone and trading calendar

- Generation timestamp: UTC in the database
- Display timestamp: user's local timezone (browser-detected)
- Trading calendar: NYSE
- Weekly cadence: Sunday 7 PM ET = Monday 00:00 UTC (roughly)

Signals never generate on market holidays. If Sunday falls on a holiday-observed weekend (rare), the signal generates on the next business day.

---

**Next**: [07 — The Regime System](07-regime-system.md)
