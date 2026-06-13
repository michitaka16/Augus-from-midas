# ML Design Challenges — ETF Clustering and Similarity

## Q1: Is K-means the Right Algorithm for ETF Clustering?

### Short Answer: NO — not as a primary algorithm.

### Why K-means fails for ETF clustering:

**1. Static clusters in a dynamic market**
K-means optimizes within-sample inertia — it finds clusters that minimize distance to centroids given the current input. But ETF correlation structures are regime-dependent:
- Normal markets: equities cluster by sector (tech vs financials vs energy)
- Crisis markets: ALL equities correlate to 1.0 (救済 trades)
- Low-vol regimes: defensive vs growth cluster differently

K-means with k=4 gives you 4 static groups. The market gives you 4 different groupings every quarter.

**2. The within-cluster variance assumption is wrong**
Financial returns have fat tails and are non-Gaussian. K-means assumes spherical clusters of roughly equal variance. ETF return distributions violate this:
- Small-cap ETFs have 3x the variance of bond ETFs
- Sector ETFs have regime-conditional variance
- Crisis periods compress between-cluster variance AND inflate within-cluster variance

**3. K-means requires you to guess k**
How many clusters do you want? For ETF universes:
- 5 clusters (large asset classes)?
- 20 clusters (fine-grained sector/specialty)?
- This choice is arbitrary and drives all downstream results.

### Better alternatives:

**Hierarchical Clustering (Ward or complete linkage)**
```
Pros:
- No need to pre-specify k — dendrogram reveals natural groupings at all scales
- Reveals nested structure: Large asset class → sub-sector → factor tilt
- Single-linkage detects ETF "chain effects" (SPY → QQQ → TQQQ chaining)
- dendrogram is interpretable by non-technical users

Cons:
- Computational cost O(n² log n) — acceptable for <500 ETFs
- Choice of linkage criterion matters (Ward vs complete vs average)
```

**HDBSCAN (Hierarchical DBSCAN)**
```
Pros:
- Finds clusters of varying density automatically
- Handles outliers as noise (not forced into a cluster)
- Produces a hierarchy like hierarchical clustering
- No k to guess

Cons:
- Requires good epsilon parameter (or auto-tuning)
- Less interpretable than a dendrogram for non-technical users
```

**Practical recommendation for Week 9:**
Use hierarchical clustering (Ward linkage) as the primary. HDBSCAN as a secondary validation. K-means only as a baseline comparison in a paper-trading comparison, not as the production algorithm.

**What hierarchical clustering reveals that K-means cannot:**
```
Normal regime dendrogram (example):
├── US Equity
│   ├── Large Cap (SPY, VOO, IVV)
│   ├── Tech/Growth (QQQ, VGT)
│   ├── Small Cap Value (VB, IWN)
│   └── Momentum (SPY momentum ETF)
├── Fixed Income
│   ├── Treasuries (TLT, GOVT, SHY)
│   ├── Investment Grade Corp (LQD, VCIT)
│   └── High Yield (HYG, JNK)
├── Alternatives
│   ├── Gold (GLD, IAU)
│   ├── REITs (VNQ,IYR)
│   └── Commodities (DJP)
└── International
    ├── Developed (VEA, IEFA)
    └── EM (VWO, IEMG)
```

---

## Q2: Is Cosine Similarity the Right Metric for ETF Recommendation?

### Short Answer: NO — not for this use case.

### Why cosine similarity fails here:

**1. Cosine similarity is INVARIANT to scale — but scale matters for ETFs**
Cosine similarity measures the angle between two vectors, ignoring magnitude. For ETF returns:

```
ETF A: daily returns [+1%, +2%, -0.5%, +3%]    → vector direction
ETF B: daily returns [+0.1%, +0.2%, -0.05%, +0.3%] → SAME direction, 10x smaller

Cosine similarity(A, B) = 0.9999 (nearly identical)
But ETF B has 10x lower volatility — they are NOT similar investments
```

**2. Cosine similarity is especially wrong for low-vol/defensive ETFs**
High-yield bonds vs investment-grade bonds:
```
HY bonds: returns [0.01, 0.02, -0.01, 0.015] → high variance
IG bonds: returns [0.001, 0.002, -0.001, 0.0015] → low variance, same direction

Cosine ≈ 0.99 (identical direction)
But IG bonds are NOT a substitute for HY bonds in a portfolio — different risk/return
```

**3. Angle-based similarity treats opposing directions as orthogonal**
```
ETF A: [+1%, -1%, +1%, -1%] → oscillating
ETF B: [-1%, +1%, -1%, +1%] → oscillating opposite

Cosine similarity = 0 (orthogonal — "not related")
But both are the SAME volatility pattern, just opposite phase
```

### Better alternatives:

**Pearson Correlation (or Spearman for non-linear)**
```
Pros:
- Captures LINEAR relationship, not just direction
- Well-understood in finance (correlation matrices are standard)
- Range [-1, +1] with clear interpretation

Cons:
- Still ignores scale (stddev)
- Sensitive to outliers
- Linear assumption still imperfect for financial returns
```

**Euclidean Distance on Standardized Features (z-score)**
```
Pros:
- Captures both direction AND scale differences
- Standardization puts all features on same footing
- Interpretable: "these ETFs are 2.3 standard deviations apart"
- Works well with hierarchical clustering (which uses Euclidean distance)

Cons:
- Sensitive to the standardization window (252 days? 504 days?)
- Requires careful feature selection
```

