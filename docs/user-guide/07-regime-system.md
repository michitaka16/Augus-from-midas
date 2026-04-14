# 07 — The Regime System

The regime detector is the brain of Midas. It's what makes the system tactical instead of static. This chapter explains how it works in detail.

## The three regimes

| Regime | Ensemble Score | Portfolio Response |
|---|---|---|
| **Normal** | < 0.35 | Full risk-on. K=6 sleeves. Vol target enforced. |
| **Cautious** | 0.35 - 0.65 | Reduced risk. K=4 sleeves. More bonds. |
| **Turbulent** | > 0.65 | Crisis. K=0. All cash. Escalation fires. |

The regime is determined by an **8-signal weighted ensemble**. No single signal flips the regime — they vote, weighted by importance.

## The 8 signals

### 1. HY OAS (High-Yield Option-Adjusted Spread) — weight 0.25

**What it is**: The yield spread between high-yield corporate bonds and Treasuries.

**Why it matters**: Credit spreads widen BEFORE equity markets price in stress. HY OAS is a leading indicator with a typical lead time of 2-4 weeks. When lenders demand higher yield from junk borrowers, something is breaking.

**Source**: FRED series `BAMLH0A0HYM2`. In crisis onset (intraday), Midas uses HYG-IEF spread as a proxy because FRED has a 1-day publication lag.

**Normalization**:
- 300bps = 0.0 (calm, e.g., mid-2021)
- 800bps = 1.0 (crisis, e.g., March 2020)
- Linear between

### 2. VIX3M Backwardation — weight 0.20

**What it is**: The ratio of 1-month VIX to 3-month VIX (VXVCLS).

**Why it matters**: Normally, VIX is in contango — near-term vol is cheaper than further-out. When this inverts (VIX > VIX3M), the market is pricing more fear in the near-term, a strong signal of stress expectation.

**Source**: FRED `VIXCLS` / `VXVCLS`.

**Normalization**:
- 0.95 ratio = 0.0 (normal contango)
- 1.15 ratio = 1.0 (deep backwardation, crisis)

### 3. Cross-Sector PC1 Variance — weight 0.20

**What it is**: The variance of the first principal component of sector ETF returns. In practice, a simpler proxy: variance of sector returns over a short window.

**Why it matters**: In normal markets, sectors are partly uncorrelated (tech does its own thing, energy does its own thing). In crisis, correlations spike to 1 — everything sells off together. PC1 dominance signals correlation breakdown.

**Source**: Computed from XLF, XLK, XLE, XLV, XLI, etc.

**Normalization**:
- 0.3 = 0.0 (healthy sector dispersion)
- 0.7 = 1.0 (all sectors moving together, crisis)

### 4. VIX Level — weight 0.10

**What it is**: The raw VIX reading.

**Why it matters**: The classic fear gauge. Simple but can be noisy (spikes and resets quickly). Lower weight because it lags HY OAS.

**Source**: FRED `VIXCLS`.

**Normalization**:
- 15 = 0.0 (calm)
- 35 = 1.0 (elevated fear)

### 5. 200-Day SMA Persistence — weight 0.10

**What it is**: How many consecutive days SPY has been above (or below) its 200-day simple moving average.

**Why it matters**: The 200-day SMA is a trend filter used by institutional investors. Persistent moves above indicate uptrend confirmation; persistent moves below indicate bear market risk.

**Source**: Computed from SPY bars.

**Normalization**:
- +20 (days above) = 0.0 (healthy uptrend)
- -20 (days below) = 1.0 (bear market territory)

### 6. 21-Day Realized Volatility — weight 0.10

**What it is**: Annualized standard deviation of SPY daily returns over the last 21 trading days.

**Why it matters**: Fast-acting. Captures immediate stress that hasn't shown up in VIX yet.

**Source**: Computed from SPY bars.

