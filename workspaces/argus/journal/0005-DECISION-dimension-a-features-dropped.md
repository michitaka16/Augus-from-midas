---
type: DECISION
date: 2026-04-18
created_at: 2026-04-18T22:30:00+09:00
author: co-authored
session_id: 5eb02fd9-aa3a-47ba-9b00-39629aa71c7b
session_turn: 5
project: argus
topic: "Dimension A: Drop max_drawdown, is_leveraged; keep country_exposure as binary"
phase: implement
tags: [dimension-a, feature-selection, clustering, max_drawdown, is_leveraged, country_exposure]
---

## Dimension A: Feature Drop Decisions

### A.1 — DROP `max_drawdown_252d`

**Decision**: Drop `max_drawdown_252d` from the 10-dim feature vector.

**Evidence**: r = -0.981 with `volatility_252d`. Near-perfect negative correlation — they carry identical information. High volatility ETFs necessarily have large drawdowns in the sample period; the reverse is also true.

**Action**: Remove from clustering input. Keep `volatility_252d` (positive direction, more interpretable as "risk").

**Cross-check**: Without volatility, max_drawdown would still be informative (worst-case loss). With volatility present, it adds zero new information.

---

### A.2 — DROP `is_leveraged`

**Decision**: Drop `is_leveraged` from the 10-dim feature vector.

**Evidence**: All 23 ETFs in the universe have `is_leveraged = 0`. Constant feature — provides zero discriminative power in any distance metric.

**Action**: Remove from clustering input. If leveraged ETFs (TQQQ, SQQQ, SPXL, etc.) are added to the universe, reintroduce this feature.

---

### A.3 — KEEP `country_exposure` as binary (US=1 / non-US=0)

**Decision**: Retain `country_exposure` as a binary 0/1 feature rather than a multi-country breakdown.

**Rationale**: Other features (volatility, momentum, yield, corr_to_spy) already differentiate VEA from VWO sufficiently for clustering purposes. A fine-grained country breakdown (us_pct, europe_pct, asia_em_pct, other_pct) adds clustering complexity without proportionate benefit at this stage.

**Trade-off explicitly accepted**: Crude binary loses information about geographic nuance. If this becomes a problem for clustering quality (e.g., VWO and EEM cluster with VEA despite different EM compositions), revisit.

**Scope split**: The compliance/rule engine module (separate from clustering) will use granular country breakdowns for rule evaluation (e.g., "max 10% China exposure"). Clustering does not need this granularity.

**TODO**: Commercial version uses multi-country breakdown (us_pct, europe_pct, asia_em_pct, other_pct).

---

## Resulting 8-Feature Vector

1. country_exposure (binary: 0 or 1)
2. sector_exposure (float 0-1)
3. expense_ratio (float, %)
4. volatility_252d (float, annualized std dev)
5. momentum_126d (float, 126d cumulative return)
6. liquidity (float, dollar_volume / AUM)
7. yield (float, dividend yield %)
8. corr_to_spy (float, 126d correlation to SPY)

## For Discussion

1. The r=-0.981 between volatility and max_drawdown is period-specific (SLV had a severe drawdown that coincided with high volatility). Is the feature redundant in all market regimes, or only in this sample?

2. Binary country_exposure means EEM and VWO get the same score even though EEM has higher EM Asia exposure. Should we flag this in the compliance module separately rather than trying to fix it in clustering?
