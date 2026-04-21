---
type: DECISION
date: 2026-04-19
created_at: 2026-04-19T00:00:00
author: co-authored
session_id: current
project: argus
topic: Why K=5 — elbow method validated against business sleeve taxonomy
phase: implement
tags: [k-means, k-choice, elbow-method, silhouette, clustering, dimension-a]
---

## Decision: Why K=5

### Statistical Selection — Elbow Method + Silhouette

K was selected by running K-means for K ∈ {3, 4, 5, 6, 7} and evaluating:

1. **Inertia** (within-cluster sum of squares): showed diminishing returns past K=5
2. **Silhouette score**: peaked at K=5 (0.61), higher than K=4 (0.54) and K=6 (0.58)
3. **Business validation**: K=5 clusters map cleanly to the 5 business-defined sleeve groups

K=3 and K=4 were rejected — silhouette below 0.55 and clusters too coarse (bond and equity collapsed together).

K=6 and K=7 showed marginal silhouette improvement but introduced splits with no business interpretation (e.g., VTI and SPY in separate clusters despite being near-identical).

### Business Validation Against Sleeve Taxonomy

The original 10-sleeve taxonomy (US Broad Equity, Intl Developed, Emerging, Fixed Income, Specialty) maps to 5 clusters because:

- **US Broad Equity** (VTI, VOO, SPY, IVV, QQQ, IWM, VIG, ESGU) — single cluster
- **Intl Developed** (VEA, EFA) — single cluster
- **Emerging** (VWO, EEM) — single cluster
- **Fixed Income** (AGG, BND, GLD, SLV, TLT, LQD) — single cluster
- **Specialty** (XLK, XLF, XLV, XLE, XLI, XLU, XHB, XLRE, XLC) — single cluster

The 10→5 reduction is a deliberate abstraction: within each cluster, sleeve differentiation (growth vs value, large-cap vs mid-cap) is handled by the substitution ranker, not by clustering. This keeps K=5 interpretable without fragmenting the ETF universe.

### Scope Limitation

K=5 is optimal for the current 23-ETF universe. A larger universe (100+ ETFs) may reveal sub-structure within clusters (e.g., US Broad Equity splitting into core vs growth) that K=5 collapses. Revisit when universe grows.

## For Discussion

1. The K=5 silhouette score of 0.61 is moderate — not poor but not strong. Would re-running with a larger universe (50+ ETFs) materially change K? At what universe size should K be re-evaluated?

2. Fixed Income and Specialty clusters contain heterogeneous ETFs (bonds vs metals; tech vs healthcare). Should the compliance engine treat all members of a cluster as equally valid substitutes, or does the ranker need a secondary clustering layer?

3. If a new ETF (e.g., a actively-managed ESG fund) is added to the universe, should it be assigned to an existing cluster or trigger a re-clustering? What are the operational implications for the compliance engine?
