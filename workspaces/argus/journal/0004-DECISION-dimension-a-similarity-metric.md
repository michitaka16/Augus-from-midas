---
type: DECISION
date: 2026-04-18
created_at: 2026-04-18T21:00:00+09:00
author: co-authored
session_id: 5eb02fd9-aa3a-47ba-9b00-39629aa71c7b
session_turn: 2
project: argus
topic: Dimension A — Similarity metric and feature count deferred to empirical evaluation
phase: todos
tags: [similarity-metric, cosine-vs-euclidean, feature-selection, ml-design, dimension-a]
---

## Decision: Defer Cosine vs Euclidean and Feature Count to Empirical Evaluation

Two ML design questions raised by the red team and ML specialist are **intentionally not resolved now**. They will be decided during implementation based on clustering quality results.

### Dimension A.1: Similarity Metric — Cosine vs Euclidean

**ML specialist objection**: Cosine similarity is magnitude-invariant. Two ETFs pointing in the same direction but different scale (e.g., high-yield bond ETF vs investment-grade bond ETF) could score 0.95 similarity despite very different risk profiles.

**Counter-argument**: Cosine measures directional alignment — which is exactly what sector/country exposure features capture. Euclidean on z-scored features penalizes absolute magnitude differences that may be noise.

**Decision rule**: Implement cosine similarity first. If silhouette scores are below 0.4, re-run with Euclidean distance on z-scored features. Compare and select based on empirical silhouette improvement.

**Logging**: Will be recorded as Dimension A.1 in decision log.

### Dimension A.2: Feature Count — 10 vs 7

**ML specialist view**: Only 7 computed features are meaningful from existing data (country, sector, volatility, momentum, liquidity, drawdown, corr_spy). The other 3 (expense_ratio, yield, avg_volume) are static metadata that add noise.

**Counter-argument**: expense_ratio and yield ARE meaningful signals (cheap passive vs expensive active; high-yield vs growth). avg_volume captures liquidity in a way that dollar-volume does not without the AUM normalization.

**Decision rule**: Start with all 10 features. Run clustering with 10 and with 7 (drop expense_ratio, yield, avg_volume). If silhouette scores improve by >0.05 when dropping, drop them. Otherwise keep all 10.

**Logging**: Will be recorded as Dimension A.2 in decision log.

## For Discussion

1. Is there a principled reason to prefer one metric over the other given the ETF domain (directional alignment vs magnitude difference)? The economic interpretation differs: cosine says "behaves similarly in direction"; Euclidean says "has similar risk/return magnitude."

2. For Dimension A.2: should we use statistical significance (ANOVA F-test) to decide which features to keep rather than silhouette score alone? Features that don't discriminate across clusters even if they improve silhouette might be masking real structure.
