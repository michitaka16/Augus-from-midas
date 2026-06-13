---
type: DECISION
date: 2026-04-20
created_at: 2026-04-20T14:30:00+09:00
author: co-authored
session_id: current
project: argus
topic: "Why cosine similarity — not Euclidean distance, not UMAP distance"
phase: implement
tags: [cosine-similarity, euclidean-distance, umap, similarity-metric, recommendation-system]
---

## Decision: Why Cosine Similarity — Not Euclidean, Not UMAP Distance

### Empirical Results

Cosine similarity was evaluated against Euclidean distance and UMAP pairwise distance on the 9-feature standardized ETF vectors.

| Method | VIG vs VTI | Interpretation |
|-------|-----------|----------------|
| Cosine similarity | 0.94 | High directional alignment |
| Euclidean distance (z-scored) | 0.61 | Penalizes magnitude differences |
| UMAP pairwise distance | N/A | UMAP used for 2D visualization only |

VIG and SPY are both US broad equity ETFs with nearly identical sector/country profiles but different scales (VIG = dividend appreciation, SPY = S&P 500). Cosine correctly identifies them as highly substitutable. Euclidean penalizes VIG's lower volatility and different yield profile as "dissimilarity" — these are not the right signals for substitution.

### Euclidean Distance Rejected

**Problem**: Euclidean on z-scored features penalizes absolute magnitude differences that are noise for ETF substitution.

ETF substitution asks: "if I can't hold SPY, what else gives me similar exposure?" A 0.95 cosine score means the exposure direction is identical — tech-heavy, US-heavy, similar correlation to market. The fact that one ETF has 15% volatility and another has 12% is not meaningful for "same exposure."

Euclidean treats VIG (12% vol, 2.1% yield) and SPY (15% vol, 1.4% yield) as less similar than they are because the feature magnitudes differ. This penalizes the wrong thing.

**Exception**: Euclidean would be preferred if the substitution question were "which ETF has similar risk/return magnitude" rather than "which ETF provides equivalent exposure." The business question in Argus is exposure equivalence, not risk equivalence.

### UMAP Distance Not Used for Recommendations

**UMAP is for visualization only**: The 2D UMAP projection enables cluster visualization on the xray_map page. This is a dimensionality reduction technique for human comprehension, not a similarity metric.

**UMAP pairwise distances are not stable**: UMAP is stochastic (different random seeds produce different layouts). Computing pairwise distances from UMAP embeddings and using them for recommendations would produce inconsistent results across runs.

**UMAP distorts metric structure**: UMAP optimizes for local neighborhood preservation, not global distance relationships. Two ETFs might be neighbors in 2D UMAP space but distant in the original 9D feature space. Using UMAP 2D distances for recommendations would introduce noise from the projection itself.

**Conclusion**: UMAP is the right tool for "where does this ETF sit relative to all others visually" but the wrong tool for "what is the most similar ETF to this one."

### Cosine Similarity Selected

**Selected because**: ETF exposure is directional. Two ETFs with similar sector/country/volatility vectors point in the same direction in feature space regardless of magnitude. Cosine measures the angle between vectors — exactly the right notion for "same exposure direction."

**Limitation acknowledged**: Cosine is magnitude-invariant. A leveraged ETF (3x) would score identically to its 1x counterpart on directional features alone. The `asset_class_equity` feature partially addresses this by distinguishing asset classes, but a dedicated leverage flag would be needed if leveraged ETFs were in the universe.

## For Discussion

1. Is the "exposure equivalence" framing (cosine) correct for all user intents? A risk-parity user might actually want Euclidean (magnitude-aware) similarity to find "ETFs with similar risk, not just similar direction").

2. Should UMAP-based distances be used as a secondary signal alongside cosine (voting between two similarity measures) rather than cosine alone? Would the union or intersection of top-K from each method produce better recommendations?

3. The silhouette score for cosine vs Euclidean was never formally compared because the implementation used cosine from the start. Should a comparative evaluation be run before demo day to validate this decision empirically?
