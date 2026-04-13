---
type: RISK
date: 2026-04-12
created_at: 2026-04-12T13:00:00Z
author: agent
session_id: analyze-session-1
session_turn: 22
project: midas-platform
topic: Fundamental tension between don't-trade-without-permission and don't-make-me-monitor
phase: analyze
tags: [risk, ux, regime, turbulent, timeout, user-brief-conflict]
---

# The Freeze Timeout Tension

## Risk

The user's brief contains two requirements that directly conflict:
1. "Turbulent markets — don't trade without my permission"
2. "I don't want to monitor it"

If the system detects a turbulent regime and the user doesn't respond, the system must either:
- (a) Stay frozen (honors requirement 1, violates requirement 2 — user loses money while not monitoring)
- (b) Auto-execute defensively (honors requirement 2, violates requirement 1 — traded without explicit permission)

Red team flagged this as CRITICAL. Resolution: a 48h configurable escalation protocol that defaults to defensive auto-execution after timeout. This is a compromise — not a clean solution. The user should understand that "I don't want to monitor" + "always ask me first" requires accepting one of these escape hatches.

## For Discussion

1. The 48h default timeout was chosen as a "reasonable" middle ground. But in March 2020, the S&P lost 12% in 2 trading days. Would a 48h timeout have been too slow? Should the default be 24h with the option to extend?
2. If the auto-defensive action is "move to cash + short bonds" and the market recovers sharply (V-shaped recovery like April 2020), the user misses the rebound AND pays transaction costs both ways. Should the escalation protocol include a "partial defensive" option (reduce equity by 50%, not 100%)?
3. Is there a third option beyond "freeze" and "auto-execute" — for example, progressively tightening stop-losses on existing positions while waiting for user response?
