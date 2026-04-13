# Plan 01 — System Architecture

**Workspace**: `midas-platform`
**Phase**: 01-analyze / 02-plans
**Date**: 2026-04-09
**Status**: Proposed (gates to `/todos`)
**Traceability anchor**: Every component cites its source in the analysis.

---

## 0. Guiding invariants

These invariants come out of the analysis and constrain every choice below. They are **non-negotiable** — any component design that conflicts with them is rejected before it is written.

1. **Impersonal publisher posture** — the server never personalises signals. The same bytes go to every subscriber. `/v1/portfolios/{id}/signals/latest` must stay CDN-cacheable. [03-product-model §1.4], [02-value-proposition §6 condition 3], [01-research/03 §3.1 Lowe]
2. **No custody** — Midas never takes IBKR money-movement scope, never holds client funds, and never deducts fees from IBKR. Billing goes through a separate Stripe channel. [01-research/03 §5.1], [VP5]
3. **Backtest ↔ live parity** — the same Core SDK workflow graph runs in backtest and live. Cost model is inside the backtest loop, not applied post-hoc. [01-research/06 §3], [VP2]
4. **LLM narrates, allocator decides** — the debate LLM reads signals and explains. It does not route, classify, or choose weights. No if/else routing on user input. [`rules/agent-reasoning.md`], [VP3], [USP3 conditional]
5. **Zero-stub, zero-fallback, zero-workaround** per `rules/zero-tolerance.md` — every endpoint returns real data, every service is functional, SDK bugs get issues not workarounds.
6. **Framework-first** per `rules/agents.md` — DataFlow for DB, Nexus for API, Kaizen for LLM agents, PACT for approval envelopes, MCP for data-source integrations. No raw SQL, no raw FastAPI, no hand-rolled agents.

---

## 1. Component inventory (by Kailash framework)

| # | Component                      | Framework          | Purpose                                                                                  |
| - | ------------------------------ | ------------------ | ---------------------------------------------------------------------------------------- |
| 1 | Data Fabric                    | **DataFlow** + MCP | Store-once cache of EODHD/Yahoo/Perplexity/FRED/CBOE; multi-tenant role isolation        |
| 2 | Regime Detection Service       | Core SDK           | Multi-signal ensemble; pure deterministic; first-class signal objects                    |
| 3 | Strategy Engine                | Core SDK           | Portfolio construction, adaptive asset allocation, HRP fallback, vol targeting           |
| 4 | Backtest Engine                | Core SDK           | Purged CPCV + walk-forward + multi-sub-horizon; **cost model inside the loop**           |
| 5 | Transaction Cost Model         | Core SDK           | IBKR Pro tiered + SEC §31 + FINRA TAF + half-spread + Almgren-Chriss impact + gap        |
| 6 | Proposal Engine                | Core SDK           | Turns strategy output into rebalance proposals with cost/risk/confidence                 |
| 7 | Debate LLM Service             | **Kaizen**         | LLM-first narration grounded in live signal values + Perplexity news                     |
| 8 | IBKR Integration               | MCP + Core SDK     | OAuth (trading + read scopes only), paper-first, order tickets                           |
| 9 | Approval / Execution Gateway   | **PACT**           | Per-trade envelopes, biometric gate, idempotent scheduler, tamper-evident audit chain    |
| 10 | Signals API / App BFF         | **Nexus**          | Multi-channel (HTTP/API, WebSocket push, CLI) — same surface for web + mobile            |
| 11 | Web shell                     | React + Shadcn     | Next.js + Shadcn UI, six primary flows from `03-user-flows/01`                           |
| 12 | Mobile shell                  | Flutter            | iOS + Android parity, push → biometric approve in <90s                                   |
| 13 | Notification fabric           | MCP (APNS/FCM)     | Regime-flip and approval-pending pushes; never marketing                                 |
| 14 | Billing                       | Stripe via MCP     | Subscription only; never through IBKR; Observer/Operator/Principal tiers                 |

---

## 2. Component interaction diagram

