# ML Specialist Review — ETF Clustering for Argus

## Preamble: What I Found vs What I Expected

I expected to review a clean ML design document. Instead I found a codebase where ETF features are already partially computed -- and a critical gap between what the design assumes and what the allocator already produces.

The existing challenges document (`02-ml-design-challenges.md`) is competent but surfaces the wrong problem. It argues about algorithm choice (K-means vs hierarchical) and metric choice (cosine vs Euclidean) without first confronting the deeper issue: **the ETF universe is defined by a static sleeve taxonomy, and the "features" for clustering aren't features at all -- they're metadata.**

This review challenges the framing from the ground up.

---

## Challenge 1: The Sleeve Taxonomy Is the Clustering Algorithm

### The Core Problem No One Is Naming

The 10 sleeves in `sleeves/__init__.py` ARE the clusters. They were designed by a human expert to represent economically distinct asset classes:

- `equity_sector`: SPY/QQQ/XLF (large-cap equity)
- `precious_metals`: GLD/SLV (gold/silver)
- `govt_bonds_short/medium/long`: SHY/SHV, IEF/IEI, TLT/TLH (bond duration ladder)
- `ig_corp_bonds`: LQD/VCIT (credit)
- `reits`: VNQ/IYR (real estate)
- `commodities`: DJP/GSG/DBC (broad commodities)
- `dividend_etfs`: VYM/DVY/SDY (equity income)
- `em_equity`: VWO/EEM (emerging markets)

This is not a 10-feature clustering problem. This is a **10-cluster prior** encoded in domain knowledge. The question isn't "how do we cluster 23 ETFs?" -- it's "why would we re-discover what the expert already encoded?"

### Where K-means Actually Works (The Unpopular Argument)

The existing challenges document says K-means is wrong for ETFs. I disagree -- partially. K-means is wrong **when the cluster structure is unknown and must be discovered**. But when:

1. The ETF universe is small (23 tickers)
2. The clusters are semantically meaningful (sleeve IDs have economic interpretability)
3. The use case is guideline monitoring (you want to know which ETFs behave like government bonds, not which ones form a Voronoi cell)

...then K-means can work as a **transductive inference** tool, not an unsupervised discovery tool. Specifically:

- Run K-means with k=10 on return/feature data to **verify** that the sleeve assignments hold up empirically
- If K-means with k=10 produces clusters that match the sleeve taxonomy, the taxonomy is validated
- If it produces different clusters, that IS the finding -- it tells you something about ETF behavior that contradicts the taxonomy

The literature supports this. MacQueen (1967) introduced K-means as a classification tool for labeled problems. DeGiorgio et al. (2009) used K-means in a transductive setting where class labels were known a priori. **Using K-means to check whether the sleeve taxonomy is empirically coherent is the correct application. Using it to discover structure in an unknown ETF universe is the wrong application.**

### Recommendation

Do NOT choose between K-means and hierarchical clustering based on which is "better" in the abstract. Choose based on the objective:

| Objective | Algorithm | Why |
|---|---|---|
| Validate sleeve taxonomy | K-means (k=10) | Transductive check: do empirical clusters match prior clusters? |
| Discover outlier ETFs | HDBSCAN | Density-based: which ETFs don't fit any sleeve? |
| Understand cross-regime behavior | Hierarchical (Ward) | Dendrogram reveals nested structure |
| Provide recommendations | None of these -- use correlation | Clustering is unsupervised; recommendations are supervised |

---

## Challenge 2: The Feature Set Gap Is a Data Architecture Problem

### What's Actually in the Codebase

The allocator (`allocator/__init__.py`) computes the following per-sleeve features **today**:

1. **126-day cumulative momentum** (lines 65-85) -- the core signal
2. **63-day covariance matrix** (lines 141-163) -- per-sleeve variance and cross-sleeve correlations
3. **Annualized volatility** (line 184) -- derived from covariance + vol-target scaling
4. **Min-variance weights** (lines 106-138) -- inverse-covariance-weighted allocation

