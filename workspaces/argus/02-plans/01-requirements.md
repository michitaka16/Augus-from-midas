# Argus Requirements Plan — Week 9 MVP

## Source: Consolidated from 01-analysis/ (codebase audit, ML challenges, PMF, failure modes, ML specialist review)

---

## 1. Week 9 MVP Feature Breakdown

### Must Have (MVP)

#### 1.1 IBKR OAuth — Monitoring-Only Scopes
- **Scope string change**: `read_positions` only (Midas uses `read_positions preview_order place_order`)
- New `ArgusBroker` class or `scope_override` parameter — do not reuse Midas-wide scope constant
- Token encryption and storage (`tokens.user_tokens` table) — reusable as-is
- **Status**: Isolated change, no dependencies

#### 1.2 Position Fetching with Extended Position Model
Extend `Position` dataclass with fields needed for guideline evaluation:

```python
@dataclass
class Position:
    ticker: str
    quantity: float
    market_value: float
    avg_cost: float
    unrealized_pnl: float
    currency: str
    # NEW FIELDS:
    asset_class: str = "equity"   # equity/bond/commodity/REIT/cash
    sector: str = ""              # GICS sector name
    region: str = ""              # geographic region
    is_leveraged: bool = False    # for "no leveraged ETFs" rule
    fund_name: str = ""           # full fund name for display
```

- Source sector/asset-class from existing `midas_strategy/sleeves/__init__.py` ETF definitions (direct reuse)
- Update `fetch_positions()` to map IBKR fields to new columns
- **Status**: Low effort, no dependencies

#### 1.3 Guideline Definition Data Model
Define `Guideline` and `GuidelineViolation` dataclasses BEFORE writing migrations:

```python
@dataclass
class GuidelineType(Enum):
    SECTOR_MAX          # "max 30% in any single sector"
    ASSET_CLASS_RANGE  # "5-15% precious metals"
    BETA_RANGE          # "portfolio beta to SPY must stay below 1.2"
    DRAWDOWN_MAX        # "drawdown cannot exceed 15%"
    LEVERAGED_FORBIDDEN # "no leveraged ETFs"
    EMERGING_MARKETS_MAX # "max 10% emerging markets"
    # ... extensible

@dataclass
class Guideline:
    id: int
    user_id: int
    name: str
    guideline_type: GuidelineType
    parameters: dict[str, float]  # e.g. {"threshold": 0.30, "sector": "tech"}
    enabled: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class GuidelineViolation:
    id: int
    guideline_id: int
    evaluated_at: datetime
    severity: str  # "warning" | "critical"
    triggered_value: float  # what was actually measured
    threshold_value: float   # what the threshold was
    position_snapshot_json: str  # positions at time of violation
    acknowledged: bool
    acknowledged_at: datetime | None
    acknowledgment_method: str | None  # "user_acknowledge" | "escalate" | "dismiss"
```

**Status**: FOUNDATIONAL — unblocks all migrations and handlers

#### 1.4 Database Migrations
New Argus-specific migrations (NOT reusing Midas migrations directly):

```
argus_v001_add_guidelines.sql       — guidelines table, violation_acknowledgments table
argus_v002_add_portfolio_snapshots.sql — position_snapshots for historical storage
argus_v003_add_audit_events.sql     — argus-specific audit event types
```

Key design decisions:
- `guidelines` table: `user_id` is NOT NULL (violations are user-specific — unlike Midas signals)
- `guideline_violations` table: stores position snapshot JSON at evaluation time
- **No `signals` table** — signals are trading outputs, irrelevant for monitoring
- **No `approvals` table reuse** — rewrite as `violation_acknowledgments`

#### 1.5 Guideline Rule Engine
Simple threshold-based rule evaluator (NOT AI):

```
For each enabled guideline:
    Fetch current positions from IBKR
    Compute portfolio metrics (allocation %, beta, drawdown)
    Compare against guideline threshold
    If violated → create GuidelineViolation record
    If resolved (was violated, now compliant) → create resolution event
```

Rules to implement for Week 9:
1. `SECTOR_MAX` — compute % in each GICS sector, flag if any exceeds threshold
2. `ASSET_CLASS_RANGE` — compute % in each asset class, flag if outside range
3. `LEVERAGED_FORBIDDEN` — flag any position where `is_leveraged == True`
4. `DRAWDOWN_MAX` — compute 252-day drawdown from peak, flag if exceeded

**Status**: Core MVP engine — straightforward threshold logic, no ML

