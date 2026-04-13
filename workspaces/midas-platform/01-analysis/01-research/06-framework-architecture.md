# Framework Architecture — Midas Platform

**Workspace**: `midas-platform`
**Phase**: 01-analysis / 01-research
**Date**: 2026-04-09
**Scope**: Map Midas components to Kailash frameworks (Core SDK, DataFlow, Nexus, Kaizen, PACT, kailash-ml, kailash-align), enforce the LLM-first debate agent contract, guarantee backtest↔live parity, and — critically — enforce the **impersonal publisher** architecture that `03-broker-and-regulatory.md` says is the legal prerequisite for US v1 under *Lowe v. SEC*.

This document is prescriptive. Every component decision is grounded in what Kailash actually offers (the specialist agents at `.claude/agents/frameworks/`) and the constraints the earlier research docs established. Where a capability is genuinely missing, it is flagged in §9 rather than hand-waved.

---

## 1. Component → Framework Mapping

Midas is a workflow problem (ingest → compute → decide → publish → serve) with a governance layer on top. That lines up with the Kailash layering: **DataFlow for storage, Core SDK for compute workflows, Kaizen for the one LLM surface, Nexus for distribution, PACT for the envelope split between server-impersonal and client-personal concerns.**

| # | Component | Framework | Rationale | What could go wrong |
|---|---|---|---|---|
| 1 | **Data fabric ingestion** (EODHD, Yahoo, Perplexity, FRED, IBKR bars) | **Core SDK workflows + DataFlow writes** | Each source is a scheduled Core SDK workflow: one `HTTPRequestNode`/custom `EODHDFetchNode` → transformation nodes → DataFlow bulk write into `prices_eod`, `macro_series`, `news_items`. Scheduling via `AsyncLocalRuntime` inside a weekly scheduler. DataFlow provides the typed models and bulk-create nodes (`PriceEODBulkCreateNode`) for free; we do not hand-write SQL. | EODHD silently restates a bar (§4 caveat in `04-data-fabric.md`). Mitigation: nightly diff job comparing `ingested_at` snapshots, writing `adjustment` rows through DataFlow. The workflow MUST fail closed on fetch error — no silent "use yesterday's bar". |
| 2 | **Shared multi-tenant DB** (Postgres 16 + Timescale + pgvector) | **DataFlow (single instance)** | DataFlow is Postgres-native, owns one `ConnectionManager` and one pool (`rules/dataflow-pool.md` — single source of truth for `get_pool_size()`). Timescale and pgvector are Postgres extensions; DataFlow treats the hypertables as normal models with a custom `indexes` hint. `@db.model` decorators generate 9 nodes per table automatically. Row-level security enforced at Postgres level for the per-tenant subset. | Multiple DataFlow instances drift pool sizes (the crisis documented in `rules/dataflow-pool.md`). Mitigation: **one** `DataFlow()` in the process, injected into all subsystems via the `runtime=` parameter so there are no orphan runtimes. |
| 3 | **Backtest engine** | **Core SDK workflow (shared with live)** | Single `WorkflowBuilder` graph parameterised on a `TimeSource` node (historical replay vs live clock). See §3. Reuses the *same* signal/allocator/cost nodes as the live scheduler. | Parity drift — the single biggest backtest failure mode. Mitigation: the node graph is identical; what differs is only the `TimeSource` node and the sink (backtest sink writes to `backtest_runs`; live sink writes to `signals`). Enforced structurally by node reuse (§3). |
| 4 | **Regime detection ensemble** (HY OAS, VIX3M, PC1, VIX, 200d SMA, RV, yield curve, drawdown override) | **Core SDK workflow with kailash-ml nodes** | Each signal is a pure node with a deterministic numeric output in `{-1, 0, +1}`. Composition is a `WeightedEnsembleNode` producing `{Normal, Cautious, Turbulent}`. The drawdown override is a `HardOverrideNode` that post-dominates the ensemble. kailash-ml is used for the HMM diagnostic overlay (§2.3 of `02-strategy-methodology.md`) as a non-gating label only. | An LLM is tempted to "help reason about the regime". BLOCKED by `rules/agent-reasoning.md`: regime classification is numeric, deterministic, and lives outside Kaizen. The LLM *explains* the regime in the debate surface but never *decides* it. |
| 5 | **Allocator** (Adaptive Asset Allocation, top-K momentum + min-var + vol-target + L1 turnover penalty) | **Core SDK custom node (`AdaptiveAllocatorNode`)** | One custom node, stateless, takes `(momentum_scores, covariance_matrix, regime_label, previous_weights, cost_table)` and returns `target_weights`. Fallback HRP is a sibling node (`HRPAllocatorNode`) selected by a `SwitchNode` on the signal-degeneracy check. Both are pure Python wrapping `numpy`/`cvxpy`. | Numerical instability on ill-conditioned covariance. Mitigation: shrinkage estimator (Ledoit-Wolf) inside the node; falls back to HRP deterministically if the condition number exceeds a threshold — this is a numerical fallback, not an error-hiding fallback (`rules/zero-tolerance.md` Rule 3). |
| 6 | **Strategy scheduler** (weekly cadence, triggered at US market close) | **Core SDK + Nexus cron channel** | Nexus supports scheduled workflow execution. The weekly job runs a single Core SDK workflow: `IngestLatest → ComputeSignals → RunRegime → RunAllocator → PriceCostModel → PublishSignals → AuditWrite`. The workflow is idempotent by `(model_portfolio_id, rebalance_ts)`. | Scheduler runs when EODHD has not yet published the close. Mitigation: the `EODHDFetchNode` has a *data-freshness gate* — it aborts the workflow (fail-closed) if the latest bar `ts` is not the expected session close. Regime becomes "unknown" → no new recommendation published. This is the correct degradation; see §7. |
| 7 | **Signal broadcast API** (the IMPERSONAL publisher model) | **Nexus API channel fronting a DataFlow read** | The published artefact is `(model_portfolio_id, rebalance_ts, target_weights, regime_label, cost_estimate_per_sleeve, signal_explainer_refs[])`. The API is `GET /v1/portfolios/{id}/signals/latest` and `GET /v1/portfolios/{id}/signals/history`. These endpoints read from a table that has **no `user_id` column**. The same bytes go to every subscriber. See §6. | Accidental personalisation — e.g. "show this signal only if user's balance > $X". The schema must make that a compile-error, not a policy violation. See §6. |
| 8 | **Web + mobile gateway** (Nexus fronting Next.js + React Native) | **Nexus (API + WebSocket channels)** | Nexus runs the server-side API, auth, subscription, and session state. Next.js and React Native are thin clients that call the Nexus API. Nexus's unified session across API/WebSocket gives the "debate chat" streaming a natural home. | Nexus is new territory for a mobile gateway — confirm with `nexus-specialist`. Fallback: Nexus as the API tier, native FCM/APNS for push. |
| 9 | **Debate-with-AI conversational agent** | **Kaizen (strict LLM-first, single `DebateAgent`)** | One Kaizen `BaseAgent` with a rich `Signature`; tools are dumb data endpoints (fetch-signal-by-id, fetch-backtest-run-by-id, fetch-current-recommendation, fetch-cost-model-output, fetch-regime-snapshot). The LLM does ALL routing, extraction, and evaluation. See §2 for the signature shape. | Developer reflex to pre-route "is this question about gold" with regex. BLOCKED by `rules/agent-reasoning.md`; enforced in code review by kaizen-specialist. |
| 10 | **Auth, subscription, user accounts** | **Nexus + DataFlow (per-tenant schema cluster)** | Users, subscriptions, Stripe linkage, notification preferences live in DataFlow models *under a separate schema namespace* (`users`, `subscriptions`, `notification_prefs`). They are never joined to `signals`. See §6. | Joining `users` to `signals` to "customise". Mitigation: PACT envelope (§5) + SQL grants that deny the signals role from reading `users.*`. |
| 11 | **News ingestion + caching** (Perplexity → pgvector) | **Core SDK workflow + DataFlow (`news_items` with `VECTOR(1536)`)** | A scheduled workflow queries Perplexity `sonar`/`sonar-pro`, embeds headlines via an `EmbeddingNode`, writes into `news_items` with pgvector HNSW index. The DebateAgent uses this as a *tool* (retrieval by semantic similarity + temporal decay). | Perplexity rate limit causes cache poisoning ("use stale news forever"). Mitigation: the tool returns news with `fetched_at` and `relevance_decay` fields; the LLM is told in its signature to surface staleness to the user. Fail-closed if news is >24h old in a Cautious/Turbulent regime. |
| 12 | **Audit trail** (immutable, every signal value, recommendation, click) | **DataFlow append-only tables + EATP chain-store (optional hash-linked)** | `audit_log` is a DataFlow append-only hypertable. Every published signal, every tool call the DebateAgent makes, every approval click on the client side (POSTed back to the server) is logged with a content hash. For cryptographic tamper-evidence (useful when Midas becomes an RIA in v2 and SEC exams begin), wrap the write in an EATP-style chain store — each record carries a hash of the previous record. Today the SDK's `src/kailash/trust/chain_store/` is the nearest primitive. | Audit writes blocking the hot path. Mitigation: the audit write is a sink node that fans out asynchronously; the publish workflow is idempotent on `rebalance_ts` so replay is safe. |

