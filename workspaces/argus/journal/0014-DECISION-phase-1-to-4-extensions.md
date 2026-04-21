---
type: DECISION
date: 2026-04-21
created_at: 2026-04-21T00:00:00
author: co-authored
session_id: current
project: argus
topic: Phase 1-4 extension decisions — feature engineering, ESG benchmark, preset expansion
phase: implement
tags: [phase-1, phase-2, phase-3, phase-4, esg-screen, esgu-benchmark, presets, feature-engineering]
---

## Decision: Phase 1-4 Extension Decisions

### Feature Engineering Iteration: 10 → 9 Features

**Change**: Added `asset_class_equity` (binary) and confirmed 9-feature vector for clustering.

**Rationale**: The 10-feature vector from Phase 1 was revised in Phase 2 when `asset_class_equity` was added as a replacement/augmentation feature. The 9-dimensional feature space (country_exposure, sector_exposure, expense_ratio, volatility_252d, momentum_126d, liquidity, yield, corr_to_spy, asset_class_equity) is used for both clustering and cosine similarity calculations.

**Decision**: `asset_class_equity` is binary (0/1) and captures whether the ETF holds equities vs fixed income vs commodities. This separates bonds from equities more cleanly than any continuous feature and improves cosine similarity between same-asset-class ETFs.

### ESG Screen via ESGU Benchmark (Phase 4)

**Change**: Added 10th preset — ESG Screen — using cosine similarity to ESGU as ESG alignment proxy.

**Rationale**: MSCI ESG API is paid (~$15K/year for institutional access). As a free alternative, cosine similarity in the 9D feature space to ESGU (iShares MSCI USA ESG Select ETF) provides a reasonable proxy: ETFs with similar country/sector/exposure profiles to ESGU score high; energy and bond ETFs score low or negative.

**Thresholds**:
- GREEN: similarity ≥ 0.80 (ESGU itself, VTI, other US broad equity)
- YELLOW: 0.60 ≤ similarity < 0.80 (moderate ESG alignment)
- RED: similarity < 0.60 (XLE: -0.46, AGG: -0.16, EEM: -0.40)

**Validation**: ESGU vs VTI similarity = 0.9976 (both US broad equity ETFs — expected). ESGU vs XLE similarity = -0.4616 (energy is opposite of ESG equity — expected). ESGU vs AGG similarity = -0.1611 (bonds orthogonal to ESG equity features — expected).

**Scope limitation**: Cosine similarity to ESGU captures feature-profile similarity, not true ESG methodology. A portfolio of high-similarity-to-ESGU ETFs is not guaranteed to have high MSCI ESG scores. Commercial version should integrate MSCI or Sustainalytics API.

### 10-Preset Expansion (Phases 2-4)

**Change**: Expanded from 3 presets (Ethical Investor, Climate First, Geopolitical Screen) to 10 presets across 5 categories.

**Preset categories**: Ethical & ESG (3), Geopolitical (1), Risk & Cost (3), Sector Focus (2), Portfolio Structure (1)

**Rule engine types added**:
- `feature_threshold`: numeric comparison (volatility, yield, expense_ratio)
- `ticker_list`: explicit green/red/yellow ETF lists
- `portfolio_level`: cluster-based portfolio allocation rules
- `similarity_benchmark`: cosine similarity to a benchmark ticker

**Decision**: Each new preset fills a gap identified in user testing — low-volatility investors needed a screen, dividend-focused investors needed yield thresholds, tech-concerned investors needed sector screens. The 10-preset library provides enough variety to demonstrate the rule engine's expressiveness without overwhelming the UI.

## For Discussion

1. The ESG Screen's 0.80/0.60 thresholds are arbitrary but grounded in intuition (0.80 = strong alignment). Should these be validated against actual MSCI ESG scores if a free tier becomes available, or against expert judgment?

2. The preset expansion added 7 new presets in 3 phases. Is there a risk of preset bloat — too many choices that paralyze the user? Should presets be limited to a curated top-5 with others accessible via "Advanced" panel?

3. The `portfolio_level` rule type assumes all ETFs in a cluster are equally valid for portfolio construction. Is this assumption sound for the Core-Satellite use case, or does the ranker need to further sort within-cluster ETFs by suitability?
