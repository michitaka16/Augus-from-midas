---
type: GAP
date: 2026-04-12
created_at: 2026-04-12T12:15:00Z
author: agent
session_id: analyze-session-1
session_turn: 15
project: midas-platform
topic: IBKR OAuth production approval is an unresolved external dependency
phase: analyze
tags: [ibkr, oauth, external-dependency, critical-path, blocker]
---

# IBKR OAuth Production Approval — Unresolved

## Gap

The plan depends on IBKR Client Portal Web API via OAuth for multi-tenant user authentication. However:

- IBKR historically approves OAuth production credentials for regulated firms (RIAs, broker-dealers)
- An unregulated SaaS (which Midas v1 is, under the publisher's exemption) may not qualify
- There is no public documentation of IBKR's approval criteria for unregulated third-party apps
- The local CP Gateway fallback works for private beta but requires each user to run local software — a non-starter for a commercial product

This is the calendar-bound critical path item. Everything else in the roadmap can be built ahead of it, but the product cannot launch commercially without either:
1. IBKR OAuth production approval, OR
2. A pivot to a different integration model (e.g., read-only position sync via CSV export + user manually places orders at IBKR)

## What's Missing

- No one has contacted IBKR to begin the conversation
- No fallback plan if IBKR says no
- No timeline estimate for the approval process
- No research on whether IBKR has a "fintech partner" program for unregulated SaaS

## Proposed Resolution

Start the IBKR application conversation in Phase 1 (immediately), not Phase 3. If the answer is "no" or "get regulated first," the fallback options are:
- Option A: Launch with manual order entry (user reads signal, places order at IBKR themselves) — uglier but legally clean
- Option B: Pursue state RIA registration in parallel (pulls in v2 scope earlier)
- Option C: Partner with an existing RIA who provides the regulatory umbrella

## For Discussion

1. If IBKR denies OAuth production access for an unregulated SaaS (which is plausible), which fallback option (A: manual entry, B: RIA registration, C: RIA umbrella) best preserves the "rapid decision-to-execution" UX promise from the brief?
2. The local CP Gateway fallback requires users to run software locally. Is there a middle ground — e.g., a hosted gateway per user that Midas provisions and manages?
3. Has IBKR ever approved OAuth for a non-regulated fintech? Specific examples would de-risk this gap significantly. (Requires web research we couldn't do in this session.)