```
                                 +-------------------------------+
                                 |       Data Fabric (DF)        |
                                 |  DataFlow + MCP adapters      |
                                 |  EODHD  Yahoo  Perplexity     |
                                 |  FRED   CBOE  (share schema)  |
                                 +---------------+---------------+
                                                 |
                 +-------------------------------+-------------------------------+
                 |                               |                               |
                 v                               v                               v
       +--------------------+         +---------------------+         +---------------------+
       | Regime Detection   |         | Transaction Cost    |         | News / Context      |
       | (Core SDK)         |         | Model (Core SDK)    |         | (Perplexity cache)  |
       |  HY OAS, VIX3M,    |         |  IBKR Pro tiered    |         |  grounded citations |
       |  PC1, drawdown     |         |  SEC/FINRA, impact  |         |  for debate only    |
       +----+---------------+         +----------+----------+         +----------+----------+
            |                                    |                               |
            |                                    |                               |
            |  regime_state          cost_bps    |                               |
            v                                    v                               |
       +----------------------------------------------+                          |
       |            Strategy Engine (Core SDK)        |                          |
       |  Adaptive Asset Allocation  HRP fallback     |                          |
       |  vol target  L1 turnover penalty (in bps)    |                          |
       +-----------------------+----------------------+                          |
                               |                                                 |
                               v                                                 |
                    +-----------------------+                                    |
                    |  Backtest Engine      |                                    |
                    |  (Core SDK)           |                                    |
                    |  CPCV + walk-forward  |                                    |
                    |  cost model INSIDE    |                                    |
                    |  regime-conditional   |                                    |
                    +-----------+-----------+                                    |
                                |                                                |
                                v                                                |
                    +-----------------------+                                    |
                    |  Proposal Engine      |                                    |
                    |  (Core SDK)           |                                    |
                    |  cost + risk + conf   |                                    |
                    +-----------+-----------+                                    |
                                |                                                |
                                |  same bytes to all                             |
                                v                                                |
                    +---------------------------------+                          |
                    |   Signals API (Nexus)           |                          |
                    |   /v1/portfolios/{id}/signals   |                          |
                    |   CDN-cacheable, impersonal     |                          |
                    +----+------------------+---------+                          |
                         |                  |                                    |
                         v                  v                                    |
               +------------------+   +-------------------+                      |
               |  Web shell       |   |  Mobile shell     |                      |
               |  (React+Shadcn)  |   |  (Flutter)        |                      |
               +--------+---------+   +---------+---------+                      |
                        |                       |                                |
                        |                       v                                |
                        |         +-----------------------------+                |
                        |         |  Debate LLM (Kaizen)        |<---------------+
                        |         |  grounded in signal stack   |
                        |         |  LLM narrates, not decides  |
                        |         +-----------+-----------------+
                        |                     |
                        +---------+-----------+
                                  |
                                  v
                    +--------------------------+
                    |  Approval / Execution    |
                    |  Gateway (PACT)          |
                    |  biometric + envelopes   |
                    |  idempotent scheduler    |
                    |  audit chain store       |
                    +------------+-------------+
                                 |
                                 v
                    +--------------------------+
                    |   IBKR (OAuth scoped)    |
                    |   trading + read only    |
                    |   NO money-movement      |
                    +--------------------------+
```

---

## 3. Component contracts

Each contract lists: purpose, framework, inputs, outputs, invariants, traceability.

### 3.1 Data Fabric — DataFlow + MCP

- **Purpose**: Store-once-reuse cache for all market data, news, and macro series. [brief §9], [VP4], [01-research/04]
- **Framework**: DataFlow for Postgres (+ Timescale for tick/bars, + pgvector for news embeddings); MCP servers wrap EODHD/Yahoo/Perplexity/FRED/CBOE as tool endpoints.
- **Inputs**: EODHD REST, Yahoo (yfinance), Perplexity search, FRED series, CBOE VIX EOD.
- **Outputs**: Cache-hit reads for every downstream component; guaranteed point-in-time correctness (as-of timestamps on every row).
- **Invariants**:
  - Single Postgres instance, single pool — enforced by `rules/dataflow-pool.md`.
  - Publisher Postgres role has NO `SELECT` on `users.*` — structural enforcement of the publisher posture [03-product-model §3.3].
  - All writes atomic per `rules/zero-tolerance.md`.
  - Backfill 2000→present per [A4].
- **Traceability**: [brief §9], [A4], [01-research/04 §1–§6], [03-product-model §4.1], [VP5].

### 3.2 Regime Detection Service — Core SDK

