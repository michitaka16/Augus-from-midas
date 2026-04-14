# 15 — Troubleshooting

Common problems and their fixes. Organized by symptom.

## The stack won't start

### "Docker command not found"

Install Docker Desktop:
```bash
brew install --cask docker
# Then open Docker Desktop from Applications
```

Wait for Docker to fully start (whale icon in menu bar stops animating).

### "docker-compose up" hangs or fails

```bash
# Check Docker is running
docker ps
# If this fails, Docker Desktop isn't running

# Check disk space
df -h
# Docker needs 5+ GB free

# Reset Docker
docker system prune -a  # removes all unused images/containers
```

### "uv command not found"

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### "Port 5432 already in use"

Another Postgres is running on your machine. Options:

```bash
# Option 1: Find and stop the other Postgres
lsof -i :5432
# Kill the PID shown

# Option 2: Use a different port for docker-compose
# Edit deploy/docker/docker-compose.yml, change "5432:5432" to "5433:5432"
# Then update DATABASE_URL in .env: postgresql://midas:midas_dev@localhost:5433/midas
```

### "Port 6379 already in use"

Another Redis is running. Same options as Postgres:
```bash
lsof -i :6379
# Kill, or change port to 6380 in docker-compose.yml
```

## Migrations fail

### "ModuleNotFoundError: No module named 'midas_governance'"

Python 3.14 editable install issue. Fix:
```bash
uv pip install -e packages/midas-governance -e packages/midas-data \
  -e packages/midas-strategy -e packages/midas-backtest \
  -e packages/midas-broker -e packages/midas-debate -e apps/api
```

If still failing, the scripts/migrate.py has a workaround that adds package paths to `sys.path`. Use it:
```bash
.venv/bin/python scripts/migrate.py migrate
```

### "relation users.accounts does not exist"

Migrations haven't run. Run:
```bash
.venv/bin/python scripts/migrate.py migrate
```

### "role midas_publisher does not exist"

Same — migrations haven't applied the GRANT statements. Run migrations.

### "could not translate host name 'db'"

You're trying to use the docker-compose hostname from outside the Docker network. Use `localhost` in `.env`:
```bash
DATABASE_URL=postgresql://midas:midas_dev@localhost:5432/midas
```

## API won't start

### "No module named midas_api"

Python path issue. Use the launcher:
```bash
.venv/bin/python scripts/start_api.py
```

NOT `.venv/bin/python -m midas_api` (broken on Python 3.14).

### "Cannot run the event loop while another loop is running"

aiohttp + asyncio bug on Python 3.14. Should be fixed in the current code (uses `AppRunner` + `TCPSite`). If you see this, ensure you're on the latest commit:
```bash
git log -1 apps/api/src/midas_api/__main__.py
```

### "Governance assertion FAILED"

The boot-time check found that the `midas_publisher` role has grants on user tables, violating the publisher exemption.

```bash
# Connect to Postgres
docker exec -it docker-db-1 psql -U midas

# Check grants
SELECT * FROM information_schema.role_table_grants
WHERE grantee = 'midas_publisher'
  AND table_schema IN ('users', 'tokens');

# Revoke any grants shown
REVOKE ALL ON SCHEMA users FROM midas_publisher;
REVOKE ALL ON SCHEMA tokens FROM midas_publisher;
```

Re-run migrations to apply the correct grants.

### "Port 8000 already in use"

```bash
lsof -ti:8000 | xargs kill
# Wait 2 seconds, then restart API
```

## Web won't start

### "next: command not found"

Dependencies not installed. From root:
```bash
npm install
npm run dev:web
```

### "Cannot find module 'react-dom/server.browser.js'"

Root node_modules has conflicting React versions (likely from apps/mobile). Fix:

```bash
# Ensure apps/mobile is NOT in the root package.json workspaces
cat package.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('workspaces'))"
# Should show: ['apps/web', 'shared/types', 'shared/tokens']  — no mobile

# Clean and reinstall
rm -rf node_modules apps/web/node_modules apps/web/.next package-lock.json
npm install
npm run dev:web
```

### "Error: ENOSPC: System limit for number of file watchers reached"

