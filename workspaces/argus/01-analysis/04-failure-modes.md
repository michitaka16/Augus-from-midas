# Failure Mode Analysis: Midas to Argus Migration

## Executive Summary

Midas and Argus share the same IBKR integration, data ingestion pipeline, audit infrastructure, and user authentication system. These shared components can migrate as-is. The failure points occur at the **Midas-specific logic layers**: the OAuth scopes are wrong for monitoring-only access, the data models encode trading concepts incompatible with guideline monitoring, the approval workflow uses the wrong state machine, the backtest engine is tightly coupled to the signal-generation pipeline, and the position model lacks the fields needed for guideline evaluation.

---

## 1. IBKR OAuth Scopes

**Severity: HIGH**

### What Midas Has

`midas-broker/ibkr/oauth.py` requests OAuth scopes: `read_positions preview_order place_order`

The `IBKROAuth` class stores encrypted tokens for these three scopes and exposes `get_access_token()` for any downstream IBKR call.

### What Breaks in Argus

IBKR OAuth is an all-or-nothing authorization. When a user connects their IBKR account through Midas, they are granting the application permission to:
- Read positions (needed for both Midas and Argus)
- Preview orders (needed for Midas trade preview)
- **Place orders (trading — not needed for Argus monitoring)**

The `place_order` scope is a legal and operational liability for Argus. The application is authorized to trade on the user's behalf even though Argus never executes trades. If the OAuth token is ever exfiltrated or the Argus broker package is repurposed, the token grants trading access it does not need.

Additionally, the IBKR OAuth flow stores tokens in `tokens.user_tokens` with these specific scopes. If the `midas_broker` role in `envelopes/__init__.py` is reused for Argus, it carries the same scope grant that enables trading.

### Migration Risk

**HIGH** — The OAuth flow itself works, but the scope is wrong from day one. This is not a code bug; it is a design gap.

### Recommended Mitigation

Before any OAuth exchange for Argus users, replace the scope string:

```python
# In the Argus broker package — use monitoring-only scopes
_OAUTH_SCOPES_MONITOR = "read_positions"
# NOT the Midas-wide _OAUTH_SCOPES = "read_positions preview_order place_order"
```

This requires:
1. Creating a new `ArgusBroker` class or constructor parameter for `scope_override`
2. Not inheriting from `IBKROAuth` directly — composing it or wrapping the token-fetch logic
3. Ensuring the IBKR developer portal application is configured with separate OAuth credentials for Argus if IBKR supports per-application scopes, or documenting that Argus users grant broader access than the application uses

The existing `TokenEncryption` (AES-256-GCM) and token storage (`tokens.user_tokens` table) are reusable. The scope string is the only change needed at the OAuth layer.

---

## 2. Data Model Mismatch

**Severity: HIGH**

### What Midas Has

The `signals` table (schema in `models/signals.py`) is structured around regime-aware allocation signals:

```
signals(id, model_portfolio_id, timestamp, regime, allocations_json, reasoning_json,
        cost_estimate_json, ensemble_score, published, published_at)
```

The primary key is `(model_portfolio_id, timestamp)`. There is **NO user_id column** — this is the structural enforcement of the publisher exemption (ADR-001). Signals are impersonal, identical for all subscribers.

### What Argus Needs