- **Purpose**: Emit a regime label (`calm_trend | normal | cautious | turbulent`) plus the contributing signal stack, so the Strategy Engine and UI can both consume it. [VP1], [USP1]
- **Framework**: Core SDK workflow; pure deterministic; **no LLM** in the decision path — regime detection is numeric per [`rules/agent-reasoning.md`].
- **Inputs**: HY OAS (FRED), VIX level + VIX3M term structure (CBOE), realized vol (multi-window, fabric), cross-sector PC1 variance, drawdown from trailing peak, yield curve shape.
- **Outputs**: `RegimeState(label, confidence, contributing_signals[], flipped_at)` persisted via DataFlow.
- **Invariants**:
  - Signals are first-class objects (not dict keys) — explicit schema and versioned.
  - **Debounce / hysteresis**: regime cannot flip more than once per N trading days, ensuring the "freeze on turbulent" gate does not whipsaw [VP1 strength caveat].
  - Every flip writes an immutable audit row with the full signal snapshot.
  - Signal definitions versioned so backtests remain reproducible.
- **Traceability**: [A3], [brief §2], [01-research/02 §2.9], [VP1], [USP1], [03-product-model §4.1].

### 3.3 Strategy Engine — Core SDK

- **Purpose**: Turn regime + fabric data into target portfolio weights for the publisher's 1–3 model portfolios. Same bytes for every subscriber.
- **Framework**: Core SDK custom nodes.
- **Inputs**: Regime state, covariance matrix, momentum/trend signals, carry, vol, 8-sleeve universe (ETFs + precious metals + govt bonds + IG corp + REITs + commodities + dividend + EM) [brief §4].
- **Outputs**: `TargetPortfolio(weights, regime_conditional_backtest_ref, generated_at)`.
- **Invariants**:
  - Weekly cadence cap [brief §4, A6]; regime-dependent within cap.
  - L1 turnover penalty calibrated in bps against the cost model [VP4, VP6].
  - Vol targeting + sleeve caps from the risk profile (client-side filter, not server mutation).
  - 80% of the code is the reusable core per the 80/15/5 decomposition [03-product-model §4.1].
- **Traceability**: [brief §4], [01-research/02 §3–§4], [VP6], [03-product-model §4.1].

### 3.4 Backtest Engine — Core SDK

- **Purpose**: Evaluate the strategy under every historical regime with honest statistics, and produce the per-trade backtest distribution shown on every approval card [VP2, USP2].
- **Framework**: Core SDK; shares node graph with live (parity invariant).
- **Inputs**: Fabric history 2000→present [A4], strategy engine, cost model.
- **Outputs**: `BacktestRun(run_id, sub_horizon, regime_bucket, sharpe, max_dd, cost_drag, dsr, pbo, equity_curve)`.
- **Invariants**:
  - Purged k-fold CPCV with 756-day embargo [01-research/02 §6].
  - Walk-forward with expanding-window retraining [VP2].
  - Multi-sub-horizon: 1y / 3y / 5y / 10y rolling + per-crisis stress windows [brief §6, A4].
  - **Transaction cost model is inside the backtest loop**, not applied post-hoc [brief §7, VP4].
  - Deflated Sharpe Ratio + Probability of Backtest Overfitting reported alongside every run.
  - Regime-conditional: per-regime Sharpe, per-regime max DD.
- **Traceability**: [brief §6, §7], [A4], [01-research/02 §6], [VP2, VP4], [USP2].

### 3.5 Transaction Cost Model — Core SDK

- **Purpose**: Produce an honest bps cost estimate for any candidate trade, used both in the backtest loop and on the approval card. [brief §7], [VP4]
- **Framework**: Core SDK custom node.
- **Inputs**: Order ticket (symbol, side, notional), current VIX, IBKR commission schedule, SEC §31 / FINRA TAF tables, historical spread fabric.
- **Outputs**: `CostBreakdown(commission, sec_fee, finra_taf, half_spread, impact, gap_risk, total_bps)`.
- **Invariants**:
  - **Cost model is first-class** — every other component consumes it via the same node, never a private copy.
  - Weekly calibration loop against realized IBKR fills catches backtest-vs-live drift [VP4 mechanism].
  - Almgren-Chriss square-root impact with a VIX-scaled half-spread.
- **Traceability**: [brief §7], [01-research/03 §broker], [01-research/02 §5.7], [VP4].

### 3.6 Proposal Engine — Core SDK

