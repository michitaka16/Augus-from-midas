---
type: DECISION
date: 2026-04-13
created_at: 2026-04-13T10:00:00Z
author: agent
session_id: codify-session-1
session_turn: 5
project: midas-platform
topic: Codified 2 project agents and 3 project skills from implementation sessions
phase: codify
tags: [codify, agents, skills, institutional-knowledge]
---

# Codified Project Agents and Skills

## Decision

Created 2 project-specific agents and 3 project-specific skills (+ updated SKILL.md) to capture institutional knowledge from the /analyze + /implement sessions.

### Agents Created
1. **midas-strategy-expert** — Regime detection ensemble, AAA allocator, cost model, backtest parity. Use for any strategy question.
2. **midas-compliance-reviewer** — Publisher exemption enforcement, PACT envelopes, audit trail. Use for code review of changes touching signals/users separation.

### Skills Created
1. **SKILL.md** (updated) — Package map, CLI scripts, critical constraints. Answers 80% of questions without sub-file reads.
2. **midas-strategy-quick.md** — Ensemble weights, sleeve tickers, AAA pipeline, cost model components.
3. **midas-compliance-quick.md** — DO/DO NOT for publisher exemption, structural enforcement checklist.

### Docs Created
1. **docs/00-authority/README.md** — Authoritative product description, quick start, architecture diagram, 5 portfolios.

## Rationale

The publisher exemption constraint (ADR-001) is the most commonly violated rule — it shapes every code change. Without a dedicated compliance reviewer agent, future sessions will accidentally add user_id to signal queries or use "your portfolio" language. The strategy expert captures the ensemble weights and allocation logic that would otherwise require reading 4+ files to reconstruct.

## For Discussion

1. Should the compliance reviewer be elevated to a mandatory gate (like security-reviewer) that runs on every PR, or is it sufficient as an on-demand agent?
2. The strategy skill has specific numbers (weights, thresholds, fee rates) that could change during backtest tuning. Should these be extracted to a config file and the skill reference the config, or is the current approach (human-readable in the skill) better for fast comprehension?