---

## 2. LLM-First Enforcement — The DebateAgent

The debate surface is the USP (`05-uiux-design.md` §1). It is also the single most tempting place to write deterministic code that violates `rules/agent-reasoning.md`. This section is the contract.

### 2.1 Tools are dumb data endpoints

Every tool below takes an ID and returns data. None contains `if`, `match`, or branching that influences the conversation.

- `fetch_signal_by_id(signal_id: str) -> SignalRecord` — returns the published signal row (weights, regime, timestamp, explainer refs).
- `fetch_backtest_run_by_id(run_id: str) -> BacktestRun` — returns equity curve, drawdowns, CPCV distribution, per-crisis stress windows.
- `fetch_current_recommendation(model_portfolio_id: str) -> Recommendation` — latest published `(target_weights, regime_label)`.
- `fetch_cost_model_output(signal_id: str, sleeve: str) -> CostBreakdown` — commission, reg fee, half-spread, impact, gap risk per leg.
- `fetch_regime_snapshot(ts: datetime) -> RegimeSnapshot` — the ensemble inputs (HY OAS, VIX3M ratio, PC1 variance, …) at a given timestamp.
- `fetch_news_by_similarity(query_text: str, lookback_days: int, top_k: int) -> list[NewsItem]` — pgvector KNN with temporal decay applied server-side numerically (not a decision).
- `fetch_counterfactual_backtest(signal_id: str, override: dict) -> BacktestRun` — "what if I held SPY instead of GLD" — runs a short incremental backtest using the same Core SDK workflow with an override.

