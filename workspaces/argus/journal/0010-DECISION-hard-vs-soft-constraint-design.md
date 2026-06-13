---
type: DECISION
date: 2026-04-19
created_at: 2026-04-19T00:00:00
author: co-authored
session_id: current
project: argus
topic: Hard vs soft constraint design for guideline rule violations
phase: design
tags: [constraint-design, hard-constraints, soft-constraints, rule-engine]
---

## Decision: Hard vs Soft Constraint Design

### The Design Question

When a guideline rule is violated, should the system treat it as a binary alert (hard constraint) or a continuous risk score (soft constraint)?

- **Hard constraint**: "Your tech sector allocation is 35% — the guideline is 30%. This is a violation." → Triggers RED alert.
- **Soft constraint**: "Your tech sector allocation score is 0.72 — the guideline target is 1.0." → Triggers YELLOW warning but does not block.

### Options Considered

**Hard Constraints Only**: Clear, unambiguous alerts. Matches how investors think about rules. Simpler to implement. Cons: Ignores magnitude of violation — 30.1% overage and 60% allocation both trigger the same alert.

**Soft Constraints Only**: Captures proximity to violation. Can alert before the rule is broken. More useful for proactive risk management. Cons: "My score is 0.72" is harder to interpret than "you violated a rule." Introduces calibration questions.

### Selected Design: Hybrid (Hard = RED, Soft = YELLOW)

Every constraint has a **type** — hard or soft — chosen at the preset level and customizable per constraint:

- **HARD**: Violation triggers RED status. Used for rules with zero tolerance (e.g., no emerging market exposure, no weapons manufacturers).
- **SOFT**: Violation triggers YELLOW warning. Used for rules where some deviation is acceptable but noteworthy (e.g., approaching the energy sector limit, drifting from the target country mix).

**Rationale**:
- The hard/soft distinction maps directly to investor mental models: "I never want this" vs "I'd prefer to avoid this but it's not a disaster"
- The distinction is per-constraint, not global. A user can set "max 30% tech" as hard and "max 2x beta" as soft.
- Magnitude is captured in the threshold slider — changing a threshold from 0% to 30% explicitly acknowledges that 0–30% is acceptable under the soft constraint.

**Acknowledged complexity**: This requires defining how the threshold maps to a status for each rule type. The current implementation: threshold is the maximum tolerable fraction (for a max constraint) or minimum required fraction (for a min constraint). Violation → RED if HARD, YELLOW if SOFT.

## For Discussion

1. Should the soft score also show a continuous risk score (0.72) alongside the YELLOW binary, or is the binary YELLOW sufficient for the demo?

2. The 0%/preset% defaults are different for hard vs soft. Should a user be able to set a soft constraint with a stricter threshold than the hard default, or should the hard threshold always be at or beyond the soft threshold?

3. How should hard violations interact with Midas signal generation? If a hard constraint is violated, should Midas automatically generate a rebalancing signal, or does the user make that decision manually?
