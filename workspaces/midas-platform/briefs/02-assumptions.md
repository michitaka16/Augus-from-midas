# Working Assumptions — Midas Platform

These were set by the agent when the user did not explicitly answer blocker questions. User can override at any gate; changing these invalidates downstream analysis.

## A1. Capital Tier
- **Default**: $50k–$1M per account, IBKR Pro commission tier
- **Rationale**: Avoids odd-lot/min-position problems, full ETF universe accessible, realistic slippage regime, "go big" meaningful
- **If wrong**: Commission model + min-trade sizing + instrument universe all shift

## A2. Regulatory Posture
- **v1**: Personal use + signal-only SaaS (system recommends, user confirms every execution)
- **v2 path**: Discretionary (RIA / equivalent license) — deferred, not blocking v1
- **Rationale**: Autonomous execution for third parties requires RIA registration (US), FCA/MAS equivalent elsewhere. Licensing is a 6–12 month parallel track. v1 ships without it by making user the executor.
- **If wrong**: v1 scope grows to include compliance, custody, reg reporting — months of work

## A3. "Turbulent" Regime Detection
- **Method**: Multi-signal ensemble, auto-detected
  - VIX level + VIX term structure (contango/backwardation)
  - Realized volatility (multiple windows)
  - Cross-asset correlation breakdown (stocks/bonds, intra-equity)
  - Credit spreads (HY OAS, IG OAS)
  - Yield curve shape / inversions
  - Drawdown from trailing peak
- **Action on trigger**: Freeze auto-trading, notify user, require explicit approval per trade until regime clears
- **If wrong**: Swap detection method without rewriting downstream gates

## A4. Backtest Horizon
- **Range**: 2000-01-01 to present
- **Regimes covered**: Dot-com bust, 2003–07 bull, 2008 GFC, 2010 flash crash, EU debt 2011–12, taper tantrum 2013, 2015–16 China/oil, 2018 vol shock, 2020 COVID, 2021 meme/low-vol, 2022 rates shock, 2023 banking stress, 2024–26 rate normalization
- **Sub-horizons**: 1y, 3y, 5y, 10y rolling windows; walk-forward; purged k-fold CV
- **If wrong**: Extend to pre-2000 (limited ETF history — would need index proxies)

## A5. Workspace & Product Name
- **Workspace**: `midas-platform`
- **Product codename**: Midas (inherited from repo)

## A6. Rebalancing Cadence Cap
- Hard cap: 1x per week (from brief)
- Regime-dependent within cap: normal = weekly or less, calm trend = biweekly, turbulent = frozen pending approval

## A7. News Ingestion
- Perplexity API as primary news/sentiment source
- Cached in fabric; re-queried only on material price moves or user open
