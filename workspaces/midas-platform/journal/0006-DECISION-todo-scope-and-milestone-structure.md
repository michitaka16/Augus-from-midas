---
type: DECISION
date: 2026-04-12
created_at: 2026-04-12T14:00:00Z
author: agent
session_id: todos-session-1
session_turn: 30
project: midas-platform
topic: 160 todos across 13 milestones with strict build/wire separation and red-team patched gaps
phase: todos
tags: [planning, milestones, scope, build-wire-separation]
---

# Todo Scope and Milestone Structure

## Decision

160 todos organized across 13 milestones (M00–M12), covering the complete v1 scope from monorepo setup through launch hardening. Red team identified 15 gaps which were patched before approval gate.

## Structure Rationale

Milestones follow the dependency graph, not arbitrary phases:
- M00 (monorepo) → M01 (data) → M02 (strategy) → M03 (backtest) → M04 (signals)
- M00 → M05 (IBKR) ← independent of M01–M04
- M00 → M06 (governance) ← independent, cross-cutting
- M04+M05+M06 → M07 (API gateway) — first integration point
- M07 → M08 (web) + M09 (mobile) — frontend consumes API
- M01+M02+M03 → M10 (debate agent) — needs data to cite
- M00 → M11 (shared types) — consumed by M08+M09
- All → M12 (hardening)

## Key Decision: Build + Wire Separation

Every component that produces or consumes data has separate build (logic) and wire (integration) todos. This catches the #1 cause of "it looks done but doesn't work" — mock data surviving into production.

## For Discussion

1. 160 todos is large. Would splitting into v1-alpha (data + strategy + backtest + API, no frontend) and v1-beta (frontend + debate + hardening) create a useful intermediate milestone, or would the split just add coordination overhead?
2. The web app (M08) has 27 todos — nearly 17% of the total. Is the screen count (dashboard, signal detail, approvals, debate, backtest explorer, trade log, regime history, settings, strategy health, onboarding + error pages + accessibility) correct, or can any screens be deferred to v1.1?
3. Stripe billing (M07-12) was a red-team addition, not in the original brief. The user said "commercializable" but didn't specify billing. Should billing be v1 scope or deferred until post-beta user validation?
