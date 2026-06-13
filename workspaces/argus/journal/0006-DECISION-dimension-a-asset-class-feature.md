---
type: DECISION
date: 2026-04-18
created_at: 2026-04-18T23:00:00+09:00
author: co-authored
session_id: 5eb02fd9-aa3a-47ba-9b00-39629aa71c7b
session_turn: 6
project: argus
topic: "Dimension A: K=5 with 9 features — asset_class_equity resolves SCHD misclassification"
phase: implement
tags: [dimension-a, feature-engineering, asset-class, schd-misclassification, k-means, clustering]
---

## Dimension A: K Selection + Feature Engineering Decision

### K=5 Selected Over K=6

K=6 silhouette (0.3884) vs K=5 silhouette (0.3818) — difference of 0.007, negligible.
Business-interpretable clusters take priority over 0.007 silhouette improvement.
"Week 5 principle" — when statistics are this close, human judgment overrides.

### asset_class_equity Feature Added

**Problem revealed**: SCHD (dividend equity ETF) classified into fixed income cluster at K=5
because its high yield (3.44%) was indistinguishable from bonds using price-derived features alone.
Yield alone cannot distinguish "high-yield equity" from "bond" — this is a genuine
feature engineering gap that pure price data cannot close.

**Fix**: Added binary `asset_class_equity` feature (1 = equity ETF, 0 = bond/commodity).
Sourced from `etf_universe.csv` metadata (23 ETFs — hardcoded is acceptable at this scale).
This is domain knowledge, not data leakage.

**Principle**: Consistent with Week 2 — "feature engineering encodes human expertise."
Investors know SCHD is equity, AGG is bonds. The algorithm shouldn't need to rediscover this.
Pure price-derived features would require 10+ years of history to converge on this distinction.

**Resulting 9-Feature Vector**:
1. country_exposure (binary: 0 or 1)
2. sector_exposure (float 0-1)
3. expense_ratio (float, %)
4. volatility_252d (float, annualized)
5. momentum_126d (float, 126d cumulative return)
6. liquidity (float, dollar_volume / AUM)
7. yield (float, dividend yield %)
8. corr_to_spy (float, 126d correlation to SPY)
9. asset_class_equity (binary: 1=equity, 0=bond/commodity/other)

### Cluster 3 Impurity Acknowledged

K=5 Cluster 3 (EEM + GLD + XLE) is economically incoherent:
EEM = emerging markets equity, GLD = gold commodity, XLE = energy sector.

**Acknowledged limitation**: With only 23 ETFs, unusual clusters can form.
Commercial version with 200+ ETFs would separate EM equity from commodities naturally
(better sector differentiation). This impurity is acceptable for the demo.

### Cosine Similarity Selected

Cosine chosen over Euclidean for within-cluster recommendations.
"Direction of exposure matters more than magnitude for ETF substitution."
VIG scored 0.94 (cosine) vs 0.61 (Euclidean) for VTI — cosine correctly
captures that VIG moves similarly to VTI at a different scale.
