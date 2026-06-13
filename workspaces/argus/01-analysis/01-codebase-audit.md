# Midas Codebase Audit — Migration to Argus

## Audit Method

Read every source file in packages/, apps/, and scripts/. Classified as:
- **REUSE**: Generic infrastructure, can serve both Midas and Argus
- **REPLACE**: Midas-specific trading logic, must be rewritten
- **KEEP-IN-MIDAS**: Cannot be moved, belongs in old/ Midas
- **DELETE**: Unused, dead code

---

## Package: midas-data

### fabric/cache.py
**Classification: REUSE**
- Generic Redis + PostgreSQL cache abstraction
- No Midas-specific logic
- Works as-is for Argus guideline monitoring

### fabric/ingest.py
**Classification: REUSE**
- Generic data ingestion from EODHD, Yahoo, FRED, Perplexity
- Argus needs the same data sources for portfolio monitoring
- Works as-is

### fabric/pit_universe.py
**Classification: REUSE**
- Point-in-time universe management
- Generic — no trading logic
- Works as-is for Argus (monitoring same ETF universe)

### sources/eodhd.py
**Classification: REUSE**
- EODHD API client
- Argus needs price/OHLCV data for portfolio monitoring
- Works as-is

### sources/yahoo.py
**Classification: REUSE**
- Yahoo Finance reconciliation client
- Already documented as "cross-check only"
- Works as-is

### sources/fred.py
**Classification: REUSE**
- FRED economic data (VIX, yield curve, credit spreads)
- These signals are useful for guideline checks (e.g., "alert when VIX > 30")
- Works as-is

### sources/perplexity.py
**Classification: REUSE**
- News/sentiment via Perplexity API
- Useful for "alert when news mentions portfolio holding negatively"
- Works as-is

### sources/ibkr_spread.py
**Classification: REUSE (partial)**
- IBKR spread data
- Useful for real-time portfolio monitoring

### models/market.py
**Classification: REUSE**
- Market data models (bars, tickers, prices)
- Generic

### models/portfolios.py
**Classification: REUSE**
- Portfolio/account models
- Argus needs the same portfolio model

### models/signals.py
**Classification: DELETE**
- Midas-specific signal model
- Argus doesn't generate trade signals

### models/users.py
**Classification: REUSE**
- User account model
- Works as-is

### models/audit.py
**Classification: REUSE**
- Immutable audit trail
- Essential for Argus (guideline violations must be audited)

### quality/checks.py
**Classification: REUSE**
- Data quality checks
- Works as-is

---

## Package: midas-strategy

### regime/ensemble.py
**Classification: REPLACE**
- Multi-signal regime detector (normal/cautious/turbulent)
- Midas-specific: drives trading decisions
- In Argus: regime awareness is ONE guideline input among many — not the primary output
- Does NOT belong in old/ — copy the ensemble weight knowledge (documented in code comments) before deletion

### allocator/blending.py
**Classification: REPLACE**
- Multi-horizon momentum blending for allocation
- Midas-specific trading logic
- DELETE after extracting HorizonConfig (lookback/window constants only — generic financial concept)

### allocator/__init__.py (Adaptive Asset Allocation)
**Classification: REPLACE**
- AAA allocator: momentum ranking → top-K → min-var → vol-target
- Midas-specific active trading logic
- DELETE

### cost/__init__.py
**Classification: REUSE (partial)**
- Transaction cost model (commission, slippage, market impact)
- Relevant for: "guideline: rebalance cost must stay below X"
- Extract cost calculation formulas, discard Midas-specific portfolio weighting
- MOVE to packages/argus-shared/

### signals/workflow.py
**Classification: DELETE**
- Signal generation pipeline (TimeSource → regime → allocator → cost → signal)
- Midas-specific
- DELETE

### signals/time_source.py
**Classification: REUSE (partial)**
- TimeSource abstraction (live vs backtest)
- Generic concept, extract for Argus use

### sleeves/__init__.py
**Classification: REUSE**
- ETF sleeve definitions (10 sleeves: equity, metals, bonds, REITs, etc.)
- Contains market structure knowledge, not trading logic
- MOVE to packages/argus-shared/

---

## Package: midas-backtest