**Normalization**:
- 10% annualized = 0.0 (calm)
- 30% annualized = 1.0 (elevated)

### 7. 3m10y Yield Curve — weight 0.05

**What it is**: The spread between 10-year Treasury yield and 3-month T-bill yield.

**Why it matters**: Yield curve inversion (negative spread) has preceded every US recession in the last 50 years. Slow-moving structural signal.

**Source**: FRED `DGS10` - `DGS3MO`.

**Normalization**:
- +1.5% (steep) = 0.0 (healthy)
- -0.5% (inverted) = 1.0 (recession risk)

### 8. (Implicit) Drawdown — hard override, not weighted

Drawdowns don't enter the ensemble score but trigger hard overrides:
- **-8% drawdown from 252-day peak** → force regime to cautious minimum
- **-12% drawdown** → force regime to turbulent

This ensures that even if the 8 ensemble signals say "normal", a real-time crash pulls the regime down. Protects against scenarios where prices move faster than the ensemble signals.

## The ensemble formula

```
score = 0.25 * norm(HY_OAS)
      + 0.20 * norm(VIX3M_backwardation)
      + 0.20 * norm(PC1_variance)
      + 0.10 * norm(VIX_level)
      + 0.10 * norm(SMA200_persistence)
      + 0.10 * norm(realized_vol_21d)
      + 0.05 * norm(yield_curve_3m10y)

# Result: 0.0 (all calm) to 1.0 (maximum stress)
```

## Hysteresis — preventing whipsaw

Without hysteresis, regime would flip every time the score crossed a threshold. This would cause the allocator to churn positions for no reason, wasting money on transaction costs.

**The rule**: the regime must be above/below a threshold for **2 consecutive days** before the regime actually transitions.

Example:
- Day 1: score = 0.32 (normal)
- Day 2: score = 0.37 (above cautious threshold — PENDING cautious)
- Day 3: score = 0.33 (back to normal — hysteresis resets, regime stays normal)

vs.

- Day 1: score = 0.32 (normal)
- Day 2: score = 0.37 (PENDING cautious)
- Day 3: score = 0.41 (confirmed cautious — regime flips)

## Deadlock override

If the score oscillates right at the threshold for 5 days without ever getting 2 consecutive days above, the hysteresis is considered stuck. At day 5, force the transition.

This prevents "stuck in limbo" scenarios during choppy markets.

## Hard overrides

Two overrides bypass the ensemble score:

### Drawdown override

Checked every tick:
```
if drawdown <= -0.12:
    regime = TURBULENT   # hard
elif drawdown <= -0.08:
    regime = max(regime, CAUTIOUS)   # soft floor
```

### Bond-as-hedge failure (PH4)

In normal times, SPY and TLT are anti-correlated (when stocks fall, bonds rally). But in stagflation or rate-shock regimes (like 2022), both fall together. This is the worst scenario for a 60/40 portfolio.

Detection: 21-day rolling correlation between SPY and TLT returns.

```
if spy_tlt_corr > +0.30:
    regime = max(regime, CAUTIOUS)
```

This override acknowledges that the standard "bonds hedge equity" assumption has failed and forces a defensive stance until the correlation normalizes.

## Regime transitions — what the user sees

### Normal → Cautious
- Banner turns yellow
- Push notification (if enabled): "Regime: Cautious"
- Next weekly signal has K=4 sleeves, more bonds
- **No emergency action**. Waits for next Sunday.

### Cautious → Turbulent
- Banner turns red, pulses
- Immediate push to all subscribers
- Signal generation triggered NOW
- Escalation timer starts (default 24h)
- If you don't respond → auto-defensive executes at timeout

### Turbulent → Cautious (recovery)
- Banner turns yellow
- Next weekly signal gradually re-enters risk
- No immediate trade

### Any → Normal
- Banner returns green
- Weekly cadence resumes

## Reading the regime panel

Click the regime banner on the Dashboard to expand:

