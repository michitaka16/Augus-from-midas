---
type: DECISION
date: 2026-04-19
created_at: 2026-04-19T00:00:00
author: co-authored
session_id: current
project: argus
topic: Why content-based filtering — not using user-item interaction data
phase: implement
tags: [content-based-filtering, collaborative-filtering, recommendation-system, dimension-a]
---

## Decision: Why Content-Based Filtering (Not Collaborative)

### The Recommendation Approach

Argus uses content-based filtering: ETF similarity is computed from observable fund attributes (sector, country, volatility, yield, expense ratio, correlation to SPY) rather than from user behavior (which ETFs users have held or viewed together).

### Collaborative Filtering Considered

Collaborative filtering would identify similar ETFs based on user behavior — e.g., "investors who hold SPY also hold QQQ, therefore SPY and QQQ are similar." This approach can surface non-obvious relationships that metadata cannot capture.

### Collaborative Filtering Rejected

**No behavioral data exists**: Midas does not log user holdings or trade history in a way accessible to a recommendation engine. The system observes live positions for the user's own portfolio but not the broader population of investor behavior.

**Cold start problem**: Even if behavioral data were collected, 23 ETFs is too small a universe for collaborative signals. There would be insufficient user-item interactions to establish reliable similarity patterns.

**Explainability requirement**: Content-based filtering produces similarity scores directly traceable to fund attributes ("these two ETFs are similar because they both have 80% tech exposure and similar volatility"). Collaborative filtering produces black-box similarity that cannot be explained to a user asking "why is this ETF recommended as a substitute?"

**Domain prior availability**: The sleeve taxonomy already encodes expert knowledge about ETF similarity. Collaborative filtering would compete with this prior rather than complement it.

**Acknowledged trade-off**: Content-based filtering cannot discover non-obvious similarity relationships that metadata does not capture. For example, if two ETFs have identical sector/country/volatility profiles but behave differently during earnings season (a pattern not in the features), collaborative filtering would detect it but content-based cannot.

### Hybrid Approach Deferred

A future version could combine content-based similarity (as the baseline) with collaborative signals from a larger user base (anonymized, aggregated). This is not feasible at the current scale.

## For Discussion

1. Is explainability of similarity scores a hard requirement, or would users accept a "because users like you held it" explanation? If explainability is soft, collaborative filtering becomes more viable when user count grows.

2. The cold-start problem could be partially addressed by bootstrapping with the sleeve taxonomy (treat sleeve co-occurrence as a proxy for user behavior). Is this worth exploring as a middle ground?

3. Are there third-party datasets (e.g., ETF correlation data from financial data providers) that could substitute for proprietary user behavior data while preserving explainability?