That last tool is the one the user actually came for. Note that the LLM cannot invent the override; the LLM *decides* which override to request based on what the user said, and the tool executes it deterministically.

### 2.2 The Kaizen signature

One signature. Rich output. The LLM does the routing, extraction, evaluation — all of it.

```python
from kaizen.core import BaseAgent, Signature, InputField, OutputField

class DebateSignature(Signature):
    """User is debating a proposed or recent Midas recommendation.
    Reason over the signal stack, the backtest evidence, and the news context
    to produce a grounded, cited, plain-language response.
    """
    user_message: str = InputField(description="The user's question or challenge")
    current_recommendation_id: str = InputField(description="The recommendation under discussion")
    conversation_history: list[dict] = InputField(description="Prior turns in this debate")

    reasoning_trace: str = OutputField(description="Step-by-step reasoning before answering")
    tool_calls_made: list[dict] = OutputField(description="Which dumb data tools were invoked and why")
    cited_signal_ids: list[str] = OutputField(description="Every signal referenced, by ID")
    cited_backtest_run_ids: list[str] = OutputField(description="Every backtest referenced, by ID")
    counterfactual_requested: bool = OutputField(description="Whether the user asked 'what if'")
    counterfactual_override: dict = OutputField(description="If yes, the weight override to test")
    response_plain_language: str = OutputField(description="The answer to show the user")
    confidence: str = OutputField(description="high, medium, low — the LLM's self-assessed grounding")
    ungrounded_claims: list[str] = OutputField(description="Claims made without a backing tool result")

class DebateAgent(BaseAgent):
    signature = DebateSignature
    tools = [fetch_signal_by_id, fetch_backtest_run_by_id,
             fetch_current_recommendation, fetch_cost_model_output,
             fetch_regime_snapshot, fetch_news_by_similarity,
             fetch_counterfactual_backtest]
```

