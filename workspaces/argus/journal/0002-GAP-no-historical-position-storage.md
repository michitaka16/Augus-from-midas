---
type: GAP
date: 2026-04-18
created_at: 2026-04-18T20:51:00+09:00
author: agent
session_id: 5eb02fd9-aa3a-47ba-9b00-39629aa71c7b
session_turn: 1
project: argus
topic: Historical position storage required for backtesting
phase: analyze
tags: [backtesting, position-storage, ibkr, argus-backtest-engine]
---

## GAP: No Historical Position Storage Exists

Midas fetches positions from IBKR in real time only. There is no `positions_history` table. This is not a gap in the current Midas design — it's intentional (publisher exemption, ADR-001). But it blocks Argus's "backtest this guideline rule" feature completely.

**What would be needed**: A daily (or per-trade) snapshot of positions stored as JSON. Either:
1. Scheduled job: snapshot IBKR positions once per trading day
2. IBKR transaction replay: replay executed trades to reconstruct historical positions

**Why this matters for Week 9**: Backtesting guideline rules against historical data (e.g., "would this 30% sector cap have been violated in 2022?") cannot be done without this. Week 9 ships the forward-looking violation detector only.

**Dependency chain**: Position snapshots → backtest engine → regime-conditional clustering validation

**Source**: Failure analysis (`04-failure-modes.md`) Section 4, corroborated by reading `midas-broker/orders/positions.py` which fetches live only.

## For Discussion

1. Is daily position snapshot sufficient for guideline backtesting, or do we need per-trade snapshots? Daily is sufficient for sector allocation rules; per-trade is needed for leverage timing rules. What is the MVP scope for "backtest this guideline"?

2. Should we store snapshots in the Midas database (which already has the infrastructure) or a separate Argus database? A separate Argus database would cleanly separate the publisher exemption data (Midas) from user-specific data (Argus).

3. Who owns the snapshot job — the API server (scheduled task) or the mobile client (which fetches positions for display anyway)? If the mobile client fetches positions, could it push snapshots to the server?