- **Purpose**: Convert a target portfolio delta into an executable proposal with everything the approval card needs on one mobile screen.
- **Framework**: Core SDK.
- **Inputs**: Current vs target weights (delta computed client-side for personal use; server-side only for the publisher reference portfolio), cost breakdown, regime state, backtest distribution ref.
- **Outputs**: `Proposal(proposal_id, trades[], expected_cost_bps, risk_delta, confidence, why_three_bullets, backtest_ref)`.
- **Invariants**:
  - No proposal fires unless expected improvement > 2× round-trip cost [VP4 mechanism].
  - 10-day minimum hold on sold sleeves; 10% weight-change cap per sleeve per week [VP6, 01-research/02 §4.3].
  - Three bullets of "why" are signal citations, not narrative.
- **Traceability**: [VP4, VP6], [01-primary-flows Flow 3 approval], [USP2].

### 3.7 Debate LLM Service — Kaizen

- **Purpose**: The user asks "why gold this week not TLT?" and gets a plain-language answer that cites the exact signal values. [VP3], [USP3]
- **Framework**: Kaizen `BaseAgent` with a `Signature` that takes the signal stack, regime label, momentum ranks, covariance snapshot, cost estimate, and relevant Perplexity news snippets as inputs, and returns a grounded explanation.
- **Inputs**: Live signal snapshot + proposal + user question + cached news (Perplexity).
- **Outputs**: `DebateTurn(answer, citations[], confidence, counter_scenario_ref?)`.
- **Invariants**:
  - **LLM-first reasoning** per [`rules/agent-reasoning.md`]: no if-else routing, no keyword matching, no regex classification, no dispatch tables. The LLM IS the router, classifier, extractor, and evaluator.
  - Every numeric claim must be cited to a signal ID, backtest run ID, or cost model output — unattributed numbers are blocked by a grounding contract [01-research/06 §2.2].
  - Sycophancy guard: when the user pushes back, return a counter-scenario, not capitulation [01-research/05 §4.2].
  - The LLM **cannot** write to allocator state. Read-only on all fabric tables.
- **Traceability**: [brief §8 "debate with the AI"], [VP3], [USP3 conditional], [`rules/agent-reasoning.md`], [01-primary-flows Flow 5], [05-ai-interaction-patterns].

### 3.8 IBKR Integration — MCP + Core SDK

- **Purpose**: Fetch read-only portfolio + place approved orders, paper-first.
- **Framework**: MCP server wrapping IBKR OAuth/Client Portal API, consumed by Core SDK nodes.
- **Invariants**:
  - OAuth scopes: `trading + read` only. **No money-movement scope** [VP5, 01-research/03 §5.1].
  - Paper-first 14 days, non-bypassable in the UI [01-primary-flows Flow 1 Step 4].
  - Build fails if any code path requests money-movement scope [03-product-model §5.4].
- **Traceability**: [brief §3], [A2], [VP5], [01-research/03 §1.5].

### 3.9 Approval / Execution Gateway — PACT

- **Purpose**: Every trade passes through a per-trade PACT envelope + biometric gate + idempotent scheduler + audit chain.
- **Framework**: PACT envelopes for constraint enforcement (Financial, Operational, Temporal, Data Access, Communication — the canonical five per `rules/terrene-naming.md`).
- **Invariants**:
  - **Monotonic tightening**: user's configured envelope (approval threshold, quiet hours, concentration cap) is stricter than the publisher's default, never wider [`rules/pact-governance.md`].
  - **Fail-closed**: any error → BLOCKED, never ALLOWED [`rules/pact-governance.md`].
  - Idempotent scheduler so a retry never double-publishes [01-research/06 §1].
  - Content-hashed append-only audit chain [03-product-model §4.1].
  - Biometric confirm via Face ID / Touch ID / passkey — non-bypassable [01-research/05 §3.3].
- **Traceability**: [brief §2], [A2], [03-product-model §4.1, §5.4], [01-primary-flows Flow 3], [`rules/pact-governance.md`].

### 3.10 Signals API / BFF — Nexus

- **Purpose**: One API surface served across web, mobile, and MCP — same workflow on every channel.
- **Framework**: Nexus.
- **Endpoints** (illustrative, finalized in `/todos`):
  - `GET /v1/portfolios/{id}/signals/latest` — impersonal, CDN-cacheable, the legal tell [03-product-model §1.4].
  - `GET /v1/regime/current` — regime label + contributing signals.
  - `POST /v1/proposals/{id}/approve` — biometric-gated, idempotent, PACT-checked.
  - `POST /v1/debate` — Kaizen debate agent entry point.
  - `GET /v1/backtests/{run_id}` — per-trade backtest distribution [VP2].