The **grounding contract** is enforced in two places. First, `ungrounded_claims` must be empty before the response is shown to the user — if the LLM admits it is speculating, the server blocks the response and the LLM retries with explicit instruction to fetch more data. Second, every `cited_signal_ids` entry is dereferenced on the server and the referenced content is rendered as an inline citation card in the chat UI. If an ID does not resolve, the response is blocked.

There is no `if "gold" in user_message` anywhere. There is no intent classifier, no dispatch table, no regex. The LLM reads the user message, picks the tools, explains the answer. That is the rule.

---

## 3. Backtest ↔ Production Parity

The canonical failure mode for quantitative products is "the backtest is written in Python-A and production runs Python-B". Midas cannot afford this (`02-strategy-methodology.md` §6; `01-competitive-landscape.md` §6.3: "backtest-to-live decay destroys credibility").

**Decision**: one Core SDK workflow, one set of custom nodes, two entry points.

### 3.1 The shared node graph

```
                                                                    
    TimeSourceNode    ──►  UniversePITNode  ──►  PriceHistoryNode    
    (historical|live)       (survivorship-free)   (adj+raw close)    
          │                                             │            
          ▼                                             ▼            
    FundamentalsPITNode ──► MomentumScoreNode ──► RegimeEnsembleNode 
                                                        │            
                                                        ▼            
                                 AdaptiveAllocatorNode (or HRP fallback)
                                                        │            
                                                        ▼            
                                           TransactionCostNode (§4)  
                                                        │            
                                                        ▼            
                                             ┌──────────┴───────────┐
                                             ▼                      ▼
                                   BacktestSinkNode           LiveSignalSinkNode
                                   (backtest_runs)            (signals, publish)
```

The entry parameters differ: the backtest entry passes `TimeSource(mode="historical", start=..., end=...)` and a walk-forward loop; the live entry passes `TimeSource(mode="live")` and runs once per rebalance. **Every node between `TimeSourceNode` and the sink is byte-identical** because they are the same Python classes imported from `src/midas/strategy/`. There is no second implementation.

### 3.2 Why this prevents drift structurally

DataFlow read nodes respect point-in-time as-of-date from the `TimeSource`, so a backtest from 2008 gets the 2008-published fundamentals, not today's restated values. The `AdaptiveAllocatorNode` has no concept of "live vs backtest" — it takes scores and returns weights. The `TransactionCostNode` (§4) is the same instance. The only thing that changes is the sink. If a developer modifies the allocator's momentum window in a session, both surfaces see the change simultaneously — which is *correct*, and the regression test suite (tier 2, real Postgres, per `rules/testing.md`) is the gate that catches unintended shifts.

---

## 4. TransactionCostNode — The Reusable Cost Primitive

The brief §7 demands realistic costs. `02-strategy-methodology.md` §5 specifies the cost function. `03-broker-and-regulatory.md` §2 verifies the fee schedule.

### 4.1 Interface contract

```python
class TransactionCostNode(BaseNode):
    """Compute total bps cost for a trade leg. Deterministic. No side effects."""

    # Inputs
    side: Literal["BUY", "SELL"]
    ticker: str
    notional_usd: float
    shares: int
    adv_usd: float               # 20-day average daily dollar volume
    spread_bps: float            # from EODHD L1 snapshot or calibrated table
    regime_vol_multiplier: float # 1.0 normal, 2.0 cautious, 3.0 turbulent
    commission_tier: Literal["fixed", "tiered"]

    # Outputs
    commission_bps: float        # IBKR Pro, min $1 floor, 1% cap
    reg_fees_bps: float          # SEC §31 + FINRA TAF on sells only
    half_spread_bps: float       # 0.5 * spread_bps * regime_vol_multiplier
    impact_bps: float            # max(0.5, 10 * sqrt(notional / adv_usd)) — Almgren-Chriss sqrt
    gap_risk_bps: float          # 95th-percentile overnight gap attributable
    total_bps: float             # sum of above
    components: dict             # itemised for audit + UI display
```

The node is used three times in the system: (a) inside the backtest to compute per-trade drag at the historical fill (next-day open), (b) inside the live scheduler to produce the cost estimate shown to the user at recommendation time, (c) inside the `L1 turnover penalty` calculation in the allocator so `lambda_turn` is calibrated in the same units. Same class. Same code path.

### 4.2 Calibration loop