### engine/walkforward.py
**Classification: REUSE (partial)**
- Walk-forward analysis framework
- Relevant for: "backtest this guideline rule against history"
- MOVE to packages/argus-shared/

### engine/cpcv.py
**Classification: REUSE (partial)**
- Combinatorial PCRT (cross-validated backtesting)
- Relevant for: "was this guideline robust across market conditions?"
- MOVE

### engine/degraded.py
**Classification: REUSE (partial)**
- Degraded performance analysis
- Relevant for: "stress-test guideline under adverse conditions"
- MOVE

### metrics/sharpe.py, benchmark.py, drawdown.py
**Classification: REUSE**
- Standard financial metrics
- MOVE to packages/argus-shared/

### reports/__init__.py
**Classification: REUSE (partial)**
- Report generation
- Relevant for: "generate guideline compliance report"
- MOVE

---

## Package: midas-broker

### ibkr/client.py
**Classification: REUSE**
- IBKR Python client
- Argus needs real-time portfolio positions from IBKR
- MOVE to packages/argus-broker/

### ibkr/oauth.py
**Classification: REUSE**
- IBKR OAuth flow
- MOVE

### orders/preview.py
**Classification: REPLACE**
- Order preview (estimate cost, fill probability)
- Midas-specific: "should I execute this trade?"
- For Argus: preview is "would this trade comply with guidelines?" — different logic
- REWRITE

### orders/submit.py
**Classification: REPLACE**
- Order submission
- Midas-specific trading
- DELETE

### orders/positions.py
**Classification: REUSE**
- Position fetching
- Essential for Argus: get current holdings to check against guidelines
- MOVE to packages/argus-broker/

### paper/__init__.py
**Classification: REUSE (partial)**
- Paper trading mode
- MOVE

---

## Package: midas-debate

### agent/debate.py
**Classification: REPLACE**
- Debate agent for discussing signals
- In Argus context: "Argus discusses guideline violations with user"
- REWRITE for Argus — different prompt, different tools, same LLM-first architecture
- KEEP architecture pattern (agent-reasoning.md rules)

### agent/signature.py
**Classification: REPLACE**
- Debate prompt/signatures
- REWRITE for Argus monitoring context

### grounding/verify.py
**Classification: REUSE (partial)**
- Response grounding verification
- Relevant for Argus: "is this guideline violation claim actually true?"
- ADAPT for Argus

### tools/data_tools.py
**Classification: REUSE (partial)**
- Data fetching tools for debate agent
- Many tools (get_portfolio, get_signal, etc.) are Midas-specific
- REWRITE for Argus tools (get_positions, check_guideline, get_benchmark)

### scenarios/counter.py
**Classification: REPLACE**
- Counter-argument scenarios for debate
- ADAPT for Argus: counter-argument for guideline violations

---

## Package: midas-governance

### assertions.py
**Classification: REUSE (partial)**
- Publisher isolation, audit immutability, broker isolation assertions
- Midas v1 assertions are procedural; Argus needs declarative policy
- MOVE and EXTEND

### audit/__init__.py
**Classification: REUSE**
- Immutable audit trail
- Essential for Argus

### envelopes/__init__.py
**Classification: REUSE (partial)**
- Governance envelope model
- For Argus: guideline constraint envelope (max drawdown, max sector weight, etc.)
- EXTEND

### migrations/
**Classification: REUSE (partial)**
- DB schema migrations
- Some are Midas-specific (signals, backtests), some are generic (users, audit)
- SPLIT: generic migrations move to Argus, Midas-specific stay in old/

---

## Apps: midas-api

### __main__.py
**Classification: REPLACE**
- 39 API routes, most Midas-specific (signals, backtests, debate)
- For Argus: monitoring routes (get_positions, check_guidelines, get_violations, alert_history)
- REWRITE

### handlers/signals.py
**Classification: DELETE**
- Midas signal endpoints
- DELETE

### handlers/regime.py
**Classification: REPLACE**
- Regime detection endpoints
- In Argus: regime is ONE input to guideline monitoring
- REWRITE as part of guideline monitoring

### handlers/backtests.py
**Classification: REUSE (partial)**
- Backtest run endpoints
- MOVE to Argus as-is for "backtest guideline rule"