#### 1.6 Violation Alerting
- Email/push notification when a new `GuidelineViolation` is created
- Notification content: "ALERT: Your portfolio now has 34% in tech. Guideline '{name}' specifies maximum {threshold}."
- Reuse existing `NotificationService` pattern — just new notification type (`violation_detected`)
- Notification preferences: user can set `email` / `push` / `none` per guideline
- **Status**: Reuses existing notification infrastructure

#### 1.7 Violation Acknowledgment Workflow
New `ViolationHandlers` class (NOT reusing `ApprovalHandlers`):

```python
class ViolationHandlers:
    async def list_violations(self, user_id: int, status: str | None) -> list[GuidelineViolation]
    async def acknowledge_violation(self, user_id: int, violation_id: int, method: str) -> dict
    async def get_violation_history(self, user_id: int, guideline_id: int) -> list[GuidelineViolation]
```

Status machine: `pending → acknowledged | escalated | dismissed`
- `acknowledged`: user saw it and dismissed
- `escalated`: user requested advisor discussion
- `dismissed`: system auto-dismissed after N days with no action

#### 1.8 Audit Trail Integration
- `audit_trail` table reusable as-is
- New event types: `violation_detected`, `violation_acknowledged`, `violation_escalated`, `guideline_created`, `guideline_updated`
- Reuse existing `AuditTrail` append pattern

#### 1.9 Portfolio Monitor UI (Web)
- Portfolio overview: current positions with allocation %, sector breakdown
- Active guidelines list with enable/disable toggle
- Violation alert panel: list of active violations with severity
- Violation detail: what triggered it, triggered value vs threshold, when it started
- Acknowledge/dismiss/escalate actions

---

### Week 9 Should NOT Include

| Feature | Why Deferred |
|---------|-------------|
| Natural language guideline parsing | Hard NLP problem — defer to Week 10+ |
| ETF similarity/clustering | Feature store doesn't exist yet; ship Precision@3 diagnostic instead |
| Historical position storage + backtesting | Requires building position snapshot infrastructure first |
| Advisor multi-portfolio view | Week 12 scope |
| Regime-conditional clustering | Achievable but requires feature store (see ML review) |
| "Find similar ETFs" consumer feature | Week 10-11 after feature store exists |

---

## 2. API Endpoint Design

### Argus API Routes (New)

```
# Portfolio
GET  /argus/positions          — Current positions (from IBKR, extended Position model)
GET  /argus/portfolio/summary — Allocation %, sector breakdown, key metrics

# Guidelines
GET  /argus/guidelines           — List user's guidelines
POST /argus/guidelines            — Create guideline
GET  /argus/guidelines/:id        — Get guideline detail
PUT  /argus/guidelines/:id        — Update guideline
DELETE /argus/guidelines/:id       — Delete guideline
POST /argus/guidelines/:id/enable  — Enable guideline
POST /argus/guidelines/:id/disable — Disable guideline

# Violations
GET  /argus/violations             — List violations (filter: status, severity, guideline_id)
GET  /argus/violations/:id         — Violation detail with position snapshot
POST /argus/violations/:id/acknowledge — Acknowledge (method: acknowledge | escalate | dismiss)
GET  /argus/violations/history/:guideline_id — Historical violations for a guideline

# Pre-trade check
POST /argus/check-trade            — "Would this trade comply with my guidelines?"

# Account
GET  /argus/account/profile        — User profile + IBKR link status
POST /argus/account/ibkr/link      — Initiate IBKR OAuth (monitoring-only scopes)
GET  /argus/account/ibkr/callback  — OAuth callback
DELETE /argus/account/ibkr/unlink  — Revoke IBKR tokens

# Audit
GET  /argus/audit                  — Paginated audit trail (event_type filter)
```

### Authentication
- Reuse existing JWT Bearer authentication from Midas
- `_extract_user(request)` pattern reusable as-is
- New `argus_subscriber` Postgres role (extends Midas subscriber pattern)

---

## 3. Data Model Additions

### New Tables

```sql
-- guidelines
CREATE TABLE users.guidelines (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users.accounts(id),
    name VARCHAR(200) NOT NULL,
    guideline_type VARCHAR(50) NOT NULL,  -- SECTOR_MAX, BETA_RANGE, etc.
    parameters_json TEXT NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_guidelines_user ON users.guidelines (user_id);

-- guideline_violations
CREATE TABLE users.guideline_violations (
    id BIGSERIAL PRIMARY KEY,
    guideline_id BIGINT NOT NULL REFERENCES users.guidelines(id),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    severity VARCHAR(20) NOT NULL,  -- warning, critical
    triggered_value DOUBLE PRECISION NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    position_snapshot_json TEXT NOT NULL DEFAULT '{}',
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledgment_method VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_violations_guideline ON users.guideline_violations (guideline_id);
CREATE INDEX idx_violations_evaluated ON users.guideline_violations (evaluated_at);

-- violation_acknowledgments (explicit — mirrors approvals but for violations)
CREATE TABLE users.violation_acknowledgments (
    id BIGSERIAL PRIMARY KEY,
    violation_id BIGINT NOT NULL REFERENCES users.guideline_violations(id),
    user_id BIGINT NOT NULL REFERENCES users.accounts(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | acknowledged | escalated | dismissed
    acknowledged_at TIMESTAMPTZ,
    method VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ack_violation ON users.violation_acknowledgments (violation_id);
CREATE INDEX idx_ack_user ON users.violation_acknowledgments (user_id);
```