- **Invariants**:
  - Any response that varies per user is outside `/v1/portfolios/...` and goes through the `users` schema role.
  - Rate limiting and auth per `rules/security.md`.
- **Traceability**: [brief §8 multi-channel], [03-product-model §1.4], [VP5], [01-research/06 §6.2].

### 3.11 Web shell — React + Shadcn

- **Purpose**: Desktop/tablet experience for the six primary flows [01-primary-flows].
- **Framework**: Next.js + Shadcn UI + Tailwind; calls Nexus API.
- **Detail in**: `02-plans/04-frontend.md`.

### 3.12 Mobile shell — Flutter

- **Purpose**: iOS + Android parity with push-to-approve <90s.
- **Framework**: Flutter; calls Nexus API.
- **Detail in**: `02-plans/04-frontend.md`.

### 3.13 Notification fabric — MCP (APNS/FCM)

- **Purpose**: Regime-flip + approval-pending pushes. Non-marketing, non-gamified [03-product-model §3.2].
- **Traceability**: [01-research/05 §5.3], [VP1, USP1], [01-primary-flows Flow 3].

### 3.14 Billing — Stripe via MCP

- **Purpose**: Subscription billing entirely separate from IBKR.
- **Invariant**: Billing **never** flows through IBKR to avoid inadvertent custody [01-research/03 §5.1], [VP5].

---

## 4. Multi-tenant data isolation (publisher ↔ user split)

This is the architectural spine of the Lowe publisher posture and must not be weakened.

```
+------------------------------------------------+
|                  Postgres                      |
|                                                |
|  +---------------------+  +------------------+ |
|  |  publisher schema   |  |   users schema   | |
|  |  (read by publisher |  |  (read by user   | |
|  |   role)             |  |   role)          | |
|  |                     |  |                  | |
|  |  market_data        |  |  users           | |
|  |  news_cache         |  |  subscriptions   | |
|  |  regime_history     |  |  notification_pr | |
|  |  backtest_runs      |  |  audit_user      | |
|  |  cost_calibration   |  |  debate_history  | |
|  |  portfolio_signals  |  |  ibkr_oauth_enc  | |
|  +---------------------+  +------------------+ |
|                                                |
|  publisher role: NO SELECT on users.*          |
|  user role:      NO SELECT on publisher mutation fns |
+------------------------------------------------+
```

**Structural enforcement**: the publisher role is granted only SELECT on `publisher.*` and INSERT on the signals output. It has **NO privileges** on `users.*`. A developer literally cannot personalise a signal because the publisher process cannot read `users.*` [03-product-model §3.3].

Enforced via DataFlow model metadata per `rules/dataflow-pool.md`.

---

## 5. Security / trust posture

- Secrets from `.env` only, loaded per `rules/env-models.md`; no hardcoded API keys, no hardcoded model strings.
- Parameterized queries only (DataFlow enforces).
- IBKR OAuth tokens encrypted at rest (per-user key).
- Audit chain content-hashed per `rules/trust-plane-security.md` (atomic writes, NOFOLLOW, HMAC constant-time compare).
- PACT fail-closed on any error [`rules/pact-governance.md`].
- Biometric non-bypassable [01-research/05 §3.3].

---

## 6. Cross-references

- `briefs/01-user-brief.md` — all §1–§9
- `briefs/02-assumptions.md` — A1–A7
- `01-analysis/01-research/01..06` — landscape, strategy methodology, broker/regulatory, data fabric, UI/UX, framework architecture
- `01-analysis/02-value-proposition.md` — VP1–VP6, USP1–USP4, Conditional GO
- `01-analysis/03-product-model.md` — shared-fabric single-publisher model, 80/15/5, three pivots
- `03-user-flows/01..05` — six primary flows, critical decisions, empty/error states, IA, AI interaction
- `.claude/rules/` — agent-reasoning, agents, autonomous-execution, pact-governance, dataflow-pool, zero-tolerance, trust-plane-security, security, independence

---

## 7. Open items for `/todos`

1. Finalize the exact Nexus route table from the illustrative list in §3.10.
2. Decide whether the `/v1/portfolios/.../signals/latest` endpoint is served from a CDN edge or origin-cached (both preserve the legal tell; CDN is cheaper at scale).
3. Decide Flutter vs React Native for mobile — plan assumes Flutter because the repo has a flutter-specialist available; final call owned by `/todos`.
4. Confirm whether Operator/Principal tier knobs land in v1 or v2 [03-product-model §7 Q5].
