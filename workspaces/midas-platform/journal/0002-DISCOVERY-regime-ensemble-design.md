---
type: DISCOVERY
date: 2026-04-12
created_at: 2026-04-12T12:05:00Z
author: agent
session_id: analyze-session-1
session_turn: 12
project: midas-platform
topic: Multi-signal regime ensemble with drawdown hard override is the right architecture
phase: analyze
tags: [strategy, regime-detection, ensemble, risk-management]
---

# Regime Detection: Why an Ensemble with Hard Override

## Finding

Research evaluated 8 candidate regime detection methods. No single signal is sufficient:
- VIX alone: too noisy, false positives in earnings season
- Trend filters (200d SMA): too late — the 2020 crash was 34% in 23 trading days
- HMM: academically elegant but opaque for the debate UX (users can't argue with hidden states)
- Credit spreads alone: leading indicator but misses equity-specific stress

The recommended design is a weighted ensemble:
| Signal | Weight | Why |
|---|---|---|
| HY OAS (credit spreads) | 0.25 | Leading indicator, 2–4 weeks ahead of equity drawdown |
| VIX3M backwardation | 0.20 | Term structure inversion signals expected future vol |
| Cross-sector PC1 variance | 0.20 | Correlation breakdown = contagion |
| VIX level | 0.10 | Classic, but noisy — low weight |
| 200d SMA persistence | 0.10 | Trend confirmation, reduces whipsaw |
| 21d realized vol | 0.10 | Fast-acting, catches immediate stress |
| 3m10y yield curve | 0.05 | Structural macro signal, slow-moving |

With a **drawdown hard override**: −8% from 252-day peak = soft halt (cautious), −12% = hard halt (turbulent, freeze trading). This backstops ensemble lag.

2-day hysteresis on regime transitions prevents oscillation at boundaries.

## Why This Matters

This ensemble IS the "don't trade without my permission in turbulent markets" requirement. If it fires too early, the user gets annoyed with false alarms. If it fires too late, they take a 20% hit before being asked. The weights and thresholds are the most important hyperparameters in the entire system — and the hardest to validate without overfitting.

## For Discussion

1. The drawdown hard override at −8%/−12% is set relative to a 252-day trailing peak. In a slowly declining market (2022-style, −25% over 9 months), the trailing peak keeps resetting. Would a fixed-window drawdown (e.g., from January 1 each year) catch the 2022 pattern earlier?
2. If VIX3M backwardation had been excluded from the ensemble (counterfactual), which of the 6 major crisis periods (2001, 2008, 2011, 2015, 2020, 2022) would the detector have missed or caught late?
3. The ensemble weights (0.25, 0.20, ...) will inevitably be tuned on historical data. How do you prevent this tuning from becoming the primary source of backtest overfitting?