The `sleeves/__init__.py` ETFDef contains: `expense_ratio`, `avg_daily_volume`, `liquidity_tier` -- these are static, defined at authoring time, never updated.

### The Critical Gap

The design document mentions "10 features" but:

- **expense_ratio** is not a feature -- it's a cost. Two ETFs with identical returns but different expense ratios are NOT different investments; one is just more expensive.
- **avg_daily_volume** in shares (not dollars) is meaningless without price. A 50M share ADV for SPY ($500/share) = $25B daily. A 50M share ADV for VNQ ($90/share) = $4.5B daily. These have different liquidity implications.
- **liquidity_tier** is a categorical prior, not a computed feature.

The actual features the allocator computes are:
- 126d return (momentum)
- 63d volatility (realized risk)
- Beta to SPY (implicit in the covariance matrix)
- Correlation to other sleeves (implicit in the off-diagonal of the covariance matrix)

None of these are persisted. They exist in the return of `allocate()` as ephemeral computation.

### What the Clustering Should Actually Use

For the "find similar ETFs for guideline monitoring" use case, the relevant features are:

**For price-behavior similarity (what the design seems to target):**
1. 252d return -- long-horizon momentum
2. 252d volatility -- annualized risk
3. Beta to SPY -- market sensitivity
4. Max drawdown (252d) -- tail risk (NOT computed anywhere)
5. Correlation to other sleeves -- cross-asset behavior

**For liquidity/market structure (what the sleeves define):**
6. ADV in dollars (not shares) -- true dollar liquidity
7. Bid-ask spread (if available) -- execution cost
8. ETF age -- market maturity

**For cost (what the current ETFDef has):**
9. Expense ratio -- total expense ratio only; performance-adjusted cost is meaningless without a benchmark

That is 9 features, not 10. And 4 of them (items 1-4) require computing from price data that the signal workflow (`signals/workflow.py`) already fetches.

### Recommendation

Before clustering, build a **per-sleeve feature store** that computes and caches these features. The allocator already computes 1-4. The `TimeSource` already fetches price data. The gap is: these are computed fresh on every signal generation and thrown away. Persisting them enables:

- Time-series clustering (cluster the 10 sleeves across 3 years of quarterly snapshots)
- Regime-conditional features (compute features separately for normal vs turbulent periods)
- Stability metrics (do features drift over time?)

---

## Challenge 3: Regime-Conditioning Is Achievable in Week 9 -- With Caveats

### What the Regime Detector Already Does

The `regime/ensemble.py` is sophisticated. It runs a 7-signal weighted ensemble with hard overrides:

- HY OAS (0.25 weight) -- leading indicator
- VIX3M backwardation (0.20) -- term structure
- PC1 cross-sector variance (0.20) -- contagion detection
- VIX level (0.10), SMA200 persistence (0.10), 21d realized vol (0.10), yield curve (0.05)

Hard overrides: drawdown >= 8% forces cautious, >= 12% forces turbulent, SPY/TLT correlation > +0.3 forces cautious.

Outputs: `RegimeLevel` (NORMAL/CAUTIOUS/TURBULENT) with confidence score.

### The Minimum Viable Regime-Conditional Clustering

Regime conditioning means: "TLT behaves like an equity in turbulent regimes (correlation flips positive with SPY). Clustering TLT with bonds in normal regimes and with equities in turbulent regimes is the correct behavior."

**Week 9 minimum viable approach:**

