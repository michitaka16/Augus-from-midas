# Midas Platform — Deployment Configuration

type: application

## Package
- **Name**: midas-platform
- **Type**: Application (not library — use /deploy, not /release)

## Infrastructure
- Database: PostgreSQL 16 + TimescaleDB + pgvector
- Cache: Redis 7
- Runtime: Python 3.12, Node.js 20

## Development Environment

```yaml
deploy_command: |
  cd deploy/docker && docker-compose up -d db redis
  cd ../.. && uv run python scripts/migrate.py migrate
  uv run python -m midas_api &
  cd apps/web && npm run dev &
deploy_check_command: curl -sf http://localhost:8000/health
smoke_test_command: curl -sf http://localhost:8000/signals/latest
user_visible_check: curl -sf http://localhost:3000 | grep -q "Midas"
production_paths:
  - packages/
  - apps/
  - shared/
  - scripts/
  - deploy/docker/
deploy_state_file: deploy/.last-deployed
```

## Pre-deploy Gates
1. CI checks pass (lint, type-check, unit tests)
2. PACT grant assertion passes (publisher/subscriber separation)
3. Database migration head matches code
4. No hardcoded API keys or model names

## Deploy Steps (Development)
```bash
# 1. Start infrastructure
cd deploy/docker && docker-compose up -d db redis

# 2. Install + migrate
uv venv && uv sync
uv run python scripts/migrate.py migrate

# 3. Seed (dev only)
MIDAS_ENV=development uv run python scripts/seed_dev.py

# 4. Start API (background)
uv run python -m midas_api &

# 5. Start web
cd apps/web && npm install && npm run dev

# 6. Verify
curl http://localhost:8000/health       # {"status": "ok"}
curl http://localhost:8000/signals/latest  # signal data
open http://localhost:3000               # Midas dashboard
```

## Staging / Production (future)
- Managed Postgres/Timescale (cloud)
- Container registry + k8s
- CDN for /signals/* endpoints
- IBKR OAuth production credentials
