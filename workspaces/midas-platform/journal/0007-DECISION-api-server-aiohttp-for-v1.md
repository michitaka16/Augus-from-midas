---
type: DECISION
date: 2026-04-12
created_at: 2026-04-12T16:00:00Z
author: agent
session_id: implement-session-1
session_turn: 45
project: midas-platform
topic: Using aiohttp as v1 HTTP server instead of full Nexus setup
phase: implement
tags: [architecture, server, aiohttp, nexus, v1]
---

# aiohttp for v1, Nexus for v2

## Decision

The API server entry point (`apps/api/src/midas_api/__main__.py`) uses aiohttp as a lightweight HTTP server for v1 development, rather than the full Nexus multi-channel deployment.

## Rationale

- Nexus requires additional configuration (channel registration, session management, middleware stack) that adds complexity before we can verify the core pipeline works
- aiohttp is a standard async Python HTTP framework with zero configuration
- The handler layer (all `*Handlers` classes) is framework-agnostic — they take a connection and return dicts
- Migrating from aiohttp to Nexus is a routing-layer swap, not a handler rewrite

## Consequences

- v1 dev server starts with `uv run python -m midas_api`
- Signal endpoints are mounted at `/signals/latest` etc. with CDN-cacheable headers
- Governance assertions run on startup — server refuses to start if publisher isolation is violated
- Migration to Nexus in v2 requires: replace aiohttp routes with Nexus channel registration, add Nexus session management, add Nexus middleware

## For Discussion

1. Should we have used Nexus from the start even if it slowed initial bring-up? The framework-first rule says yes; pragmatism says get the pipeline running first.
2. If Nexus is not installed when the API starts, should the server fall back to aiohttp automatically (current behavior) or fail loudly?
3. The handler pattern (class with async methods returning dicts) was specifically designed for framework portability. Does this pattern hold when Nexus adds WebSocket channels for debate streaming?