Increase file watcher limit:
```bash
# macOS
sudo sysctl -w kern.maxfiles=65536
sudo sysctl -w kern.maxfilesperproc=65536

# Linux
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### "500 Internal Server Error" on all pages

Check the web log:
```bash
tail -30 /tmp/midas_web.log
```

Usually a React hydration error or missing module. Restart:
```bash
lsof -ti:3000 | xargs kill
cd apps/web
rm -rf .next
cd ../..
npm run dev:web
```

## Dashboard shows "Could not connect to API"

### API is down
```bash
curl http://localhost:8000/health
# Should return {"status": "ok"}
```

If it fails, restart the API (see "API won't start" above).

### CORS issue
Check browser console for CORS errors. The API allows `http://localhost:3000` by default. If you're accessing from a different origin, update `CORS_ORIGINS` in `apps/api/src/midas_api/channels/__init__.py`.

## Debate agent fails

### "All configured LLM API keys were rejected (401 Unauthorized)"

Your LLM keys are invalid. Get a working one from:
- https://platform.openai.com/api-keys (OpenAI)
- https://console.anthropic.com (Anthropic)
- https://intl.minimaxi.com (MiniMax)
- https://open.bigmodel.cn (ZhipuAI)

Update `.env` and restart the API:
```bash
lsof -ti:8000 | xargs kill
.venv/bin/python scripts/start_api.py &
```

### "Could not connect to the LLM API"

DNS or network issue. Check `MINIMAX_API_BASE` and `ZAI_API_BASE` in `.env` are correct URLs.

Test directly:
```bash
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
# Should return a list of models
```

### "Response contains unverified claim"

The LLM cited an ID that doesn't exist in the database. This happens rarely when the LLM hallucinates. The grounding check catches it. The response is shown with a warning. Don't trust the claim.

### AI response takes > 60 seconds

LLM is slow (MiniMax can be slow during peak hours). Options:
- Switch primary provider: move ZAI or OpenAI to position 1 in the fallback chain
- Use a faster model: change `DEFAULT_LLM_MODEL` to `gpt-4o-mini` or `claude-haiku-4-5`

## Approvals don't appear

### No pending approvals shown

Check:
```bash
# API side
curl http://localhost:8000/approvals/pending -H "Authorization: Bearer $TOKEN"
# Should return {"approvals": [...], "count": N}
```

If empty, no signals have published yet. In dev mode, run:
```bash
.venv/bin/python scripts/generate_signals.py 2026-04-13
```

This publishes a signal which (in dev mode) also creates approval records for existing users.

### Approvals page crashes

Check browser console. Most likely the API returned unexpected shape. Check:
```bash
curl http://localhost:8000/approvals/pending -H "Authorization: Bearer $TOKEN"
# Verify JSON structure matches what the page expects
```

## Signals show stale data

### "Last updated" is from yesterday

Signal generation runs Sunday 7 PM ET. If today's Tuesday and you haven't had a new signal, that's normal — it waits until next Sunday.

To force a signal in dev:
```bash
.venv/bin/python scripts/generate_signals.py $(date +%Y-%m-%d)
```

### Regime signal is empty

The regime detector needs FRED data. If FRED API is down or rate-limited:
```bash
# Check data fabric
curl http://localhost:8000/regime/current
# If regime field is "normal" and all signals are 0, that's default/fallback behavior
```

Run `scripts/load_historical.py` to backfill FRED data.

## IBKR connection fails

### "OAuth exchange failed: 401"

Your `IBKR_CLIENT_ID` or `IBKR_CLIENT_SECRET` in `.env` is wrong, OR IBKR hasn't approved your OAuth application yet (production approval takes 2-4 weeks).

Beta workaround: use the local CP Gateway. See chapter 14.

### "connection refused on localhost:5000"

CP Gateway isn't running. Start it:
```bash
cd /path/to/ibkr/cp-gateway
./bin/run.sh
```

Log into IBKR via the browser at `https://localhost:5000`. Gateway must stay running.

### "Certificate error" on localhost:5000

CP Gateway uses a self-signed cert. Accept it in your browser (one-time). For the Python client, we already disable SSL verification (only safe for local gateway).

### Orders fail with "Insufficient buying power"

You don't have enough cash in IBKR to execute the buys. Check your IBKR balance. Midas doesn't know your balance, so it can't prevent this upstream.

### Orders fail with "Stock halted"

IBKR halted trading on a specific ETF. Wait for the halt to clear, then retry the approval.

## Tests fail

### "ImportPathMismatchError"

