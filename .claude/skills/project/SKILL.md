# Midas Platform — Project Skills

Quick-reference knowledge for the Midas autonomous portfolio manager.

## Architecture

Midas is an **impersonal publisher** of regime-aware multi-asset ETF model portfolios (US publisher's exemption, Lowe v. SEC). 5 portfolios, 10 sleeves, IBKR-native, debate-with-AI.

### Package Map
| Package | Purpose | Key File |
|---|---|---|
| `midas-data` | Data fabric (EODHD, FRED, Yahoo, Perplexity, Redis cache) | `fabric/__init__.py` |
| `midas-strategy` | Regime detection, AAA allocator, cost model, signal workflow | `signals/workflow.py` |
| `midas-backtest` | Walk-forward, CPCV, metrics, replay, reports | `engine/walkforward.py` |
| `midas-broker` | IBKR CP API, OAuth (AES-256-GCM), orders, paper trading | `ibkr/client.py` |
| `midas-debate` | Kaizen debate agent, grounding contract, counter-scenarios | `agent/debate.py` |
| `midas-governance` | PACT envelopes, boot-time assertions, chain-hashed audit | `assertions.py` |
| `midas-api` | aiohttp gateway (v1), 25 routes, JWT auth, CORS | `__main__.py` |

### LLM Provider Chain
MiniMax → ZAI → OpenAI → Anthropic. All OpenAI-compatible except Anthropic.

### CLI Scripts
```bash
scripts/migrate.py migrate          # Apply DB migrations
scripts/seed_dev.py                 # Seed dev data
scripts/verify_eodhd_delisted.py    # BLOCKER: verify PIT universe source
scripts/load_historical.py          # Load 26 years of data
scripts/generate_signals.py         # Generate signals for all 5 portfolios
scripts/run_backtest.py growth      # Run backtest with benchmark gates
```

## Critical Constraints
1. `signals` table has **NO user_id** — structural enforcement via PACT
2. Boot-time assertion blocks API startup if publisher role has user grants
3. Debate agent is **LLM-first** — zero deterministic routing
4. Turbulent escalation: 24h default auto-defensive timeout
5. All API keys from `.env`, model names from `DEFAULT_LLM_MODEL`

## Sub-Files
- [midas-strategy-quick.md](midas-strategy-quick.md) — Strategy engine cheatsheet
- [midas-compliance-quick.md](midas-compliance-quick.md) — Publisher exemption rules
- [pool-safety.md](pool-safety.md) — DataFlow pool safety (inherited)