### handlers/approvals.py
**Classification: REPLACE**
- Trade approval workflow
- In Argus: guideline violation acknowledgment workflow
- ADAPT

### handlers/debate.py
**Classification: REPLACE**
- Debate messaging
- REWRITE for Argus context

### handlers/account.py
**Classification: REUSE**
- Account management
- MOVE

### handlers/auth.py
**Classification: REUSE**
- JWT authentication
- MOVE

### handlers/notifications.py
**Classification: REUSE**
- Notification endpoints
- MOVE

### scheduler/escalation.py
**Classification: REUSE (partial)**
- Pending approval escalation
- For Argus: guideline violation escalation
- ADAPT

---

## Apps: midas-web

### All pages
**Classification: REPLACE**
- Dashboard, Signals, Approvals, Debate, Backtests, Audit, Settings
- Argus pages: Portfolio Monitor, Guideline Editor, Violation Alert, Audit Log, Settings
- Rewrite from scratch — different UX paradigm

### components/AuthBadge.tsx
**Classification: REUSE**
- Move to Argus

### lib/api.ts
**Classification: REPLACE**
- API client with Midas-specific endpoints
- Rewrite for Argus endpoints

---

## Apps: midas-mobile

### All screens
**Classification: REPLACE**
- Same as web: rewrite for Argus paradigm

### lib/api.ts
**Classification: REPLACE**
- Same as web

---

## Scripts

### scripts/seed_dev.py
**Classification: REUSE (partial)**
- Seed data with realistic ETF prices, signals, backtests
- For Argus: seed with portfolio positions, guideline templates, violation history
- ADAPT

### scripts/load_historical.py
**Classification: REUSE**
- Historical data loader
- MOVE

### scripts/migrate.py
**Classification: REUSE (partial)**
- DB migration runner
- SPLIT: generic schema moves to Argus

### scripts/start_api.py
**Classification: REUSE**
- Python path setup for all packages
- MOVE (generic launcher)

### scripts/run_backtest.py
**Classification: REUSE (partial)**
- MOVE for Argus "backtest guideline rule" feature

---

## Summary: File Migration Plan

### Move to old/midas/ (Midas-specific, never runs again)
- packages/midas-strategy/src/midas_strategy/{regime,allocator,signals/} (all)
- packages/midas-backtest/src/midas_backtest/ (all — backtest engine)
- packages/midas-debate/src/midas_debate/{agent/,scenarios/} (rewrite)
- packages/midas-broker/src/midas_broker/orders/{submit.py}
- packages/midas-governance/src/midas_governance/ (declarative policy model — REWRITE)
- apps/api/src/midas_api/handlers/{signals,regime,backtests}.py
- apps/api/src/midas_api/handlers/debate.py
- apps/web/src/app/{signals,approvals,backtests,debate}/
- apps/web/src/lib/api.ts (rewrite)
- apps/mobile/ (rewrite)
- scripts/seed_dev.py (adapt for Argus)

### Move to packages/argus-shared/ (extracted, reused)
- packages/midas-data/src/midas_data/{fabric,models/{market,portfolios,users,audit},sources,quality}
- packages/midas-strategy/src/midas_strategy/sleeves/ (ETF definitions)
- packages/midas-strategy/src/midas_strategy/cost/ (cost model formulas)
- packages/midas-backtest/src/midas_backtest/{metrics,engine/{walkforward,cpcv,degraded},reports}
- packages/midas-broker/src/midas_broker/ibkr/{client.py,oauth.py}
- packages/midas-broker/src/midas_broker/orders/positions.py
- packages/midas-broker/src/midas_broker/paper/
- packages/midas-governance/src/midas_governance/audit/
- packages/midas-governance/src/midas_governance/envelopes/ (adapt)
- packages/midas-debate/src/midas_debate/grounding/
- scripts/load_historical.py
- scripts/migrate.py
- scripts/start_api.py
- scripts/run_backtest.py

### New packages to create
- packages/argus-monitor/ — guideline monitoring engine
- packages/argus-policy/ — declarative policy model
- packages/argus-broker/ — IBKR integration (reuses midas-broker)
- packages/argus-debate/ — Argus discussion agent (reuses midas-debate pattern)
- apps/argus-api/ — new API server
- apps/argus-web/ — new Next.js frontend