Use importlib mode for pytest:
```bash
PYTHONPATH="packages/midas-data/src:packages/midas-strategy/src:..." \
.venv/bin/python -m pytest --import-mode=importlib
```

### "async def functions are not natively supported"

Install pytest-asyncio:
```bash
uv pip install pytest-asyncio
```

### "Sharpe ratio = 0"

The test uses constant returns which have zero standard deviation. Expected — the test should use `random.gauss` for varying returns.

## Database gets corrupted

### "duplicate key value violates unique constraint"

Most likely: seed script ran twice. Reset:
```bash
cd deploy/docker
docker-compose down -v  # -v deletes volumes
docker-compose up -d db redis
cd ../..
.venv/bin/python scripts/migrate.py migrate
MIDAS_ENV=development .venv/bin/python scripts/seed_dev.py
```

### Can't connect to database

Check the container is healthy:
```bash
docker-compose -f deploy/docker/docker-compose.yml ps
# Both db and redis should show "healthy"
```

If not:
```bash
docker-compose -f deploy/docker/docker-compose.yml logs db
# Look for the actual error
```

## Performance issues

### Web feels slow

Check the Next.js dev server has compiled the page. First load is slower. Refresh once and subsequent loads are fast.

### API responses are slow

Check Postgres isn't overloaded:
```bash
docker stats docker-db-1
# CPU should be < 50%
```

If high, run `VACUUM ANALYZE` to refresh statistics:
```bash
docker exec -it docker-db-1 psql -U midas -c "VACUUM ANALYZE;"
```

### Dashboard polling burns battery

The dashboard polls every 60s when tab is active. If battery life is a concern, close the tab when not using.

Mobile doesn't poll in the background — only push notifications wake it.

## Data is wrong

### "Regime says normal but I see the market is crashing"

Check the regime panel. The ensemble score may be rising but hasn't crossed the cautious threshold yet. Hysteresis requires 2 consecutive days above threshold before flipping.

Check the 8 signals individually. If HY OAS is 650bps and rising, a flip to cautious is imminent.

### "Cost estimate is wildly wrong"

The cost model uses historical spreads. If you're in a high-vol regime not well-represented in training data, costs may underestimate. The model widens 1.5-2x in turbulent regime, but specific ETF spreads can widen even more.

This is why there's a cost cap: max 1% of trade value per order (IBKR's rule).

### "Allocation jumps around week-to-week"

Check turnover. If > 30% weekly, either:
1. Regime just flipped (expected)
2. Momentum signal is near-degenerate (HRP fallback may be active)
3. Bug — report to ops

## Logging and debugging

### Enable debug logs

In `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

Restart API. Logs will be much more verbose.

### View all API logs
```bash
tail -f /tmp/midas_api.log
```

### View web dev logs
```bash
tail -f /tmp/midas_web.log
```

### View Postgres logs
```bash
docker-compose -f deploy/docker/docker-compose.yml logs -f db
```

### View Redis logs
```bash
docker-compose -f deploy/docker/docker-compose.yml logs -f redis
```

## Complete reset

Nuclear option — reset everything:

```bash
# Stop everything
lsof -ti:8000,3000 | xargs kill 2>/dev/null
cd deploy/docker && docker-compose down -v
cd ../..

# Clean Python
rm -rf .venv
uv venv
uv sync
uv pip install -e packages/midas-governance -e packages/midas-data \
  -e packages/midas-strategy -e packages/midas-backtest \
  -e packages/midas-broker -e packages/midas-debate -e apps/api

# Clean Node
rm -rf node_modules apps/web/node_modules apps/web/.next package-lock.json
npm install

# Start fresh
cd deploy/docker && docker-compose up -d db redis
cd ../..
.venv/bin/python scripts/migrate.py migrate
MIDAS_ENV=development .venv/bin/python scripts/seed_dev.py
.venv/bin/python scripts/start_api.py &
npm run dev:web
```

If after this it still doesn't work, check the `.env` file — most "it broke" issues trace back to misconfigured environment variables.

## Getting help

- **Technical issues**: open an issue in the GitHub repo
- **Strategy questions**: use the Debate chat
- **Billing**: email `billing@midas.app`
- **Security issues**: email `security@midas.app` (do NOT file public issues)

---

**Next**: [16 — Security & Privacy](16-security.md)