A weekly background workflow (another Core SDK workflow, scheduled via Nexus) reads realised IBKR fills from the v2 live data, compares against the modelled cost, and writes a `cost_calibration` row per ticker per regime. If realised exceeds modelled by >2x for four weeks, the workflow raises an alert (audit + ops notification). The alert is *not* automatic recalibration — a human reviews before constants move, because the calibration constants affect published signals and would cause an unannounced strategy drift otherwise.

---

## 5. PACT Governance — The Server/Client Envelope Split

`03-broker-and-regulatory.md` §3.1 establishes the constraint: under *Lowe v. SEC*, the US v1 only survives as a "publisher" if the SERVER produces IMPERSONAL model portfolios. But the USER is allowed to have personal preferences — they just have to live on the CLIENT side (or in a clearly-separated server schema never joined to signals).

PACT envelopes model this split cleanly.

### 5.1 Two PACT envelopes

**Envelope A: `midas/publisher` (server-side, constrained).**
- **Operational**: may read `instruments`, `prices_eod`, `macro_series`, `news_items`, `corporate_actions`, `fundamentals_pit`. May write `signals`, `backtest_runs`, `audit_log`.
- **Data Access**: explicitly denied read access to `users`, `positions`, `orders`, `notification_prefs`, `subscriptions`. This is enforced at Postgres role level, not just in code.
- **Financial**: N/A (no money movement — Midas never holds funds, `03-broker-and-regulatory.md` §5.1).
- **Temporal**: may run only on market-close cadence (no intraday triggers in v1).
- **Communication**: publishes only via the `GET /v1/portfolios/{id}/signals/latest` channel. No `POST` to users. No per-user fan-out.

**Envelope B: `midas/client-personalization` (server-side, quarantined).**
- **Operational**: manages user account, subscription status, notification preferences, watchlist, approval history, *which* model portfolio(s) they subscribe to.
- **Data Access**: reads `users`, `subscriptions`, `notification_prefs`, `approval_log`. Reads `signals` ONLY via the same public API endpoint that any subscriber uses — not via direct DB join.
- **Communication**: sends push notifications, manages the approval UI.
- **What it cannot do**: modify signals, re-weight published portfolios, filter signals per-user, compute per-user suitability. If the code tries, PACT fail-closed blocks the action and the audit trail records the attempt.

### 5.2 What is a PACT concern vs not

PACT is the *envelope enforcer*. What PACT does handle: the role separation, the default-deny on cross-envelope reads, the fail-closed on violations, the audit. What PACT does not handle: the actual signal math (that is Core SDK), the storage (DataFlow), or the LLM reasoning (Kaizen with its own signature-level grounding contract). PACT sits between them as the grammar of allowed actions.

The `GovernanceContext(frozen=True)` pattern from `rules/pact-governance.md` is exactly the shape Midas wants: the `publisher` workflow receives its context, cannot self-modify, and if a developer writes code that tries to join `signals` to `users` at query time, the context denies the read and the workflow fails closed.

---

## 6. Impersonal-Publisher Architecture — The Hardest Constraint

This is the section that matters most. The legal argument in `03-broker-and-regulatory.md` §3.1 collapses if the server ever personalises. The architecture must make personalisation *structurally impossible on the server*, not merely *policy-forbidden*.

### 6.1 Schema-level enforcement

The `signals` table has the following columns and NO others relating to identity:

```
signals (
  model_portfolio_id   uuid       NOT NULL,
  rebalance_ts         timestamptz NOT NULL,
  target_weights       jsonb       NOT NULL,  -- {ticker: weight_pct}
  regime_label         text        NOT NULL,  -- Normal | Cautious | Turbulent
  cost_estimate_bps    jsonb       NOT NULL,  -- per-sleeve from TransactionCostNode
  backtest_run_id      uuid        NOT NULL,  -- link to the proving backtest
  published_at         timestamptz NOT NULL,
  content_hash         bytea       NOT NULL,  -- tamper evidence
  PRIMARY KEY (model_portfolio_id, rebalance_ts)
);
```

**There is no `user_id` column. There is no foreign key to `users`. There is no `account_balance`, no `risk_tolerance`, no `tax_situation`.** The Postgres role that owns the `publisher` envelope has `SELECT, INSERT` on `signals` and `NO SELECT` on the entire `users` schema. A developer cannot write "personalise this signal" because the SQL would fail with a permissions error at runtime. This is the structural enforcement PACT's data-access constraint layer maps onto.

