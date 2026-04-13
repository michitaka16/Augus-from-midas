# Midas Platform

Regime-aware multi-asset ETF portfolio manager with transparent backtests and an AI debate layer.

## What it is

Midas publishes impersonal model portfolios — the same signals to all subscribers at the same time. It detects market regime shifts (normal / cautious / turbulent) using an 8-signal ensemble, allocates across 10 asset sleeves via Adaptive Asset Allocation, and lets you debate its reasoning with a grounded AI agent that cites every claim to a real signal, backtest, or cost model output.

## What it is NOT

- Not personalized investment advice (operates under US publisher's exemption)
- Not real-time trading (screen-active pull, not streaming)
- Not options/leverage/single-stock (ETF universe only)
- Not international in v1 (US-only; UK/SG/EU geofenced)

## Quick Start

```bash
cp .env.example .env     # Fill: MINIMAX_API_KEY, DATABASE_URL, EODHD_API_KEY
cd deploy/docker && docker-compose up -d db redis
uv venv && uv sync
uv run python scripts/migrate.py migrate
MIDAS_ENV=development uv run python scripts/seed_dev.py
uv run python -m midas_api &
cd apps/web && npm install && npm run dev
# Open http://localhost:3000
```

## Architecture

```
User (web/mobile)
  ↓
API Gateway (aiohttp, 25 routes, JWT auth)
  ↓                    ↓                  ↓
Signal Broadcast   Debate Agent       Approvals
(impersonal,       (Kaizen, LLM-     (per-user,
 CDN-cacheable)     first, grounded)   JWT-protected)
  ↓                    ↓                  ↓
Strategy Engine    Data Fabric        IBKR Broker
(regime detect,    (EODHD, FRED,     (CP API, OAuth,
 AAA allocator,     Redis cache,      AES-256-GCM
 cost model)        pgvector)          tokens)
  ↓
Backtest Engine    Governance
(walk-forward,     (PACT envelopes,
 CPCV, PBO,         boot-time assert,
 benchmark gates)   chain-hashed audit)
```

## 5 Model Portfolios

| Portfolio | Vol Target | Style |
|---|---|---|
| Aggressive Growth | 18% | Max momentum allocation |
| Growth | 14% | Diversified top sleeves |
| Balanced | 10% | Mix of equity + bonds |
| Conservative | 6% | Heavy bond allocation |
| Income | 6% | Dividend + REIT bias |

## License

See [LICENSE](../../LICENSE).
