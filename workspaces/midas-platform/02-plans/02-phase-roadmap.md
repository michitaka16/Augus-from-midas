# Midas v1 — Phase Roadmap

Phases are autonomous execution sessions. Each phase gates on the previous. Effort is in autonomous sessions, not human-days (see `rules/autonomous-execution.md`).

## Phase 1 — Foundation (3–4 sessions)

**Goal**: Data flowing, backtest running, cost model validated.

| Deliverable | Sessions | Gate |
|---|---|---|
| D1. Data fabric: EODHD + FRED ingestion, Timescale schema, Redis cache, PIT universe | 1–2 | Data for all 8 sleeves from 2000-present loads clean |
| D3. Backtest engine: walk-forward + CPCV + Deflated Sharpe | 1 | Known benchmark (60/40) reproduces published returns ± 50bps |
| D2. Cost model node (TransactionCostNode) | 0.5 | Cost of a known historical rebalance matches IBKR statement ± 10% |
| D2. Regime detection ensemble | 0.5 | 2008, 2020, 2022 all correctly classified as turbulent within 5 trading days |

**Human gate**: Review backtest output for reasonableness. Does regime detection match your intuition?

## Phase 2 — Strategy (2–3 sessions)

**Goal**: AAA allocator producing signals that beat benchmarks in backtests net of costs.

| Deliverable | Sessions | Gate |
|---|---|---|
| D2. Adaptive Asset Allocation + HRP fallback | 1 | Walk-forward Sharpe > 0.5, PBO < 0.4 across all sub-horizons |
| D4. Signal publication pipeline (impersonal schema, 3 model portfolios) | 0.5 | `/signals/latest` returns valid JSON, no user_id anywhere in the stack |
| D2. Multi-horizon signal blending + turnover penalty | 0.5 | Turnover < 200%/year, max rebalance 1x/week |
| Backtest↔live parity regression tests | 0.5 | Nightly replay tolerance passes on 100 random dates |

**Human gate**: Review backtest results + PBO. Do the 3 model portfolios (Growth/Balanced/Conservative) make sense?

## Phase 3 — Broker + Auth (2 sessions)

**Goal**: User can link IBKR, see their positions, submit an order.

| Deliverable | Sessions | Gate |
|---|---|---|
| D5. IBKR Client Portal API connector (local Gateway for beta) | 1 | Paper account: read positions, preview order, submit order, confirm fill |
| D7/D8. Auth (email + MFA), account model, model portfolio subscription | 1 | New user signs up, picks a model portfolio, links IBKR paper account |
| D9. PACT envelope enforcement (publisher/subscriber separation) | 0.5 | Publisher Postgres role confirmed unable to SELECT from users.* |

**Human gate**: Walk through signup → IBKR link → paper trade flow end-to-end.

## Phase 4 — Web + Mobile UX (3–4 sessions)

**Goal**: All 7 web screens + mobile approval flow working.

| Deliverable | Sessions | Gate |
|---|---|---|
| D7. Dashboard, signal detail, pending approvals, backtest explorer, trade log, settings | 2 | All screens render with real data from Phase 1–3 |
| D8. Mobile: push → approval card → biometric → execute | 1 | iOS/Android: receive push, approve, order lands at IBKR paper |
| D7. Debate chat UI (frontend shell) | 0.5 | Chat renders, sends messages, shows response cards with citations |
| Responsive polish + dark mode | 0.5 | No layout breaks on mobile web or tablets |

**Human gate**: Use the product for a week in paper-trading mode. Does the UX match your expectation?

## Phase 5 — Debate Agent (2 sessions)

**Goal**: Conversational AI that defends its positions with data.

| Deliverable | Sessions | Gate |
|---|---|---|
| D6. Kaizen DebateAgent + grounding contract | 1 | 20-turn conversation about a regime flip: zero ungrounded claims |
| D6. Counter-scenario capability | 0.5 | "What if I skip this rebalance" produces a grounded cost/opportunity analysis |
| D6. Sycophancy resistance testing | 0.5 | Agent defends its position when challenged with bad arguments |

**Human gate**: Debate with the agent about a real regime event. Does it feel useful, not annoying?

## Phase 6 — Hardening + Launch Prep (2 sessions)

**Goal**: Production-ready, auditable, legally clean.

| Deliverable | Sessions | Gate |
|---|---|---|
| Security review (full stack) | 0.5 | Zero CRITICAL, zero HIGH findings |
| Legal copy review (no "your portfolio" language on server) | 0.5 | Marketing + in-app copy reviewed |
| IBKR OAuth production approval follow-up | — | External dependency (not session-bound) |
| Backtest regression suite in CI | 0.5 | All golden hashes match; PBO thresholds enforced |
| Monitoring + alerting (cost model drift, Perplexity spend, data gaps) | 0.5 | Dashboard shows all tripwires from risk register |
| Perplexity fallback (RSS + FinBERT) tested | — | Graceful degradation confirmed |

**Human gate**: Final sign-off for private beta launch.

## Total: ~14–17 autonomous sessions

At ~1 session/day, this is roughly 3–4 weeks of autonomous execution. The IBKR OAuth production approval is the calendar-bound critical path — everything else can run ahead of it using the local Gateway fallback.
