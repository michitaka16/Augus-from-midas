# M00 — Monorepo Setup

Dependency: None (first milestone)
Deliverable: D10 (Infrastructure)

## Todos

### M00-01: Initialize monorepo directory structure
Create the full directory tree from `02-plans/03-monorepo-layout.md`:
- `packages/` (midas-data, midas-strategy, midas-backtest, midas-broker, midas-debate, midas-governance)
- `apps/` (api, web, mobile)
- `shared/` (types, tokens)
- `deploy/` (docker, ci)
- `tests/` (unit, integration, e2e)
Each Python package gets `pyproject.toml`, `src/<name>/`, `__init__.py`, `tests/`.
Each JS/TS project gets `package.json`, `tsconfig.json`, `src/`.
Root `pyproject.toml` configured as workspace orchestrator.

### M00-02: Configure root Python tooling
- Root `pyproject.toml` with workspace references (uv/hatch workspaces)
- Root `conftest.py` that auto-loads `.env`
- `.env.example` with all required keys (EODHD_API_KEY, PERPLEXITY_API_KEY, LLM_MODEL, IBKR_* placeholders)
- `.gitignore` covering `.env`, `__pycache__`, `node_modules`, `.next`, `dist`
- `pytest.ini` or `pyproject.toml [tool.pytest]` with tier markers (unit, integration, e2e, regression)

### M00-03: Configure root TypeScript tooling
- Root `package.json` with npm/pnpm workspaces referencing `apps/web`, `apps/mobile`, `shared/*`
- Root `tsconfig.json` with path aliases
- `shared/types/package.json` + `shared/tokens/package.json` as shared packages
- ESLint + Prettier config

### M00-04: Configure CI/CD skeleton
- `.github/workflows/ci.yml`: lint, type-check, pytest (unit), build web, build mobile
- `.github/workflows/backtest-regression.yml` (placeholder — wired in M03)
- `.github/workflows/grounding-assertions.yml` (placeholder — wired in M10)
- Dockerfile for API service
- `deploy/deployment-config.md`

### M00-05: Database schema initialization
- DataFlow model definitions for ALL tables across all packages (placed in `packages/midas-data/src/midas_data/models/`):
  - `bars` (TimescaleDB hypertable): ticker, date, open, high, low, close, adj_close, volume, source
  - `fundamentals`: ticker, report_date, as_of_date, field, value
  - `corp_actions`: ticker, ex_date, action_type, factor, announced_date
  - `etf_universe`: ticker, inception_date, delist_date, sleeve, is_active (point-in-time)
  - `regime_signals`: date, signal_name, value, ensemble_score, regime (normal/cautious/turbulent)
  - `signals`: model_portfolio_id, timestamp, allocations_json, reasoning_json, cost_estimate, regime (NO user_id)
  - `signal_inputs`: signal_id, snapshot_json (immutable, for replay)
  - `news_items`: id, source, published_at, title, content, embedding (pgvector VECTOR(1536)), perplexity_citations_json
  - `users`: id, email, password_hash, mfa_secret, created_at (SEPARATE schema)
  - `user_preferences`: user_id, model_portfolio_id, notification_settings, timeout_hours (SEPARATE schema)
  - `user_tokens`: user_id, access_token_enc (BYTEA), refresh_token_enc (BYTEA), expires_at, scopes (SEPARATE schema, separate PG role)
  - `approvals`: user_id, signal_id, status, decided_at, method (manual/timeout-auto)
  - `audit_trail`: id, prev_hash, timestamp, event_type, payload_json, actor (TimescaleDB hypertable, append-only)
  - `backtest_runs`: id, model_portfolio_id, started_at, config_json, results_json
- Postgres role definitions: `midas_publisher` (read bars/regime/signals, write signals), `midas_subscriber` (read signals + user_preferences, write approvals), `midas_broker` (read/write user_tokens), `midas_audit` (INSERT + SELECT only on audit_trail)
- Initial migration scripts in `packages/midas-governance/src/midas_governance/migrations/`

### M00-06: Build database migration runner
- Alembic or DataFlow migrations CLI configured at project root
- `midas db migrate` command to apply all migrations
- `midas db rollback` for rollback (1 step)
- Used as init container in Docker (M12-06)
- Validate idempotency: running migrate twice is a no-op

### M00-07: Build development seed data script
- `scripts/seed_dev.py`: populates local DB with sample data for development
- Sample bars (SPY, GLD, TLT, VNQ — 1 year), sample regime signals, sample signal, sample backtest run
- Deterministic (seeded random) so local dev is reproducible
- NOT used in production — gated by `MIDAS_ENV=development` check
