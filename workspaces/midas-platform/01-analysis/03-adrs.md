# Architecture Decision Records — Midas v1

Each ADR links to the research doc that justifies it. Status: PROPOSED pending red team.

## ADR-001: v1 operates under the US publisher's exemption (Lowe v. SEC)

**Context**: Autonomous per-user portfolio management requires an RIA registration that takes 6–12 months and significantly expands scope.
**Decision**: v1 ships as an impersonal publisher of model portfolios. No per-user personalization on the server. US-only at launch. UK/SG/EU geofenced.
**Consequences**:
- `signals` table has no `user_id` column. Structurally enforced.
- Cannot offer tax-loss harvesting, account-balance-aware recs, or personalized risk scoring in v1.
- User applies signals to their own IBKR account; user clicks every execution.
- Must publish on a regular cadence (weekly) to preserve "impersonal" characterization.
- Marketing copy must be carefully scrubbed; no "your" portfolio language on the signal server.
**Source**: `01-research/03-broker-and-regulatory.md`

## ADR-002: IBKR Client Portal Web API via OAuth

**Decision**: Client Portal Web API is the primary broker integration. Per-user local CP Gateway as fallback during private beta until IBKR OAuth production approval.
**Rejected**: TWS API (not multi-tenant), FIX CTCI (requires institutional master).
**Consequences**: OAuth production approval is a critical-path dependency. Begin the IBKR application conversation early.
**Source**: `01-research/03-broker-and-regulatory.md`

## ADR-003: Regime detection via weighted multi-signal ensemble

**Decision**: Ensemble of HY OAS (0.25), VIX3M backwardation (0.20), cross-sector PC1 variance (0.20), VIX level (0.10), 200d SMA persistence (0.10), 21d realized vol (0.10), 3m10y yield curve (0.05). Drawdown hard override at −8% soft / −12% hard halt. 2-day hysteresis.
**Rejected**: Pure HMM (too opaque for debate UX), pure VIX threshold (too brittle), pure trend filter (late to turbulent).
**Source**: `01-research/02-strategy-methodology.md`

## ADR-004: Adaptive Asset Allocation as primary allocator

**Decision**: AAA = weekly top-K momentum ranking (K=6 normal, K=4 cautious, K=0 turbulent) → min-variance within selected set → vol-target (14% normal / 8% cautious / cash turbulent). L1 turnover penalty calibrated to the cost function. 10-day min-hold. 10%/week weight cap. HRP fallback on degenerate signal.
**Source**: `01-research/02-strategy-methodology.md`

## ADR-005: Single workflow, time-source injected, for backtest/live parity

**Decision**: One Core SDK workflow runs both backtest and live. The only variable is a `TimeSourceNode` (historical clock vs system clock). Every signal/allocator/cost node is byte-identical across surfaces.
**Enforcement**: Tier-2 regression tests on real Postgres gate every merge. Drift is a release blocker.
**Source**: `01-research/06-framework-architecture.md`

## ADR-006: Postgres 16 + TimescaleDB + pgvector, single instance via DataFlow

**Decision**: One PG instance, DataFlow-managed pool, Timescale hypertables for price/bar data, pgvector for news embeddings, standard tables for portfolios and audit. Redis hot cache. S3 cold archive.
**Rejected**: ClickHouse (operational burden), DuckDB-as-store (not multi-tenant), schema-per-user (breaks shared fabric).
**Source**: `01-research/04-data-fabric.md`

## ADR-007: Next.js (web) + React Native Expo (mobile) + shared TypeScript packages

**Decision**: Next.js for web, React Native Expo for iOS/Android, shared `packages/core` (domain types) and `packages/tokens` (design).
**Rejected**: Flutter (web rendering trails HTML for financial UIs + debate screen is text-heavy).
**Source**: `01-research/05-uiux-design.md`

## ADR-008: Kaizen-based debate agent with hard grounding contract

**Decision**: Single `DebateAgent` with a `DebateSignature` whose output fields include `cited_ids: list[CitationRef]`. An `ungrounded_claims` field must be empty or the response is rejected before reaching the user. Tools are dumb data endpoints only (`fetch_signal`, `fetch_backtest`, `fetch_cost_model`, `fetch_current_recommendation`, `fetch_news_by_id`). NO keyword routing. NO intent classification in Python. LLM-first per `rules/agent-reasoning.md`.
**Source**: `01-research/06-framework-architecture.md`, `rules/agent-reasoning.md`

## ADR-009: PACT envelopes for publisher/subscriber separation

**Decision**: Two PACT operating envelopes: (a) Publisher envelope — produces signals, has no read access to `users.*`; (b) Subscriber envelope — reads signals and user preferences, can never modify signals. The Postgres role separation is auto-derived from the envelope definition.
**Gap**: PACT does not yet auto-generate `GRANT`/`REVOKE` SQL from envelopes; Midas will hand-maintain migrations in v1 and propose the primitive upstream.
**Source**: `01-research/06-framework-architecture.md`

## ADR-010: Backtest horizon 2000-present with CPCV + embargo + Deflated Sharpe

**Decision**: Backtest from 2000-01-01 using point-in-time ETF universe (EODHD delisted-tickers ingestion). Walk-forward + Combinatorial Purged Cross-Validation with embargo. Report Deflated Sharpe and Probability of Backtest Overfitting (PBO). No single-split results.
**Source**: `01-research/02-strategy-methodology.md`, `01-research/04-data-fabric.md`