**For the ETF recommendation use case:**
Use Euclidean distance on standardized features as the primary metric. Supplement with Pearson correlation for interpretation. Reserve cosine similarity ONLY for comparing return direction patterns (e.g., "which ETFs move in the same direction as SPY?").

**Practical recommendation:**
```
1. Compute feature matrix: [return, vol, sharpe, beta, volume, sector_weight, ...]
2. Z-score standardize each feature across the ETF universe
3. Use Euclidean distance for clustering (Ward linkage)
4. Use Pearson correlation as a secondary similarity measure for recommendations
5. NEVER use cosine similarity as a primary similarity metric for portfolios
```

---

## Q3: Is 10 Features Enough? What Would You Drop?

### The real question is: 10 features for what purpose?

The user hasn't specified the clustering objective. "Cluster ETFs" without a goal is meaningless — clustering by volatility gives different groups than clustering by sector exposure.

### Standard ETF feature sets by objective:

**For risk-based clustering (group by risk characteristics):**
1. Annualized volatility (22d, 63d, 252d) — DROP: just use 252d
2. Maximum drawdown (252d)
3. Sharpe ratio
4. Beta to SPY (or other benchmark)
5. Correlation to portfolio benchmark
6. Tail ratio (95th / 5th percentile of daily returns)
7. Recovery time (avg days from drawdown to new high)
8. Turnover (annual portfolio churn)

**For factor-based clustering:**
1. Market beta
2. Size beta (small-cap vs large-cap loading)
3. Value factor loading
4. Momentum factor loading (252d return)
5. Quality factor loading (ROE, debt/equity)
6. Sector exposure weights (top 3 sectors by weight)

**For liquidity-based clustering:**
1. Average daily volume
2. ADV (average dollar volume)
3. Number of institutional holders
4. bid-ask spread (if available)
5. ETF age

### What I would DROP from the current 10:

**DROP these:**
- `avg_volume` — liquidity is captured by ADV in dollar terms, avg_volume in shares is meaningless without price
- `yield` — dividend yield is irrelevant for non-income ETFs; confuses growth vs income categories
- `expense_ratio` — it's a cost, not a return driver; an expensive ETF can have identical returns to a cheap one

**ADD these (missing and high-importance):**
- `max_drawdown_252d` — critical risk measure, captures tail risk that volatility misses
- `corr_to_benchmark` — whether an ETF tracks with the portfolio or diverges is critical for monitoring
- `sector_top3_weights` — at minimum, the top sector exposure (ETF could be 40% tech and that's the whole story)

**The minimum viable feature set for ETF clustering (Week 9, production):**
1. 252d return (momentum)
2. 252d volatility (risk)
3. Sharpe ratio (risk-adjusted return)
4. Beta to SPY (market sensitivity)
5. Max drawdown (tail risk)
6. ADV in $ (liquidity)
7. Top sector weight (identity)

7 features. 10 is overkill if features are correlated (vol and max_drawdown are ~80% correlated; Sharpe and return are ~70% correlated).

---

## The Highest-Risk Component for Week 9

### Identification: The "ETF Clustering for Recommendations" Problem is Underspecified

The single highest-risk component is: **defining what "similar ETF" means for the guideline monitoring use case.**

Here is why:

1. **If the user means "find ETFs that would have similar behavior in a crash":**
   → Need regime-conditional clustering (cluster separately in normal vs turbulent markets)
   → This doubles the data requirements and makes historical backtesting necessary
   → NOT achievable in Week 9

2. **If the user means "find ETFs with similar factor loadings":**
   → Need a factor model (Fama-French or similar)
   → Data is available (AQR publishes factor data), but the regression is complex
   → Achievable in Week 9 with existing libraries (statsmodels, sklearn)

3. **If the user means "find ETFs that would trigger the same guideline violations":**
   → This is a SUPERVISED problem (given guideline rule → which ETFs violate it)
   → Not clustering at all — classification
   → Labeled data needed (violations per ETF per historical period)
   → NOT achievable in Week 9 without pre-existing labels

4. **If the user means "find ETFs that move together (high correlation)":**
   → Simple correlation-based clustering
   → Achievable in Week 9
   → But this is NOT the same as "similar ETF" in any sophisticated sense

### My Recommendation:

**For Week 9, ship the simplest version that works:**
- Euclidean distance on 7 standardized features (return, vol, sharpe, beta, max_dd, adv, sector_top1)
- Hierarchical clustering with Ward linkage
- No regime conditioning (defer to Week 10)
- PRESENT as "ETF similarity for monitoring" not "AI-powered ETF clustering"
- Be honest that similarity = "statistically similar historical price behavior"

**The risk:** If the user expects "intelligent ETF clustering that knows when to group defensives together vs when to group them with risk assets," this will disappoint. The financial ML literature has NOT solved regime-conditional unsupervised clustering in a robust, generalizable way. Over-promising this capability is the highest risk for Week 9.

### Mitigation:

Build a validation dashboard showing:
- For each cluster: top-3 representative ETFs
- Cluster stability over time (do clusters hold across 2020, 2022, 2024?)
- Correlation heatmap within each cluster
- This lets users judge quality without needing to understand the algorithm