```
Regime: Normal (score 0.28, confidence 82%)

Signal breakdown:
  HY OAS            345 bps    [normalized: 0.09]
  VIX3M backwdn.   0.92       [normalized: 0.00]
  PC1 variance      0.34       [normalized: 0.10]
  VIX level         14.2       [normalized: 0.00]
  SMA200 persist    +42 days   [normalized: 0.00]
  Realized vol      11.3%      [normalized: 0.07]
  Yield curve       +1.48%     [normalized: 0.01]

Hard overrides: none
  Drawdown from peak: -2.1% (below -8% threshold)
  SPY/TLT 21d corr: -0.31 (bonds hedging, healthy)

Hysteresis state: stable at normal for 14 days
```

**Confidence** is derived from how far the score is from the next threshold. A score of 0.15 is "very confident normal"; a score of 0.33 is "low confidence, near cautious boundary".

## Historical regime timeline

Click the Regime History link to see the last 252 trading days' regime classifications:

```
2024-04-01 to 2024-06-15:  Normal    (score range 0.18-0.31)
2024-06-16 to 2024-06-18:  Cautious  (triggered by VIX spike + HY widening)
2024-06-19 to 2024-11-02:  Normal    (score range 0.22-0.34)
...
```

This helps you understand how often the regime flips (typically 2-5 transitions per year in normal markets, more in 2008/2020-style crises).

## What you can disagree with — and how

The regime detector is deterministic. It reads the signals and computes the score. There's no ML model to "update" — if you think the signals are weighted wrong, you can argue with the system's author (me) but not with the system itself.

However, you CAN:

1. **Override at the portfolio level**: Skip a rebalance. Your portfolio stays where it is. The next signal incorporates the new state.
2. **Switch to a more conservative portfolio**: If you think the detector is being too aggressive, switch from Growth to Balanced.
3. **Go fully cash**: Unsubscribe temporarily. Come back when you're comfortable.

What you CANNOT do:
- Change the signal weights
- Add new signals
- Change the thresholds

These are system-level decisions that would require Midas to ship an update. The rationale: if users could tune these, each user would have a different regime detector, and we'd lose the backtest-live parity property that makes the system trustworthy.

## Why these specific signals?

The 8 signals were selected based on:
1. **Academic research**: Papers on regime detection, credit spreads as leading indicators
2. **Historical fit**: Which combination best predicted the 2001, 2008, 2020, 2022 drawdowns in walk-forward testing?
3. **Orthogonality**: Minimize correlation between signals (no point adding 3 VIX-like signals)
4. **Data availability**: All signals must be available daily from public sources or IBKR data

Future versions may add/remove signals, but the weights and thresholds will be recalibrated via full backtest validation.

## Known limitations

### 1. Fast flash crashes
If a crash happens in < 2 days (hysteresis window), the regime won't flip in time. The portfolio rides part of the drop before the defensive move. This is an inherent trade-off — shortening hysteresis would cause false flips in choppy markets.

### 2. Novel regimes
The signals were calibrated on 2000-2024 data. A novel regime (something unprecedented like 1929, 1974, or a black swan not seen in the training window) may not be captured cleanly. The drawdown override provides some protection but can't fully substitute for pre-flight signal updates.

### 3. Central bank intervention
When the Fed or Treasury intervenes aggressively (2020 COVID response, 2023 banking crisis), credit spreads can snap back faster than hysteresis allows. The system may stay cautious for a week or two after it's "safe" to re-enter. This is conservative, which we prefer to overreacting the other way.

### 4. Single-asset shocks
If there's a crisis specific to one sleeve (e.g., emerging market currency shock) but the ensemble signals don't pick it up, the portfolio may stay overweight that sleeve. This is a risk — we rely on momentum ranking to rotate out of such sleeves, but momentum can lag by weeks.

---

**Next**: [08 — Approving Trades](08-approvals.md)
