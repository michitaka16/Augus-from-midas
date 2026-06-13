# Argus — ETF Compliance & Recommendation Dashboard

**Argus** is a multi-page Dash application for ETF compliance screening and replacement recommendation. It validates portfolios against curated screening presets (Geopolitical Screen, Ethical Investor, Climate First) and recommends alternatives using cluster-based cosine similarity.

**Evolved from Midas** (Week 3 prototype). Midas code preserved in `old/` at project root.

---

## Setup

Requires Python 3.11+. Install dependencies:

```bash
cd apps/argus
uv venv
uv pip install dash dash-bootstrap-components plotly scikit-learn pandas numpy
```

Alternatively, install from the project root (all Argus dependencies are included):

```bash
uv pip install dash dash-bootstrap-components plotly scikit-learn pandas numpy
```

## Run

```bash
cd apps/argus
PYTHONPATH="../../packages/argus-shared/src:../../packages/argus/src" python dash_app.py
```

Starts on **http://127.0.0.1:8050**

## Test (Demo Scenario)

```bash
PYTHONPATH="../../packages/argus-shared/src:../../packages/argus/src" python -c "
import sys; sys.path.insert(0, '.')
from dash_app import compute_portfolio_compliance, compliance_score, cosine_sim_in_cluster, get_cluster, CLUSTER_NAMES

portfolio = ['VTI', 'VWO', 'EEM', 'VOO', 'AGG']
result = compute_portfolio_compliance(portfolio, 'geopolitical_screen')
score = compliance_score(portfolio, 'geopolitical_screen')
green = sum(1 for v in result.values() if v['status'] == 'green')

print('ETF Status:')
for etf in portfolio:
    r = result[etf]
    print(f'  {etf}: {r[\"status\"].upper()} — {r[\"detail\"]}')
print(f'Compliance Score: {green}/{len(portfolio)} = {score}%')

violating = [etf for etf in portfolio if result[etf]['status'] == 'red']
for ticker in violating:
    cluster_name = CLUSTER_NAMES.get(get_cluster(ticker), f'Cluster {get_cluster(ticker)}')
    recs = cosine_sim_in_cluster(ticker, top_n=3)
    print(f'Top 3 Alternatives for {ticker} ({cluster_name}):')
    for rec in recs:
        print(f'  {rec[\"ticker\"]} — cosine_sim={rec[\"cosine_similarity\"]:.4f}')
"
```

Expected output:
```
ETF Status:
  VTI: GREEN — Compliant
  VWO: RED — HARD: China exposure via FTSE Emerging Markets
  EEM: RED — HARD: China exposure via MSCI Emerging Markets
  VOO: GREEN — Compliant
  AGG: GREEN — Compliant
Compliance Score: 3/5 = 60.0%
Top 3 Alternatives for VWO (International Equity):
  VEA — cosine_sim=0.9669
  EFA — cosine_sim=0.9515
  EEM — cosine_sim=0.4180
Top 3 Alternatives for EEM (International Equity):
  VWO — cosine_sim=0.4180
  EFA — cosine_sim=0.3477
  VEA — cosine_sim=0.3153
```

## File Structure

```
apps/argus/
├── dash_app.py          # Main Dash app (3 pages: Compliance, xray_map, Recommend)
├── pages/               # Page layout modules (page1, page2, page3)
└── data/                # Static data
    ├── etf_universe.csv         # ETF metadata (name, sleeve, asset_class)
    ├── etf_prices.csv           # Daily price cache
    ├── etf_stats.csv            # ETF stats (expense_ratio, yield, AUM, volume)
    ├── etf_xray_features.csv    # 9-dim feature vectors (StandardScaler applied)
    ├── etf_xray_data.csv        # Enriched X-ray panel data (country/sector breakdowns)
    ├── umap_coords.csv          # 2D UMAP projection coordinates
    ├── cluster_results.json      # K-means labels for K=3..8
    └── presets.json             # Screening presets (hard/soft constraints, flagged_etfs)
```

## Architecture

- **Clustering**: K-means (K=5) on 9 standardized features. ETF universe: 23 ETFs.
- **Similarity**: Cosine similarity within cluster for replacement recommendations.
- **Compliance**: Rule-based engine (hard = red, soft = yellow, none = green).
- **Visualization**: Plotly UMAP 2D scatter for cluster exploration.
- **Framework**: Dash + dash-bootstrap-components.

## Key Design Decisions

1. **Content-based filtering** — similarity from fund attributes, not user behavior
2. **Cosine > Euclidean** — direction of exposure matters more than magnitude
3. **K=5** — statistical (silhouette) and business interpretability aligned
4. **Hard/soft constraints** — red (fail), yellow (warn), green (pass)
5. **HQ-based country exposure** — acknowledged limitation, revenue-based deferred to commercial
