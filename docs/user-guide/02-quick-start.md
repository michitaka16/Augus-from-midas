# 02 — Quick Start

Get Midas running on your machine in under 10 minutes.

## Prerequisites

Install these first (one-time):

```bash
# Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Docker Desktop — for Postgres + Redis
brew install --cask docker
# Then open Docker Desktop from Applications and wait for it to start

# uv — Python package manager (fast, handles virtualenvs)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Node.js 20 — for the web frontend
brew install node@20
```

Verify everything is installed:

```bash
docker --version    # Docker version 29.x+
uv --version        # uv 0.11.x+
node --version      # v20.x.x
npm --version       # 10.x.x
```

## Step 1: Clone and configure

```bash
cd ~/Documents/GitHub
git clone <your-repo-url> midas
cd midas

# Create .env from template
cp .env.example .env
```

Open `.env` in your editor and fill in:

```bash
# Required for basic operation
DATABASE_URL=postgresql://midas:midas_dev@localhost:5432/midas
JWT_SECRET_KEY=change-this-to-a-random-32-char-string
IBKR_TOKEN_ENCRYPTION_KEY=<64-hex-char-string>   # openssl rand -hex 32

# Required for real signals (Phase 2)
EODHD_API_KEY=your-eodhd-key-here                # https://eodhd.com
FRED_API_KEY=your-fred-key-here                  # optional, for higher rate limits
PERPLEXITY_API_KEY=pplx-your-key-here            # optional, for news search

# Required for debate AI (Phase 2) — pick ONE
MINIMAX_API_KEY=your-minimax-key
DEFAULT_LLM_MODEL=MiniMax-Text-01
# OR
OPENAI_API_KEY=sk-proj-your-key
DEFAULT_LLM_MODEL=gpt-4o-mini
# OR
ANTHROPIC_API_KEY=sk-ant-your-key
DEFAULT_LLM_MODEL=claude-sonnet-4-6

# Required for IBKR integration (Phase 2)
IBKR_CLIENT_ID=your-ibkr-app-id
IBKR_CLIENT_SECRET=your-ibkr-app-secret
```

> **Note**: Phase 1 (the current deployment) works without any API keys except `DATABASE_URL` and `JWT_SECRET_KEY`. You'll see seed data instead of live signals. This is fine for exploring the interface.

## Step 2: Start infrastructure

```bash
cd deploy/docker
docker-compose up -d db redis
cd ../..

# Verify
docker-compose -f deploy/docker/docker-compose.yml ps
# Both db and redis should show "Up (healthy)"
```

## Step 3: Install Python dependencies

```bash
uv venv
uv sync

# Also install the editable packages explicitly (Python 3.14 workaround)
uv pip install -e packages/midas-governance -e packages/midas-data \
  -e packages/midas-strategy -e packages/midas-backtest \
  -e packages/midas-broker -e packages/midas-debate -e apps/api
```

## Step 4: Run database migrations

```bash
.venv/bin/python scripts/migrate.py migrate
```

You should see:
```
migration.applied filename=0001_initial_schema.sql
migration.applied filename=0002_debate_history.sql
migrations.complete applied_count=2
```

This creates:
- All tables (bars, signals, regime_signals, news_items, users, approvals, audit_trail, etc.)
- 4 Postgres roles (midas_publisher, midas_subscriber, midas_broker, midas_audit)
- GRANT permissions that structurally enforce the publisher exemption

## Step 5: Seed development data

```bash
MIDAS_ENV=development .venv/bin/python scripts/seed_dev.py
```

This loads:
- 12 ETFs into the universe (SPY, GLD, TLT, VNQ, LQD, VWO, etc.)
- ~1008 bars (4 tickers × ~252 trading days)
- 1 regime signal snapshot (normal regime)
- 1 sample signal for the Growth portfolio

## Step 6: Start the API server

```bash
.venv/bin/python scripts/start_api.py &
```

You should see:
```
assertion.publisher_isolation.PASSED
assertion.audit_immutability.PASSED
assertion.broker_isolation.PASSED
assertions.all_passed
server.listening port=8000
```

Test it:
```bash
curl http://localhost:8000/health
# {"status": "ok"}

curl http://localhost:8000/signals/latest | python3 -m json.tool
# Shows the Growth portfolio with 8 sleeves, regime=normal
```

## Step 7: Start the web frontend

In a new terminal:
```bash
cd ~/Documents/GitHub/midas
npm run dev:web
```

You should see:
```
▲ Next.js 14.2.x
- Local: http://localhost:3000
✓ Ready in 1s
```

## Step 8: Open the app

Navigate to http://localhost:3000 in your browser. You should see:
- Midas dashboard with a green "Normal" regime banner
- The Growth portfolio allocation across 8 sleeves
- A left sidebar with Dashboard, Signals, Approvals, Debate, Backtests, Trade Log, Settings

Click "Sign up" and create an account to access authenticated features.

## Step 9: Verify everything works

```bash
# From the midas directory
bash <<'EOF'
echo "=== Health ==="
curl -sf http://localhost:8000/health && echo ""

echo "=== Signals ==="
curl -sf http://localhost:8000/signals/latest | python3 -c "
import sys,json; d=json.load(sys.stdin)
s=d['signals'][0]
print(f\"  {s['model_portfolio_id']}: {len(s['allocations'])} sleeves, regime={s['regime']}\")
"

echo "=== Web pages ==="
for p in "/" "/signals" "/approvals" "/debate" "/backtests" "/audit" "/settings" "/login" "/signup"; do
  STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:3000$p")
  printf "  %-15s %s\n" "$p" "$([ $STATUS = 200 ] && echo '✓' || echo "✗ $STATUS")"
done
EOF
```

All checks should show ✓.

## What you can do now (Phase 1)

- Browse the dashboard and see regime state + allocation
- Sign up, log in, switch model portfolios
- View the audit trail (empty until first signal publishes)
- View settings and adjust timeout / notification preferences
- See the debate chat interface (will show "configure LLM key" until Phase 2)

## What you CAN'T do yet (Phase 2)

- Get real responses from the debate AI — needs a working LLM API key
- Load 26 years of historical market data — needs EODHD API key + running `scripts/load_historical.py` (takes hours)
- Run backtests on real data — requires the historical load
- Execute real trades via IBKR — requires IBKR OAuth production approval
- Publish real weekly signals — requires all of the above

## Stopping the stack

```bash
# Stop API
lsof -ti:8000 | xargs kill

# Stop web
lsof -ti:3000 | xargs kill

# Stop infrastructure
cd deploy/docker && docker-compose down
```

## Resetting the database

```bash
cd deploy/docker
docker-compose down -v  # -v deletes the volume
docker-compose up -d db redis
cd ../..
.venv/bin/python scripts/migrate.py migrate
MIDAS_ENV=development .venv/bin/python scripts/seed_dev.py
```

---

**Next**: [03 — Your First Week](03-first-week.md)