### Tables to NOT Reuse from Midas

| Midas Table | Argus Action |
|---|---|
| `signals` | DELETE — trading signals irrelevant |
| `signal_inputs` | DELETE — regime computation snapshots not needed |
| `approvals` | DO NOT REUSE — rewrite as `violation_acknowledgments` |
| `model_portfolios` | DO NOT REUSE — replace with user-specific `guidelines` |

### Extended Existing Tables

```sql
-- tokens.user_tokens: add argus-specific scope indicator (optional column)
ALTER TABLE tokens.user_tokens ADD COLUMN scopes VARCHAR(255) NOT NULL DEFAULT 'read_positions';

-- users.accounts: already has everything needed, no changes
-- audit_trail: already has event_type field, no changes
```

---

## 4. Migration Sequence

### Phase 1: Foundation (Day 1-2)
1. Create `packages/argus-shared/` — move reusable Midas components
2. Extend `Position` dataclass with sector/asset_class fields
3. Define `Guideline` and `GuidelineViolation` dataclasses
4. Write `argus_v001` migration

### Phase 2: Core Engine (Day 2-4)
5. Build guideline rule engine (threshold evaluator)
6. Create `ViolationHandlers` class
7. Wire up IBKR OAuth with monitoring-only scopes
8. Build violation alerting (reuse notification infrastructure)

### Phase 3: API + UI (Day 4-6)
9. Implement Argus API routes
10. Build portfolio monitor web UI
11. Write escalation scheduler condition for violations

### Phase 4: Stabilization (Day 7)
12. End-to-end test: IBKR OAuth → positions → guideline check → violation → alert → acknowledge
13. Seed data: guideline templates (common rules as starting points)

---

## 5. Key Architectural Decisions

### ADR-1: Rule Engine Is Threshold-Based, Not AI
The Week 9 rule engine evaluates simple threshold conditions (sector %, beta, drawdown). No ML, no LLM. This is achievable in 1 week and provides genuine value.

NLP parsing ("define guidelines in plain English") is deferred. When added, it will generate structured `Guideline` records — the same rule engine evaluates them.

### ADR-2: Position Snapshots Stored at Evaluation Time
When a violation is detected, the current positions are snapshotted as JSON and stored with the violation record. This enables:
- Accurate historical record of what triggered the violation
- Backtesting later (when snapshot infrastructure is built)
- User can see exactly what positions looked like when violated

### ADR-3: ETF Similarity Is a Diagnostic, Not a Consumer Feature
Week 9: Compute Precision@3 against sleeve prior as a validation diagnostic. Display internally ("this ETF's behavior is anomalous relative to its sleeve classification").

Week 10-11: Ship consumer-facing similar ETF discovery only after feature store exists and UX can explain regime-conditional behavior.

### ADR-4: OAuth Scopes Are Set at Authorization Time
The scope string (`read_positions`) is set when the user first authorizes Argus. The scope cannot be changed retroactively on existing tokens. New users get monitoring-only scopes; existing Midas users who migrate will re-authorize with new scopes.

### ADR-5: No Shared Handler Classes Between Midas and Argus
`ApprovalHandlers` is NOT extended for violations. A new `ViolationHandlers` class is written from scratch. The semantic domains are different enough that sharing the class would require conditional branches that undermine the architecture.

---

## 6. Dependencies Summary

```
EXTEND Position dataclass (1.2)
         ↓
Define Guideline/Violation models (1.3)
         ↓
Write migrations (1.4)          ← can be parallelized after models defined
         ↓
Build rule engine (1.5)        ← depends on models
         ↓
ViolationHandlers (1.7)         ← depends on migrations
         ↓
Alerting (1.6)                 ← depends on violations being storable
         ↓
API routes + UI (1.9, Section 2) ← depends on everything above
```

**Critical path**: Models → Migrations → Rule Engine → Handlers → API/UI

IBKR OAuth scope change (1.1) is isolated and can run in parallel with everything else.
