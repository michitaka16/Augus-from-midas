---
type: DECISION
date: 2026-04-19
created_at: 2026-04-19T00:00:00
author: co-authored
session_id: current
project: argus
topic: Why K-means — centroid clustering over density and probabilistic alternatives
phase: implement
tags: [k-means, gmm, dbscan, clustering-algorithm, dimension-a]
---

## Decision: Why K-Means (Not GMM, Not DBSCAN)

### Candidate Algorithms Considered

1. **K-means** — Centroid-based, assigns each point to nearest mean
2. **GMM (Gaussian Mixture Models)** — Probabilistic, assigns soft membership probabilities
3. **DBSCAN** — Density-based, discovers clusters of arbitrary shape

### K-Means Selected

**Transductive framing**: The goal is taxonomic validation, not discovery. As established in `0001-DISCOVERY-sleeve-taxonomy-is-the-clustering-algorithm.md`, the sleeve taxonomy (10 sleeves) is the domain prior. K-means with K equal to the sleeve count checks whether empirical data matches expert priors — not whether unknown structure exists.

**Interpretability**: Cluster centroids map directly to sleeve priors. The user can see "the average ETF in the growth-tech cluster" and compare it to the sleeve definition. GMM means are similar but membership is probabilistic — an ETF can partially belong to two clusters — which complicates substitution logic.

**ETF universe size**: With 23 ETFs, density-based methods (DBSCAN) are unreliable. DBSCAN requires a meaningful density parameter (eps) that cannot be robustly estimated at N=23. K-means is stable at small N.

**Implementation simplicity**: K-means converges reliably and quickly. GMM requires careful initialization (EM can converge to local optima) and adds complexity without proportional benefit for this use case.

**GMM rejected**: Soft membership is appealing in theory but creates ambiguous substitution logic ("show me ETFs similar to SPY" — should a borderline ETF appear in both clusters?). The 23-ETF scale makes probabilistic membership noise rather than signal.

**DBSCAN rejected**: eps parameter is sensitive and difficult to set without a larger universe. Number of clusters is data-determined, not controllable — conflicts with the sleeve prior validation objective. Noise detection (points not assigned to any cluster) adds an edge case requiring separate handling.

**Scope limitation explicitly accepted**: K-means assumes spherical clusters of roughly equal size. Real ETF data may have non-spherical structures (bond ETFs and equity ETFs form a continuum rather than distinct spheres). A commercial version with 200+ ETFs should revisit GMM for soft boundaries.

## For Discussion

1. If future analysis reveals non-spherical cluster structures through visualization, would switching to GMM be worth the added complexity? Is there a clear empirical threshold that would trigger this reconsideration?

2. DBSCAN's noise detection could identify ETFs that don't fit any sleeve (anomaly detection). Should DBSCAN be run as a diagnostic alongside K-means, not as a replacement?

3. The 23-ETF universe is fixed for the demo. At what universe size (50 ETFs? 100?) would DBSCAN become viable and worth revisiting?
