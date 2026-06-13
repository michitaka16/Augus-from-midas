---
type: CONNECTION
date: 2026-04-18
created_at: 2026-04-18T20:52:00+09:00
author: agent
session_id: 5eb02fd9-aa3a-47ba-9b00-39629aa71c7b
session_turn: 1
project: argus
topic: Midas signal pipeline outputs become Argus violation detection inputs
phase: analyze
tags: [midas-allocator, argus-rule-engine, data-pipeline, reuse]
---

## Connection: The Allocator's Ephemeral Outputs Are the Rule Engine's Required Inputs

The Midas allocator computes per-sleeve features on every signal generation run:
- 126-day cumulative momentum
- 63-day covariance matrix (per-sleeve variance + cross-sleeve correlations)
- Annualized volatility
- Min-variance weights

These features exist ephemerally in the `AllocationResult` returned by `allocate()`. They are computed, used once, and discarded.

For Argus, the guideline rule engine needs the same feature computations to evaluate rules like "sector max 30%" or "beta to SPY must stay below 1.2". These are the SAME computations the allocator already does.

**The connection**: If we persist the allocator's per-sleeve features to a feature store (even just the latest values), we get:
1. The feature store needed for ETF similarity diagnostics (Challenge 2 in ML review)
2. The inputs for beta/volatility-based guideline rules without recomputation
3. A foundation for regime-conditional clustering

**What this means architecturally**: The `argus-monitor` package should share the feature computation code with `midas-strategy`, not duplicate it. The allocator's `compute_daily_returns()` and covariance matrix computation should be in `argus-shared/`, not in `midas-strategy`.

**Counterintuitive insight**: The Midas allocator and Argus rule engine are not just "reuse opportunities" — they are two consumers of the same underlying feature computation. Building one feature store serves both.

**Source**: Reading `allocator/__init__.py` (lines 65-184), `signals/workflow.py` (lines 45-160), corroborated by ML specialist review.

## For Discussion

1. Should the feature store be append-only (time series of features per sleeve) or just current values? Append-only enables regime-conditional clustering (compute features separately for normal vs turbulent periods). Current values are sufficient for forward-looking violation detection.

2. The allocator computes features per-sleeve (10 sleeves), not per-ETF (23 ETFs). Is sleeve-level granularity sufficient for Argus rules? A "max 30% tech sector" rule needs per-ETF classification (QQQ, XLK, VGT all count as tech) — does the allocator already compute this mapping?

3. The regime detector (`regime/ensemble.py`) is the most sophisticated piece of Midas. For Argus, should regime be an INPUT to guideline evaluation ("in turbulent regimes, TLT behaves like equity — reclassify it") or a separate monitoring concern?