### 6.2 Client-side personalisation is still allowed

What Alex cares about (notification cadence, which model portfolio they follow, whether they want to approve every trade or just material ones) lives in Envelope B. The client app calls two URLs:

1. `GET /v1/portfolios/{id}/signals/latest` — returns the **same bytes** to every subscriber of portfolio `id`. Cacheable at CDN.
2. `GET /v1/me/preferences` — returns the user's personal preferences from the quarantined schema.

The client (Next.js or React Native) composes them locally: "apply my preference filter to the signal I just fetched". The *delta* between the current model portfolio weights and the user's actual IBKR account balances is computed **client-side**, against balances fetched **directly from IBKR via OAuth** (`03-broker-and-regulatory.md` §1.5). Midas's server never sees the user's IBKR balances. That is the Lowe-compatible posture.

### 6.3 Why the CDN-ability is the legal tell

If the same HTTP response to `/signals/latest` can be cached on a public CDN and served to every subscriber, the publisher exemption is defensible. The moment a response varies by user identity, it is personalised advice. The architecture should therefore aim for `Cache-Control: public` on the signals endpoint. If that cache header ever has to be removed, the architecture has slipped out of Lowe and the legal posture needs re-review.

---

## 7. Failure Modes → Fail-Closed

Every external dependency fails at some point. The rule is always the same: **fail-closed to "no new recommendation", never fail-open to "trade anyway"** (`rules/pact-governance.md` MUST Rule 4). The client UI shows the last-published signal with a staleness badge; it does not fabricate a new one.

| Failure | Detection | Response |
|---|---|---|
| EODHD fetch returns 5xx or stale bar | `EODHDFetchNode` compares latest `ts` vs expected session close | Workflow aborts. Regime workflow records `status=unknown`. `LiveSignalSinkNode` does NOT publish. Previous signal stays latest; UI shows "data unavailable — no new recommendation" |
| Yahoo fallback also fails | Fallback node's own health check | Same fail-closed. We never publish a half-verified signal. |
| IBKR OAuth token expired or auth fails | Per-user, client-side during order placement | Client shows "reconnect IBKR" — but this does **not** affect the server's ability to publish. The publisher does not depend on IBKR auth. |
| Perplexity rate-limited | News workflow's own backoff + age check | News becomes stale. DebateAgent sees staleness in the tool response and surfaces it to the user via the grounding contract. Regime ensemble does not depend on news — it still runs. |
| Regime detector internal disagreement (signals contradict beyond threshold) | `WeightedEnsembleNode` computes a confidence score; if ensemble variance exceeds a threshold, regime = `uncertain` | Treat `uncertain` as Cautious (the conservative default), freeze automation, require user approval — matches the brief §2 posture. |
| Allocator covariance ill-conditioned | Condition-number check inside `AdaptiveAllocatorNode` | Deterministic fallback to HRP. This is the single place fallback is acceptable because it is a numerical fallback, not an error-hiding fallback. |
| DataFlow pool exhausted | Pool monitor (`rules/dataflow-pool.md`) | Back-pressure the ingestion workflows first; publisher workflow has priority because it is what the product sells. |
| Audit write fails | Sink node error | Workflow aborts *before* the signal is published. No unaudited signal ever goes out. This is a hard invariant. |

Each of these maps cleanly to a PACT `fail-closed` in the `publisher` envelope. The LLM debate surface fails closed too: if tools are unavailable, the DebateAgent's signature is instructed to say "I cannot answer without the underlying data — please retry later" rather than speculate.

---

## 8. Monorepo Layout

The repo already has `src/`, `tests/`, `deploy/`, `conftest.py`, `pyproject.toml`. Proposed layout under `/Users/takahidekawabe/Documents/GitHub/disease-risk-identifier/midas/`:

