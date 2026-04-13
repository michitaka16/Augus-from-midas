# Midas v1 — Monorepo Layout

Root: `/Users/takahidekawabe/Documents/GitHub/disease-risk-identifier/midas/`

```
midas/
├── pyproject.toml                  # Root project, workspace orchestration
├── .env                            # API keys (EODHD, Perplexity, IBKR), model names
├── conftest.py                     # Root conftest, auto-loads .env
│
├── packages/
│   ├── midas-data/                 # D1: Data fabric
│   │   ├── src/midas_data/
│   │   │   ├── sources/            # EODHD, FRED, Yahoo, Perplexity adapters
│   │   │   ├── fabric/             # Cache layer, invalidation, PIT universe
│   │   │   ├── models/             # DataFlow models (bars, fundamentals, news, corp_actions)
│   │   │   └── quality/            # Gap detection, reconciliation, bad-tick filter
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── midas-strategy/             # D2: Strategy engine
│   │   ├── src/midas_strategy/
│   │   │   ├── regime/             # Ensemble detector, signal definitions
│   │   │   ├── allocator/          # AAA, HRP, vol-target, turnover penalty
│   │   │   ├── cost/               # TransactionCostNode (IBKR fees + slippage + impact)
│   │   │   ├── signals/            # Signal generation workflow, TimeSourceNode
│   │   │   └── sleeves/            # 8 asset sleeve definitions + ETF tickers
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── midas-backtest/             # D3: Backtest engine
│   │   ├── src/midas_backtest/
│   │   │   ├── engine/             # Walk-forward, CPCV, embargo
│   │   │   ├── metrics/            # Deflated Sharpe, PBO, regime-conditional stats
│   │   │   ├── replay/             # Nightly live-vs-backtest replay
│   │   │   └── reports/            # Report generation (JSON + human-readable)
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── midas-broker/               # D5: IBKR integration
│   │   ├── src/midas_broker/
│   │   │   ├── ibkr/               # CP Web API client, OAuth, local Gateway fallback
│   │   │   ├── orders/             # Order preview, submission, position sync
│   │   │   └── paper/              # Paper trading adapter
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── midas-debate/               # D6: Debate agent
│   │   ├── src/midas_debate/
│   │   │   ├── agent/              # DebateAgent, DebateSignature
│   │   │   ├── tools/              # Dumb data endpoints (fetch_signal, etc.)
│   │   │   ├── grounding/          # Citation verification, ungrounded_claims check
│   │   │   └── scenarios/          # Counter-scenario generator
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── midas-governance/           # D9: PACT governance
│       ├── src/midas_governance/
│       │   ├── envelopes/          # Publisher/subscriber envelopes
│       │   ├── audit/              # Append-only audit trail
│       │   └── migrations/         # Postgres role GRANT/REVOKE SQL
│       ├── tests/
│       └── pyproject.toml
│
├── apps/
│   ├── api/                        # D4 + D7-backend: Nexus API gateway
│   │   ├── src/midas_api/
│   │   │   ├── channels/           # Nexus channel configs
│   │   │   ├── handlers/           # Signal broadcast, debate, approvals, auth
│   │   │   └── scheduler/          # Weekly signal cron, data refresh cron
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── web/                        # D7: Next.js web application
│   │   ├── src/
│   │   │   ├── app/                # Next.js app router
│   │   │   ├── components/         # shadcn + custom
│   │   │   └── lib/                # API client, state, hooks
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── mobile/                     # D8: React Native Expo
│       ├── src/
│       │   ├── screens/            # Approval, dashboard, debate, settings
│       │   └── components/
│       ├── app.json
│       └── package.json
│
├── shared/
│   ├── types/                      # Shared TypeScript domain types (packages/core)
│   │   ├── src/
│   │   └── package.json
│   └── tokens/                     # Design tokens (packages/tokens)
│       ├── src/
│       └── package.json
│
├── deploy/
│   ├── deployment-config.md
│   ├── docker/
│   └── ci/                         # GitHub Actions workflows
│
├── tests/
│   ├── unit/                       # Tier 1
│   ├── integration/                # Tier 2 (real Postgres)
│   └── e2e/                        # Tier 3 (Playwright + paper IBKR)
│
└── workspaces/
    └── midas-platform/             # COC workspace (analysis, plans, journal)
```

## Dependency Graph

```
midas-data ← midas-strategy ← midas-backtest
                             ← midas-broker
                             ← midas-debate (reads signals, backtests, costs)
midas-governance (cross-cutting, enforces envelope separation)
midas-api (orchestrates all packages via Nexus)
web / mobile (consume midas-api)
```

## Key Design Rules

1. `midas-strategy` NEVER imports from `midas-broker` or `midas-debate`. Strategy is pure computation.
2. `midas-data/models/` defines DataFlow models. No other package defines tables.
3. `midas-debate/tools/` are dumb data endpoints — they call `midas-data` and `midas-strategy` read APIs. No decision logic.
4. `midas-governance/envelopes/` is the source of truth for what each Postgres role can access. Migrations derive from envelopes.
5. Signal publication happens in `midas-api/handlers/` — it reads from `midas-strategy`, writes to the signals table (via DataFlow), and never touches `users.*`.