Argus needs:
- Per-user **guideline definitions** with rule types, thresholds, and parameters
- Per-user **violation records** linking a guideline, a position snapshot, and a timestamp
- Per-user **acknowledgment records** (the equivalent of Midas's approval workflow)
- A **positions** table that stores the IBKR position snapshot at evaluation time (so violations can be evaluated against the exact positions that triggered them)

### Schema Migration Path

This is the most complex failure point because the Midas schema contains Midas-specific tables that have no Argus equivalent:

| Midas table | Argus equivalent | Migration action |
|---|---|---|
| `signals` | None | DELETE — signals are trading outputs |
| `signal_inputs` | None | DELETE — snapshot of signal inputs (regime computation) |
| `approvals` | `violation_acknowledgments` | ADAPT — approval status machine maps to acknowledgment status machine |
| `model_portfolios` | `portfolio_profiles` | ADAPT — model portfolios are impersonal; Argus profiles are user-specific |
| `accounts` | `accounts` (keep) | REUSE — IBKR account linking is identical |
| `audit_trail` | `audit_trail` (keep) | REUSE — immutable chain hash audit works for any platform |
| `regime_signals` | Guideline input | ADAPT — regime signals become one input TYPE for guideline evaluation |

### Key Incompatibilities

**1. `signals` table has no user_id.** The publisher exemption means signals are purely impersonal. Argus violations are **user-specific** — user A's guideline violations are not user B's. The entire user-scoped query pattern (`WHERE user_id = $1`) must be introduced in Argus-specific tables, which is a new pattern not used by Midas.

**2. `approvals` vs `violation_acknowledgments`.** The Midas `approvals` table has a rigid status machine: `pending → approved | rejected | held`. The join to `signals` is hardcoded:

```sql
JOIN signals s ON s.id = a.signal_id
```

For Argus, the acknowledgment workflow needs different statuses: `pending → acknowledged | escalated | dismissed`. The JOIN target changes from `signal_id` to `violation_id`. This is an ADAPT, not a REUSE.

**3. No guideline definition table exists.** This is the most significant gap. All of the following must be built new:

- `guidelines` — user_id, name, rule_type, parameters_json, enabled, created_at
- `guideline_violations` — guideline_id, position_snapshot_json, evaluated_at, severity, triggered_value, threshold_value
- `violation_acknowledgments` — violation_id, user_id, status, acknowledged_at, method

### Recommended Mitigation

1. **Do not reuse the Midas migrations directly.** The migration runner in `midas-governance/migrations/__init__.py` is generic and works for Argus, but the migration SQL files must be rewritten.
2. Create new numbered migrations for Argus schema (`argus_v001_add_guidelines.sql`, etc.) in the Argus package, not in `midas-governance/migrations/`.
3. Before writing any migration, define the `Guideline` and `GuidelineViolation` dataclass models in `argus-shared`, then generate migrations from those models.
4. Seed data changes: replace `DEFAULT_PORTFOLIOS` seed with guideline template seeds (e.g., common rules like "max 30% single sector" as starting templates).

---

## 3. Approval Flow vs Violation Acknowledgment Workflow

**Severity: HIGH**

### What Midas Has

`handlers/approvals.py` exposes a workflow where:

1. User has **pending approvals** — unapproved trade signals from the publisher
2. User can **approve** (trades execute), **reject** (trades discarded), or **hold** (acknowledged but not executing)
3. The `approval_id` is the handle for all subsequent operations
4. The escalation scheduler (`scheduler/escalation.py`) escalates approvals older than N hours

### What Argus Needs

The workflow is inverted in concept:

1. Argus **detects a violation** — a guideline rule is breached by the current positions
2. User must **acknowledge** the violation — they are aware of it
3. User can **escalate** (request discussion with advisor), **dismiss** (acknowledge and close), or the system auto-escalates if unacknowledged for N days

### What Can Be Reused

- The **audit trail** integration (`await self._audit.append(...)`) patterns in every approval handler are directly reusable for violation acknowledgments
- The **escalation scheduler** (`scheduler/escalation.py`) has a generic time-based escalation mechanism that only needs new condition logic
- The **notification system** (`handlers/notifications.py`) can notify on violations instead of pending approvals

### What Must Be Rebuilt

- The `ApprovalHandlers` class is **not reusable**. Its methods are tightly coupled to `signals` table joins:
  ```python
  "FROM users.approvals a JOIN signals s ON s.id = a.signal_id"
  ```
  Replacing this with `JOIN violations v ON v.id = a.violation_id` is a full rewrite.
- The status machine is subtly different. Midas approval has three non-terminal states (pending, held) and two terminal states (approved, rejected). Argus acknowledgment has pending and two terminal states (acknowledged, escalated). The state transition logic is similar enough to copy the pattern but different enough that sharing the class would be misleading.
- The `escalation.py` scheduler currently fires on `approvals WHERE status = 'pending' AND created_at < NOW() - INTERVAL 'N hours'`. For Argus, it should fire on `violations WHERE acknowledged_at IS NULL AND created_at < NOW() - INTERVAL 'N days'`. The scheduler framework is reusable; the query and interval are not.

### Recommended Mitigation

1. Keep the **escalation scheduler framework** (`scheduler/escalation.py`) as a reusable component — it polls on a configurable condition. Pass the condition as a SQL predicate parameter.
2. Keep the **audit append pattern** — the same `audit.append(event_type="violation_acknowledged", ...)` call works.
3. Write a new `ViolationHandlers` class in the Argus broker package that mirrors the structure of `ApprovalHandlers` but targets violation tables.
4. Do not attempt to unify the two handler classes into one. The semantic domains are different enough that a unified class would require conditional branches that defeat the purpose.

---

## 4. Backtest Engine Reuse for Guideline Rule Backtesting

**Severity: MEDIUM**

### What Midas Has

`midas-backtest/engine/walkforward.py` runs walk-forward analysis. The `WalkForwardEngine` class:

1. Takes a `data_fabric` (market data) and a `model_portfolio_id`
2. Generates signals for each test period via `generate_signals(time_source, data_fabric, ...)`
3. Collects returns on the test period and computes Sharpe, drawdown, turnover, cost drag

The engine is tightly coupled to `midas_strategy.signals.workflow` via this import:
```python
from midas_strategy.signals.workflow import generate_signals
```

The entire signal-generation pipeline (TimeSource → regime detection → AAA allocator → cost model → signal) runs for each period.

### What Argus Needs

"Backtest this guideline rule" means: given a guideline definition (e.g., "max 30% in any single sector"), did historical positions violate it? This is not a signal-generation task. It is a **position-evaluation task**.

The inputs are:
- Historical position snapshots (not available in Midas — positions are read from IBKR in real time only)
- A guideline rule definition
- A time range

The output is a list of violation events with timestamps.

### Why This Is a Medium Risk

The walk-forward engine's **infrastructure** (period generation, date arithmetic, performance metric computation) is reusable. The **signal generation pipeline** is not applicable to Argus.

The `WalkForwardEngine` class does the following:
- `generate_periods()` — purely date-based, fully reusable
- `_collect_period_returns()` — uses `data_fabric.get_bars()` for price data, fully reusable
- `run()` — calls `generate_signals()` from `midas_strategy`, not reusable

Additionally, Midas has **no historical position storage**. Positions are fetched from IBKR live. There is no `positions_history` table. For Argus to backtest guideline rules, historical positions must be stored — either by a scheduled snapshot job or by replaying trades from IBKR's transaction history.

### Recommended Mitigation

1. **Extract the period-generation infrastructure** into a reusable `PeriodGenerator` class that takes `(initial_train_years, test_step_years, start, end)` and emits `(train_start, train_end, test_start, test_end)` tuples. Move to `argus-shared/`.
2. **Do not reuse the walk-forward `run()` method.** Replace it with a new `GuidelineBacktestEngine.run()` that, for each test period:
   - Loads position snapshot at `test_start`
   - Evaluates each active guideline against that snapshot
   - Records violations
3. **Build historical position storage first.** This is a prerequisite for backtesting. Options:
   - Scheduled job: snapshot IBKR positions once per trading day, store in `position_snapshots(account_id, date, positions_json)`
   - IBKR transaction replay: replay executed trades from IBKR API to reconstruct historical positions
4. The C-PCV engine (`engine/cpcv.py`) and degraded performance analysis (`engine/degraded.py`) are reusable for "was this guideline robust across market conditions?" but only after historical position storage is in place.

---

## 5. IBKR Position Fetching Compatibility

**Severity: MEDIUM**

### What Midas Has

`midas-broker/orders/positions.py` fetches positions via `ibkr_client.get_positions(account_id)` and normalizes to a `Position` dataclass:

```python
@dataclass
class Position:
    ticker: str
    quantity: float
    market_value: float
    avg_cost: float
    unrealized_pnl: float
    currency: str
```

Comment in the file: "This data NEVER leaves the client in v1 (publisher exemption)."

### What Argus Needs

The `Position` dataclass fields are **sufficient for basic compliance monitoring** (checking allocation percentages, sector concentration, single-position limits). However, several guideline evaluation needs are **not met**:

| Guideline need | Required field | Status in Midas Position |
|---|---|---|
| Sector classification | ETF sector (GICS) | **MISSING** — needed for "max 30% single sector" |
| Asset class | equity/bond/commodity/REIT | **MISSING** — needed for "min 20% bonds" |
| Issuer / fund name | Full fund name | **MISSING** — needed for "no leveraged ETFs" |
| Geographic exposure | country/region | **MISSING** — needed for "max 10% emerging markets" |
| Cost basis tracking | avg_cost vs current price | PRESENT — useful for tax-aware guidelines |
| Derivative exposure | delta/gamma for options | **MISSING** — relevant if user holds options |

The `fetch_positions()` function normalizes from IBKR's raw position fields (`contractDesc`, `position`, `mktValue`, `avgCost`, `unrealizedPnl`, `currency`). These IBKR fields include the data, but `fetch_positions()` discards most of it during normalization.

### Recommended Mitigation

1. **Extend the `Position` dataclass** with additional fields sourced from IBKR:
   ```python
   @dataclass
   class Position:
       ticker: str
       quantity: float
       market_value: float
       avg_cost: float
       unrealized_pnl: float
       currency: str
       asset_class: str = "equity"  # NEW: equity/bond/commodity/REIT/cash
       sector: str = ""             # NEW: GICS sector name
       region: str = ""             # NEW: geographic region
       is_leveraged: bool = False  # NEW: for "no leveraged ETFs" rule
       fund_name: str = ""          # NEW: full fund name for display
   ```
2. Update `fetch_positions()` to map IBKR's `contractDesc` and available metadata fields to these new columns.
3. For sector classification, leverage the existing `midas_strategy/sleeves/__init__.py` ETF definitions — they already classify the 10 sleeves by asset class and sector. This is a direct reuse opportunity. The sleeve definitions map ticker → (asset_class, sector, region, leveraged_flag).
4. If IBKR provides sector/asset-class metadata directly in position data, use it. If not, look up from the sleeve definitions or from a static ETF metadata table.

---

## Cross-Cutting Failure Points

### A. Governance Envelopes

`midas-governance/envelopes/__init__.py` defines four roles: `PUBLISHER` (no user access), `SUBSCRIBER` (user-scoped), `BROKER` (IBKR tokens only), `AUDIT` (audit trail only).

The `PUBLISHER` envelope is irrelevant for Argus (signals are gone). The `SUBSCRIBER` envelope needs extending: add grants for `guidelines`, `guideline_violations`, and `violation_acknowledgments` tables. The `BROKER` envelope is reusable as-is (IBKR tokens are the same).

The boot-time assertions (`assertions.py`) are also reusable — `assert_publisher_isolation` becomes `assert_argus_isolation` (checking that the Argus process has no grants on the old Midas tables).

### B. Audit Trail

The `AuditTrail` class in `midas-governance/audit/__init__.py` is fully reusable. It appends records to `audit_trail` with chain hashing. The event type field (`approval_decided`, `signal_published`) is arbitrary — `violation_detected`, `violation_acknowledged` are valid new event types.

### C. Data Fabric

The entire `midas-data/fabric/` layer (cache, ingest, pit_universe) and all source clients (EODHD, Yahoo, FRED, Perplexity) are reusable for Argus. Argus needs the same price/OHLCV data for historical position reconstruction and the same economic data for regime-aware guidelines ("alert when VIX > 30").

### D. The Debate Agent Pattern

`midas-debate/agent/debate.py` implements LLM-first architecture correctly — no deterministic routing, grounding verification, provider chain fallback. This pattern is **fully reusable** for Argus's violation discussion workflow.

The rewrite scope is:
- New `DebateInput`/`DebateOutput` signatures for guideline context instead of signal context
- New data tools: `get_positions`, `check_guideline`, `get_violation_history` instead of `get_signal`, `get_regime`
- New prompt (Argus-specific system prompt for discussing investment guideline violations)
- `grounding/verify.py` citation types change from `signal_*`, `backtest_*` to `violation_*`, `guideline_*`

---

## Summary Risk Register

| Failure Point | Severity | Migration Risk | Mitigation Effort |
|---|---|---|---|
| IBKR OAuth scopes (place_order scope present) | HIGH | OAuth tokens grant trading access Argus does not need | Low — scope string change + new constructor parameter |
| Data model mismatch (no user_id, no guidelines table) | HIGH | Schema migration is complex; signals table has no Argus equivalent | Medium — write new migrations, define models first |
| Approval workflow vs violation acknowledgment | HIGH | Status machine, JOIN targets, and escalation logic all differ | Medium — mirror pattern, new handler class |
| Backtest engine coupled to signal pipeline | MEDIUM | Period generation reusable; signal pipeline not applicable | Medium — extract period generator, build new backtest engine, requires historical position storage first |
| Position model lacks sector/asset-class fields | MEDIUM | Sufficient for basic allocation checks; insufficient for sector/asset rules | Low — extend dataclass + integrate sleeve definitions |
| Governance envelopes (PUBLISHER irrelevant) | LOW | SUBSCRIBER needs new table grants; assertions need updating | Low — add grants, rename assertion |
| Audit trail | LOW | Fully reusable | None — reuse as-is |
| Data fabric / sources | LOW | Fully reusable | None — reuse as-is |
| Debate agent architecture | LOW | Pattern is reusable; signatures and tools need rewriting | Medium — new signatures + prompt + tools |

---

## Recommended Priority Order

1. **Extend `Position` dataclass** (EASIEST — immediate gain, no dependencies)
2. **Create `IBKROAuth` scope override for Argus** (EASIEST — isolated change)
3. **Define `Guideline` and `GuidelineViolation` dataclass models** (FOUNDATIONAL — unblocks migrations)
4. **Write Argus migrations** (depends on step 3)
5. **Build `ViolationHandlers`** (depends on step 4)
6. **Build historical position storage** (depends on steps 1 and 4; unblocks backtesting)
7. **Build `GuidelineBacktestEngine`** (depends on step 6)
8. **Extend governance envelopes** (depends on step 4)
9. **Adapt debate agent** (parallel to step 5)
10. **Adapt escalation scheduler** (depends on step 5)