```
midas/
├── src/midas/
│   ├── data_fabric/          # EODHD/Yahoo/Perplexity/FRED/IBKR fetchers (Core SDK nodes)
│   │   ├── eodhd.py          # EODHDFetchNode
│   │   ├── yahoo.py          # YahooFallbackNode
│   │   ├── perplexity.py     # PerplexityNewsNode
│   │   ├── fred.py           # FREDMacroNode
│   │   └── ibkr_bars.py      # IBKRBarNode (v2 only)
│   ├── models/               # DataFlow @db.model definitions
│   │   ├── prices.py         # Instrument, PriceEOD, PriceIntraday, CorporateAction
│   │   ├── fundamentals.py   # FundamentalPIT
│   │   ├── macro.py          # MacroSeries
│   │   ├── news.py           # NewsItem with VECTOR(1536)
│   │   ├── signals.py        # Signal (NO user_id), BacktestRun, Recommendation
│   │   ├── users.py          # User, Subscription, NotificationPref (separate schema)
│   │   └── audit.py          # AuditLog (append-only hypertable)
│   ├── strategy/             # The shared engine — backtest AND live
│   │   ├── universe.py       # UniversePITNode
│   │   ├── features.py       # MomentumScoreNode, CovarianceNode
│   │   ├── regime/           # RegimeEnsembleNode + per-signal nodes
│   │   ├── allocator.py      # AdaptiveAllocatorNode, HRPAllocatorNode
│   │   ├── cost.py           # TransactionCostNode
│   │   └── workflow.py       # The single WorkflowBuilder graph
│   ├── backtest/             # TimeSource(historical), walk-forward driver, CPCV
│   ├── scheduler/            # Live TimeSource, Nexus cron registration, idempotency
│   ├── signals_api/          # Nexus API channel, GET /v1/portfolios/{id}/signals/*
│   ├── debate_agent/         # Kaizen DebateAgent + tool definitions
│   ├── governance/           # PACT envelopes (publisher, client-personalization)
│   ├── shared_types/         # Pydantic/dataclass types shared server↔client
│   └── __init__.py
├── apps/
│   ├── web/                  # Next.js — dashboard, approvals, debate chat, backtest explorer
│   └── mobile/               # React Native — push-first approval flow
├── tests/
│   ├── unit/                 # Tier 1: pure node tests
│   ├── integration/          # Tier 2: real Postgres + DataFlow
│   └── e2e/                  # Tier 3: full workflow replay against historical data
├── deploy/
├── docs/
│   └── 00-authority/         # canonical decisions
└── workspaces/
```

Python packaging: one package (`midas`) under `src/`, with submodules as above. This keeps the import graph flat and lets the strategy package be unit-tested without pulling in Nexus or Kaizen. The Next.js and React Native apps are separate workspaces under `apps/`, not Python packages.

---

## 9. Missing Kailash Capabilities

Being honest.

1. **Kaizen grounding-citation primitive.** The DebateAgent's `cited_signal_ids` + `ungrounded_claims` + server-side dereference is a pattern that would benefit from a first-class Kaizen primitive — something like `GroundedSignature` that automatically verifies every cited ID against a resolver before the response returns. Today this has to be hand-built around `BaseAgent.run()`. **Action**: file a feature request on `kailash-kaizen` after v1 proves the pattern works.

2. **PACT schema-grant synchronisation.** PACT envelopes today are Python-side. The architecture above relies on Postgres role grants matching the PACT data-access constraints *exactly*. There is no automated sync that translates a PACT `DataAccessConstraints` into the corresponding `GRANT`/`REVOKE` SQL. Today this is manual — a migration script maintained alongside the envelope definitions. **Action**: propose a PACT extension that generates the SQL from the envelope, reviewed by `pact-specialist`.

3. **Core SDK TimeSource node.** The backtest↔live parity pattern depends on a `TimeSourceNode` that the rest of the graph consumes for "what is the current as-of-date". This is a common pattern and Core SDK does not ship it as a first-class node — it would be a custom node in `src/midas/strategy/`. Not a blocker, but a candidate for upstream contribution.

4. **CPCV driver.** Combinatorial purged cross-validation (§6.3 of `02-strategy-methodology.md`) is quantitative-specific and not in kailash-ml today. It will be a Midas-local implementation calling the shared workflow repeatedly. Not upstreamable unless kailash-ml wants to own finance-specific CV.

5. **Nexus scheduled workflow with idempotency keys.** Nexus supports scheduled execution; confirm with `nexus-specialist` whether idempotency keys (so a retry of a Friday-close workflow cannot double-publish) are first-class or a Midas responsibility.

Everything else — DataFlow for storage, Core SDK for compute, Kaizen for the LLM surface, PACT for the envelope split — is in-scope for the frameworks as they exist.