```
Step 1: For each of the 3 regimes, compute:
  - 252d return per sleeve
  - 63d covariance matrix per regime
  - Average correlation to SPY per regime

Step 2: Use these as "regime snapshots":
  - Normal regime features (63d rolling window when regime == NORMAL)
  - Cautious regime features (63d rolling window when regime == CAUTIOUS)
  - Turbulent regime features (63d rolling window when regime == TURBULENT)

Step 3: Clustering:
  - Option A: Run hierarchical clustering separately per regime snapshot
  - Option B: Use regime as a feature dimension (add 3 binary columns: is_normal, is_cautious, is_turbulent) and cluster once

Step 4: Store cluster assignments per regime so Argus can look up:
  - "In current regime (NORMAL, conf=0.85), which ETFs cluster with TLT?"
```

**Literature:** Ang and Timmermann (2012), "Regime Changes and Financial Markets," Annual Review of Financial Economics, shows that regime-conditional correlations are critical for portfolio construction and that naive unconditional correlations materially misrepresent tail risk. This is not a theoretical concern -- it has measurable portfolio impact.

### What This Actually Requires

The computation is achievable in Week 9 because:

1. Price data is already fetched by `TimeSource.get_bars()`
2. Regime labels are already computed by `RegimeDetector.detect()`
3. Daily returns are already computed by `compute_daily_returns()`

The hard part is NOT the computation -- it's the **feature store** (Challenge 2). If features aren't persisted, regime-conditional clustering requires replaying the entire backtest history on every query.

**Risk:** The naive approach (Option B -- add binary regime columns) confounds regime effects with other features. If the regime columns dominate the Euclidean distance, all NORMAL-period ETFs cluster together regardless of their asset class. This is the wrong answer.

**Mitigation:** Normalize regime features separately within each regime before combining. Or use Option A (separate clusterings per regime) and validate that cluster stability is acceptable (same ETFs cluster together across regimes).

---

## Challenge 4: Validation Is the Wrong Word -- Use Diagnostic

### The Problem with "Validation" in Unsupervised Learning

"Validation" implies a ground truth. Clustering has no ground truth. What you can have is:

1. **Internal coherence**: Are within-cluster distances smaller than between-cluster distances?
2. **Semantic coherence**: Do cluster members share economic meaning? (Does the "government bonds" cluster actually contain government bond ETFs?)
3. **Temporal stability**: Do clusters persist over time? (Do they hold across 2020, 2022, 2024?)
4. **Actionable differentiation**: Do clusters produce different guideline violation signals?

### Metric Inventory

**Silhouette score** (range -1 to +1): Average ratio of between-cluster distance to within-cluster distance. A silhouette > 0.5 means clusters are well-separated. A silhouette < 0.25 means clusters are barely distinguishable. **This is a necessary but not sufficient condition for usefulness.**

**Davies-Bouldin index** (lower is better): Average worst-case ratio of within-cluster scatter to between-cluster separation. Captures cluster overlap that silhouette misses.

**Calinski-Harabasz index** (higher is better): Ratio of between-cluster variance to within-cluster variance. More statistically powerful than silhouette for small datasets (< 50 samples).

**For the Argus use case specifically:**
- Internal coherence metrics (silhouette, DB, CH) tell you if clusters are statistically distinct
- **They do NOT tell you if clusters are economically meaningful**
- Economic meaning requires: (a) the sleeve taxonomy as a prior, and (b) human review of cluster membership

### The Right Diagnostic for Argus

Given the "find similar ETFs for guideline monitoring" use case, the diagnostic that matters is:

```
For each ETF, find its 3 nearest neighbors by Euclidean distance in feature space.
Count: how many neighbors share the same sleeve ID?

Precision@3 = (# neighbors with same sleeve) / (# total neighbors)

If Precision@3 > 0.7: ETF's nearest neighbors are from the same sleeve.
  → The sleeve taxonomy is empirically coherent. Clustering confirms domain expertise.

If Precision@3 < 0.3: ETF's nearest neighbors are from different sleeves.
  → The sleeve taxonomy is NOT empirically coherent. TLT is closer to SPY than to SHY.
  → This IS the finding. Report it. Do not paper over it with a different algorithm.
```

