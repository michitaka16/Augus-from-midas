---
type: DISCOVERY
date: 2026-04-18
created_at: 2026-04-18T20:50:00+09:00
author: agent
session_id: 5eb02fd9-aa3a-47ba-9b00-39629aa71c7b
session_turn: 1
project: argus
topic: ETF clustering reframed as taxonomic validation
phase: analyze
tags: [etf-clustering, ml-design, sleeves, transductive-learning]
---

## Discovery: The Sleeve Taxonomy IS the Clustering Algorithm

The 10 sleeves in `midas_strategy/sleeves/__init__.py` are not a preprocessing step for clustering — they ARE the cluster prior, authored by a domain expert. The ETF universe has only 23 tickers. K-means is not "wrong" if used as a **transductive inference tool**: run K-means with k=10 to CHECK whether empirical clusters match the sleeve taxonomy, not to DISCOVER structure.

**Why this matters for Argus**: The "find similar ETFs" feature should be framed as taxonomic validation (Precision@3 against sleeve prior) first, not as unsupervised discovery. This is a discovery tool that surfaces which ETFs violate the sleeve prior (TLT in turbulent regimes, REITs, dividend ETFs are likely candidates).

**Source**: ML specialist agent review (`05-ml-specialist-review.md`), corroborated by reading `sleeves/__init__.py` and `allocator/__init__.py`.

## For Discussion

1. The existing `02-ml-design-challenges.md` debates K-means vs hierarchical as if the objective is unsupervised discovery. Does the user intend "find similar ETFs" as a consumer feature or as an internal diagnostic? The answer changes the entire ML approach.

2. If the sleeve taxonomy is the prior, who authored it and what economic reasoning underlies each sleeve assignment? The allocator uses these sleeves but doesn't validate them. Is there documented rationale for why SPY and QQQ are in the same sleeve while TLT is separate?

3. The Precision@3 diagnostic requires a per-sleeve feature store that doesn't exist yet (features are ephemeral). What is the minimum feature store needed to run this diagnostic in Week 9 — just 126d return and 63d volatility per sleeve?
