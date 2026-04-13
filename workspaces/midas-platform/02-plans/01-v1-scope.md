# Midas v1 — Scope Definition

## What v1 IS

An impersonal-publisher platform (US publisher's exemption) that broadcasts regime-aware multi-asset ETF model portfolios via web + mobile, with a debate-with-AI layer and IBKR-native user-executed trades.

## What v1 is NOT

- Not a discretionary advisor (requires RIA license — v2+)
- Not tax-aware (per-user tax-lot awareness = personalization = breaks publisher exemption)
- Not real-time trading (screen-active pull, not streaming)
- Not options/leverage/single-stock (ETF universe only)
- Not international (US-only; UK/SG/EU geofenced)

## Deliverables

### D1. Data Fabric
- EODHD ingestion pipeline (EOD bars, fundamentals, corporate actions, delisted tickers)
- FRED ingestion (VIX, VIX3M, VVIX, credit spreads, yield curve, macro)
- Yahoo Finance reconciliation layer (backup, cross-check, not primary)
- Perplexity news ingestion with pgvector caching
- Postgres 16 + TimescaleDB + pgvector, DataFlow-managed
- Redis hot cache for screen-active pulls
- Point-in-time ETF universe (survivorship-free backtests)
- Historical data load: 2000-01-01 to present

### D2. Strategy Engine
- Regime detection ensemble (8 signals, weighted, 2-day hysteresis, drawdown override)
- Adaptive Asset Allocation (top-K momentum → min-variance → vol-target)
- HRP fallback allocator
- Transaction cost model node (IBKR tiered + SEC §31 + FINRA TAF + slippage + impact + gap)
- Single Core SDK workflow with TimeSourceNode (backtest/live parity)
- 8 asset sleeves: equity sector ETFs, precious metals, govt bonds (all durations), IG corp bonds, REITs, commodities, dividend ETFs, EM equity

### D3. Backtest Engine
- Walk-forward validation
- CPCV with embargo
- Deflated Sharpe and PBO reporting
- Multi-horizon: 1y, 3y, 5y, 10y rolling windows
- Cost-drag attribution
- Regime-conditional performance breakdown
- Point-in-time instrument universe

### D4. Signal Publication
- Weekly signal generation (post-Friday-close, publish Sunday evening)
- Impersonal: keyed by (model_portfolio_id, timestamp), NO user_id
- 5 model portfolios: "Aggressive Growth" (18% vol target), "Growth" (14%), "Balanced" (10%), "Conservative" (6%), "Income" (6%, dividend-heavy)
- CDN-cacheable `/signals/latest` endpoint
- Signal audit trail (immutable, every input value preserved)

### D5. IBKR Integration
- Client Portal Web API connector
- OAuth flow (production application in-flight; local CP Gateway fallback for beta)
- Order preview (what the signal implies for the user's current holdings — computed CLIENT-SIDE)
- Order submission (user-initiated, biometric-confirmed)
- Position sync (read-only, for the approval UX)
- Paper trading mode for onboarding

### D6. Debate Agent
- Kaizen-based DebateAgent with DebateSignature
- Hard grounding contract: every claim cites signal/backtest/cost IDs, `ungrounded_claims` must be empty
- Tools: fetch_signal, fetch_backtest_run, fetch_cost_model, fetch_recommendation, fetch_news_by_id, fetch_regime_state
- Counter-scenario capability ("if you disagree, here's what happens if we skip this rebalance")
- Resist sycophancy: trained to defend positions with data, not capitulate
- LLM-first, zero deterministic routing

### D7. Web Application (Next.js)
- Dashboard: portfolio value, P&L vs benchmark, current regime, next signal date, pending approvals count
- Signal detail: per-sleeve allocation, reasoning, cost estimate, backtest context
- Pending approvals: grouped rebalance card, per-item opt-out, biometric confirm
- Order preview (feature-flagged, pending legal opinion): client-side computation showing what the signal implies for user's IBKR holdings. Server never sees user positions.
- Debate chat: full conversation UI, citation cards, backtest drill-down
- Backtest explorer: multi-horizon, regime-conditional, cost-drag, turnover
- Trade log / audit: immutable record of every signal, every action
- Settings: model portfolio selection, notification preferences, IBKR link
- Auth: email + password, MFA

### D8. Mobile Application (React Native / Expo)
- Approval-first UX: push notification → one-screen approval card → biometric → execute at IBKR
- Debate chat (simplified)
- Dashboard (read-only)
- Deep link from push to specific pending approval
- Biometric auth (Face ID / Touch ID)

### D9. Governance & Audit
- PACT publisher/subscriber envelope separation
- Postgres role enforcement (publisher role cannot SELECT from users.*) + boot-time assertion + CI check
- Turbulent escalation protocol: T+0h notify → T+12h reminder → T+24h auto-defensive (configurable 12h–72h)
- Append-only audit hypertable
- Regime change audit (every transition logged with all input signal values)

### D10. Infrastructure
- Monorepo layout (see 03-monorepo-layout.md)
- CI/CD: GitHub Actions, pytest, backtest regression, grounding assertions
- Secret management: .env, never in repo
- Deployment: containerized (Docker), managed Postgres/Timescale

## Out of Scope (v2+)

| Feature | Reason | When |
|---|---|---|
| Personalized risk scoring | Publisher exemption | v2 + RIA |
| Tax-loss harvesting | Publisher exemption | v2 + RIA |
| Auto-execution (no user click) | Publisher exemption | v2 + RIA |
| UK/SG/EU expansion | Licensing | v2+ |
| Options / leverage | Asset universe scope | v3+ |
| Community features | Network effect layer | v3+ |
| Single stocks | Research burden | v3+ |