This diagnostic is inspired by information retrieval evaluation (Manning et al., 2008, Introduction to Information Retrieval). It directly measures whether the taxonomic prior (sleeve IDs) maps to statistical similarity. It requires no ground truth -- just the sleeve labels that already exist.

### What Cluster Stability Tells You

A cluster stability analysis (re-run clustering on rolling 252-day windows and measure cluster membership change) is valuable but often misinterpreted:

- High stability (same ETFs in same clusters across time) can mean: (a) the structure is genuinely stable, or (b) the features are dominated by a slowly-changing variable (expense ratio is static, so it biases toward stability)
- Low stability can mean: (a) the market structure genuinely shifts across regimes, or (b) the feature set is too noisy

For the ETF use case, I expect low stability across regimes for bond sleeves specifically (TLT's behavior changes dramatically between normal and turbulent markets). This is a FEATURE, not a bug -- it tells the guideline monitoring system that TLT must be re-clustered when the regime changes.

---

## The Meta-Challenge: The Use Case Drives the Method, Not the Other Way Around

The existing challenges document asks "is K-means right?" and "is cosine similarity right?" These are the wrong questions.

The right question is: **"What does 'similar ETF' mean for guideline monitoring?"**

If "similar" means "would violate the same guideline rule":
- This is a SUPERVISED problem. You need historical violation labels per ETF per rule.
- Not achievable in Week 9 without pre-existing labels.
- Clustering is the wrong tool entirely.

If "similar" means "has historically similar price behavior":
- This is an unsupervised problem. Euclidean distance on standardized features works.
- Hierarchical clustering is preferred for interpretability.
- Achievable in Week 9 with existing code paths.

If "similar" means "would have similar behavior in a crash scenario":
- This is a counterfactual problem. You need regime-conditional clustering.
- The allocator already computes the regime; this is achievable.
- The minimum viable version: cluster on rolling 252d features when regime == NORMAL only, and accept that cluster assignments will change when regime changes.

### My Recommendation for Argus Week 9

**Ship the diagnostic, not the clustering.**

Build the per-sleeve feature store first (Challenge 2). Then run the Precision@3 diagnostic on existing sleeve assignments. Report:

- Which ETFs' nearest neighbors are NOT from the same sleeve? (These are the ETFs that violate the taxonomic prior -- TLT, dividend ETFs, and REITs are likely candidates)
- What is the average silhouette score? (Are clusters statistically distinguishable?)
- How stable are clusters across 2020, 2022, and 2024? (Do sleeve assignments hold across crises?)

This is a **discovery tool** for the guideline monitoring system. It tells the human analyst which ETFs behave counter-intuitively relative to their sleeve assignment -- and those are exactly the ETFs that need special monitoring attention.

**Do NOT ship "here are 4 clusters of similar ETFs" as a consumer-facing feature in Week 9.** That requires: (a) the feature store, (b) regime-conditional clusters, (c) a human-understandable dendrogram or explanation of what "similar" means, and (d) a UX that shows the user why TLT is in the "equity-like" cluster in turbulent regimes. That is a Week 10 or Week 11 deliverable.

---

## Summary of Challenges

| Challenge | Current Framing | Correct Framing |
|---|---|---|
| Algorithm choice | "K-means vs hierarchical" | "Transductive validation vs exploratory discovery" |
| Similarity metric | "Cosine vs Euclidean" | Neither matters until features are correct |
| Feature set | "10 features for ETF clustering" | "9 features from a per-sleeve feature store that doesn't exist yet" |
| Regime conditioning | "Can we do it in Week 9?" | "Yes -- compute regime snapshots from existing allocator data" |
| Validation | "Silhouette score" | "Precision@3 against sleeve prior + cluster stability over time" |
| Use case | "Find similar ETFs" | "Discovery tool: which ETFs violate the taxonomic prior?" |

The existing design challenges document is a solid first pass. The gap is that it treats these as ML design decisions when they are actually **data architecture decisions** that must precede any ML work.
