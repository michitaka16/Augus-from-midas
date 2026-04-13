# M04 — Signal Publication

Dependency: M02 (strategy workflow produces signals), M00 (schema)
Deliverable: D4
Package: `apps/api` (scheduler + handlers)

## Todos

### M04-01: Build signal scheduler
`apps/api/src/midas_api/scheduler/signal_cron.py`
- Weekly cron: trigger signal generation post-Friday-close (configurable, default Sunday 7 PM ET)
- Idempotency: check if signal for (model_portfolio_id, week) already exists before generating
- Calls the strategy workflow (M02-08) for all 5 model portfolios
- On success: write to `signals` + `signal_inputs` tables
- On failure: do NOT publish partial signals; alert ops; retry once

### M04-02: Build signal broadcast handler
`apps/api/src/midas_api/handlers/signals.py`
- `GET /signals/latest` — returns the most recent signal for each model portfolio
- `GET /signals/{model_portfolio_id}/latest` — single portfolio
- `GET /signals/{model_portfolio_id}/history` — paginated history
- CDN-cacheable: set `Cache-Control: public, max-age=3600` (signals are impersonal, same for everyone)
- NO user_id in request or response. NO authentication required for signal reads (impersonal publisher model)

### M04-03: Wire signal broadcast to Nexus
- Register signal handlers as Nexus API channel
- Verify CDN-cacheability (no `Set-Cookie`, no `Vary: Authorization` on signal endpoints)
- Verify the `/signals/latest` endpoint is CDN-able (this is the legal tell — per 06-framework-architecture.md)

### M04-04: Build data refresh scheduler
`apps/api/src/midas_api/scheduler/data_cron.py`
- Daily: EODHD EOD bars after market close, FRED macro signals
- On-demand (screen-active): bars since last fetch, throttled to max 1 req/10s per user
- Weekly: EODHD fundamentals + corporate actions
- Perplexity: on material price moves (>2% daily) or user opens debate chat

### M04-05a: Build turbulent escalation state machine
Split from M04-05 — pure logic:
- State machine: NOTIFIED → REMINDED → AUTO_DEFENSIVE | USER_DECIDED
- Timer logic: T+0h, T+12h, T+24h (configurable)
- Decision rules: user approved → execute user choice; user held → reset timer; timeout → defensive
- No external dependencies — pure state transitions

### M04-05b: Wire escalation to notifications + audit + approvals
Split from M04-05 — integration:
- Connect state machine to push notification service (M07-08)
- Write each escalation step to audit trail via midas-governance
- Write approval records to `approvals` table
- Connect timeout auto-defensive to signal workflow (generate defensive signal)

### M04-08: Wire signal publication to audit trail
- On every signal publication (M04-01): INSERT into `audit_trail` with event_type=`signal_published`
- Payload: signal_id, model_portfolio_id, regime, all input signal values
- Uses `midas_audit` Postgres role (INSERT only)
- This closes the D4 audit trail deliverable

### M04-06: Test — signal publication Tier 1
- Scheduler idempotency (double-run doesn't duplicate)
- Escalation timer logic (T+0, T+12, T+24 transitions)
- Signal endpoint response shape (no user_id)

### M04-07: Test — signal publication Tier 2 (real Postgres)
- Full signal generation + broadcast cycle on test data
- Escalation protocol end-to-end: mock regime flip → notifications fire → timeout → auto-defensive
- CDN-cacheability assertion (response headers)
