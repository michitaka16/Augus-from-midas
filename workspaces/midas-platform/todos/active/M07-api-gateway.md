# M07 — API Gateway

Dependency: M04 (signal handlers), M05 (IBKR handlers), M06 (governance)
Deliverable: D4 backend + D7 backend
Package: `apps/api`

## Todos

### M07-01: Build Nexus API gateway
`apps/api/src/midas_api/channels/`
- Configure Nexus with API channel
- Mount all handlers: signals, auth, debate, approvals, backtest, settings
- CORS configuration for web + mobile origins
- Rate limiting per endpoint

### M07-02: Build auth handlers
`apps/api/src/midas_api/handlers/auth.py`
- `POST /auth/signup` — email + password, MFA setup link
- `POST /auth/login` — email + password + MFA token → JWT
- `POST /auth/refresh` — JWT refresh
- `POST /auth/mfa/setup` — TOTP setup (QR code)
- `POST /auth/mfa/verify` — TOTP verification
- Password hashing: bcrypt/argon2
- JWT with short expiry (15 min) + refresh token (7 days)

### M07-03: Build user account + subscription handlers
`apps/api/src/midas_api/handlers/account.py`
- `GET /account` — user profile
- `PUT /account/portfolio` — choose model portfolio subscription
- `PUT /account/preferences` — notification settings, timeout hours (12h–72h)
- `POST /account/ibkr/link` — initiate IBKR OAuth
- `GET /account/ibkr/callback` — IBKR OAuth callback
- `DELETE /account/ibkr/unlink` — revoke IBKR tokens

### M07-04: Build approval handlers
`apps/api/src/midas_api/handlers/approvals.py`
- `GET /approvals/pending` — list pending approvals for this user
- `POST /approvals/{id}/approve` — approve (biometric confirmed by client)
- `POST /approvals/{id}/reject` — reject
- `POST /approvals/{id}/hold` — acknowledge but hold (resets escalation timer)
- `GET /approvals/history` — past decisions

### M07-05: Build backtest API handlers
`apps/api/src/midas_api/handlers/backtests.py`
- `GET /backtests/{model_portfolio_id}/latest` — most recent backtest results
- `GET /backtests/{run_id}` — specific run (for debate agent citation links)
- `GET /backtests/{model_portfolio_id}/history` — paginated runs

### M07-06: Build debate API handler
`apps/api/src/midas_api/handlers/debate.py`
- `POST /debate/message` — send user message, receive AI response
- `GET /debate/history` — conversation history for user
- WebSocket channel for streaming responses (optional v1, fallback to polling)
- Routes to midas-debate DebateAgent (M10)

### M07-07: Build regime + strategy health handlers
`apps/api/src/midas_api/handlers/regime.py`
- `GET /regime/current` — current regime state + confidence + signals
- `GET /regime/history` — past regime transitions + outcomes (per PH3 — AI track record)
- `GET /health/strategy/{model_portfolio_id}` — strategy health dashboard (per PC2: underperformance transparency)

### M07-08: Build push notification service
`apps/api/src/midas_api/handlers/notifications.py`
- Push via Expo Push Notifications (React Native) + Web Push API
- Email via SendGrid/SES for escalation reminders
- Notification types: signal_published, regime_changed, escalation_reminder, approval_confirmed
- Strictly gated: ONLY regime flips, pending approvals, execution confirmations (per UX research — no engagement spam)

### M07-09: Wire all handlers to real packages
- Signals handler → midas-strategy signal workflow
- Debate handler → midas-debate DebateAgent
- Approval handler → midas-governance audit trail + midas-broker order submission
- Backtest handler → midas-backtest report reads
- Auth handler → DataFlow user model
- Regime handler → midas-strategy regime detector

### ~~M07-12: Build payment/subscription billing (Stripe)~~ — DEFERRED to post-beta
User decision: billing ships post-beta after user validation. v1 beta is free access.

### M07-13: Build API documentation (OpenAPI)
- Auto-generate OpenAPI spec from Nexus handlers (if supported) or manual spec
- Swagger UI at `/docs` (dev/staging only, not production)
- Document all endpoints with request/response shapes, auth requirements, rate limits

### M07-14: Build rate limiting configuration
- Per-endpoint rate limits:
  - `/auth/*`: 10 req/min per IP (brute force protection)
  - `/debate/message`: 20 req/min per user (LLM cost control)
  - `/signals/*`: 60 req/min per IP (CDN handles most, this is origin protection)
  - `/approvals/*`: 30 req/min per user
- Return `429 Too Many Requests` with `Retry-After` header
- Redis-backed counter (reuse existing Redis)

### M07-10: Test — API Tier 1 (unit)
- Auth flow: signup, login, MFA, JWT refresh
- Approval state transitions
- Notification gating logic

### M07-11: Test — API Tier 2 (integration, real Postgres)
- Full auth cycle: signup → MFA → login → JWT → access protected endpoint
- Signal endpoint returns real signal data from Postgres
- Approval flow: create pending → approve → order submitted → audit logged
- Push notification fires on regime change (mock push service, verify payload)
