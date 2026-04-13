# Midas — Critical Decision Points

Phase: 01-analysis / 03-user-flows
Author: uiux-designer
Date: 2026-04-09

This document covers the moments where Alex must make a high-stakes decision fast — and where getting the layout wrong kills either the decision or the trust. From the brief: "modern UX for rapid decision-to-execution". These decisions happen on mobile in the majority of cases (in-between meetings, in transit, at a coffee break), so **mobile above-the-fold is the governing constraint**.

Five critical decisions covered:

1. Approve a single rebalance proposal
2. Approve a bulk set of trades after a regime flip
3. Force-override auto-trading back on during a turbulent regime
4. Override the cost-model soft block on a net-negative trade
5. Modify a proposal (reduce size, exclude instruments)

For each: the above-fold layout, the CTA hierarchy, the escape hatches, the logging and audit requirements.

---

## Governing principles

1. **Above-fold on mobile is the budget.** iPhone 15 standard viewport ~390×844pt, minus status bar and home indicator, leaves ~760pt usable. Everything the user needs to say yes or no must fit in that. Anything that doesn't fit is behind a tap.
2. **Primary CTA is thumb-reachable, large, and high-contrast.** 56pt minimum tap height, bottom quarter of the screen, full-width or near-full-width.
3. **Secondary CTAs (Debate, Modify) are outlined, not filled.** Visually subordinate without being hidden.
4. **Tertiary CTAs (Reject, Override) are text-only, small, and deliberately unglamorous.** These are paths Alex should take only when they mean it.
5. **Biometric is the commit gate, not a separate screen.** Biometric overlays the approval button on press. The 200ms of friction is the product.
6. **Every decision is logged with full context.** Approval source, biometric method, signal snapshot hash, backtest reference, debate reference (if any). This is the compliance spine and the trust affordance simultaneously.
7. **Escape hatch is always visible.** "Debate this" is never more than one tap away on any decision screen. The user should never feel cornered.
8. **No time pressure.** No countdown timers, no "expires in 5 minutes" urgency. Proposals expire at the next rebalance window, and Midas says so plainly, without counting down.

---

## Decision 1 — Approve a single rebalance proposal

**Context**: Flow 3 single-trade or 2–3-trade proposal in a calm regime. The most frequent high-stakes decision Alex will make.

### Mobile above-fold layout

```
+-------------------------------+  <- top of viewport
|  Rebalance proposal           |
|  Fri 2026-04-09  08:32 ET     |
+-------------------------------+
|                               |
|  3 trades                     |  <- lead: count + cost
|  Net cost ~$34  (2.7 bp)      |
|  Turnover 14%  (cap 20%)      |
|                               |
|  What changes (sleeve view)   |  <- delta, not detail
|   Equities ETF  42% -> 38%    |
|   Gov bonds     18% -> 22%    |
|   Precious met  12% -> 12%    |
|                               |
|  Expected improvement         |  <- outcome, not pitch
|   +0.3% / yr risk-adjusted    |
|   Drawdown risk: -1.1%        |
|                               |
|  Why (3 bullets max)          |
|   Calm-trend weekly tilt      |
|   Gold momentum crossed       |
|   Bond carry improved         |
|   [ see signals ]             |
|                               |
|  [ Debate ]   [ Modify ]      |  <- secondary
|                               |
|  +-------------------------+  |
|  |        APPROVE          |  |  <- primary, 56pt,
|  +-------------------------+  |     thumb-reachable
|                               |
|  Reject                       |  <- tertiary, text-only
+-------------------------------+  <- fold
```

### CTA hierarchy

| Level | Label | Style | Action |
|---|---|---|---|
| Primary | APPROVE | Filled, gold, full-width, 56pt, biometric overlay on press | Executes all trades on biometric success |
| Secondary | Debate | Outlined, half-width | Opens Flow 5 with proposal context pre-loaded |
| Secondary | Modify | Outlined, half-width | Expands to per-trade list with checkboxes |
| Tertiary | Reject | Text-only, small | Rejects with optional reason; confirmation modal |

### Escape hatches

- Tap "see signals" → signal snapshot tile (same as Debate grounding tile) without leaving the approval screen. Grounding without commitment.
- Tap "Debate" → full Flow 5 with context. Can return with a decision or without.
- Tap sleeve name in the "What changes" block → Portfolio Detail for that sleeve.
- Tap notification out of habit → always lands on this screen; never on a partially committed state.

### Logging

On approval: timestamp, biometric method (Face ID / Touch ID / passkey), proposal ID, allocator version, signal snapshot hash, cost estimate, user's current device, IP country.

On rejection: same minus biometric, plus optional reason text.

On debate: debate session ID linked to the proposal. If Alex returns from debate and approves, the debate ID is attached to the approval record.

### Success target

P50 time-to-decision < 60 seconds. P90 < 3 minutes. If P90 drifts above 5 minutes, the information hierarchy is wrong; revisit.

---

## Decision 2 — Bulk approve after a regime flip

**Context**: Flow 4 / Flow 3 variant. A regime flip produced 3–8 correlated defensive trades. Forcing Alex to approve each one individually is user-hostile and creates approval fatigue. But pre-checking everything "for convenience" is also wrong — it trains Alex to mass-approve without reading.

### Design choice

**Checkboxes default to OFF.** Alex must actively select what to approve. Bulk approve applies only to checked items. This is slower by 3–5 seconds per decision but preserves intent.

### Mobile layout

```
+-------------------------------+
|  Regime flip: HIGH VOL        |
|  4 defensive trades proposed  |
|  Net cost ~$58  (4.3 bp)      |
+-------------------------------+
|                               |
|  Grouped by rationale:        |
|                               |
|  ---- De-risk equities -----  |
|  [ ] SELL 250 SPY             |
|      BUY 820 GLD              |
|      ~$128,100   cost $16     |
|      [ why ] [ debate ]       |
|                               |
|  [ ] SELL 100 QQQ             |
|      BUY 310 IEF              |
|      ~$58,400    cost $12     |
|      [ why ] [ debate ]       |
|                               |
|  ---- Reduce EM exposure ---  |
|  [ ] SELL 50 EEM              |
|      BUY 180 SHY              |
|      ~$22,300    cost $8      |
|      [ why ] [ debate ]       |
|                               |
|  ---- Trim energy ----------  |
|  [ ] TRIM 30 XLE              |
|      ~$6,700     cost $4      |
|      [ why ] [ debate ]       |
|                               |
|  [ Check all ]  [ Uncheck all]|
|                               |
|  Selected: 0 of 4             |
|  [        APPROVE 0         ] |  <- disabled until >=1 checked
|                               |
|  Reject all                   |
+-------------------------------+
```

### Interaction rules

1. **Checkboxes start unchecked.** No pre-selection. "Check all" is available but is a deliberate action, not a default.
2. **Button label updates live** with the selected count: "APPROVE 0" (disabled), "APPROVE 3", "APPROVE 4".
3. **Tapping the row (not the checkbox) expands detail** — delta, cost breakdown, which signals contributed to this specific trade. This is the "I want to read it carefully" affordance.
4. **"Why" per item** opens an inline grounding tile without leaving the list.
5. **"Debate" per item** opens Flow 5 with just that single trade's context. On return, the checkbox state is preserved.
6. **Cost total updates live** as items are checked/unchecked, including expected turnover impact against the cap.
7. **One biometric covers the whole batch.** After tapping APPROVE N, a single biometric confirms all selected items. Partial failures during execution are surfaced per-item on the confirmation screen.

### Second escape hatch: "Trust this whole rebalance"

For the rare case where Alex fully trusts the system's read on the regime and wants to approve wholesale without per-item review:

```
  [  Trust this whole rebalance  ]  <- small link, below the main list
```

Tapping this:
1. Checks all items
2. Shows a confirmation screen: "You're approving 4 trades without per-item review. This is logged as a wholesale approval. Continue?"
3. Requires a **second biometric** (on top of the approval biometric) — two-factor because the friction should match the commitment.
4. Logs the wholesale approval distinctly in the audit trail.

This exists because forcing a senior professional to tap 8 checkboxes when they already trust the call is disrespectful of their time. But the wholesale path is not the default, and it is instrumented.

### CTA hierarchy

| Level | Label | Style | Action |
|---|---|---|---|
| Primary | APPROVE N | Filled gold, full-width, disabled when N=0 | Executes all checked items on biometric |
| Secondary | Check all / Uncheck all | Outlined, small | Toggles all checkboxes |
| Secondary | Debate | Per-item, outlined | Opens single-trade debate |
| Tertiary | Reject all | Text-only, small | Rejects the entire proposal; confirmation modal |
| Tertiary | Trust this whole rebalance | Text link, small | Two-biometric wholesale path |

### Escape hatches

- Every item has its own Debate link. Alex can debate one, return, approve the batch.
- "See regime explanation" at the top returns to the regime context screen from Flow 4.
- Closing the app does not discard the checkbox state — it persists until the proposal expires.

### Logging

- Per-item approval state (approved, not approved, debated, rejected)
- Batch approval timestamp + biometric method
- Wholesale path flag (true/false)
- Regime state at time of approval (snapshot hash)
- Any per-item debates linked

### Success target

P50 time-to-decision for a 4-trade bulk < 3 minutes. P90 < 8 minutes.

---

## Decision 3 — Force-override auto-trading during a turbulent regime

**Context**: Flow 4. Midas has paused auto-trading because the regime detector fired. Alex disagrees with the regime call and wants to force auto-trading back on. This is an unusual, high-consequence action — the UX should respect the decision but not make it trivial.

### Layout

```
+-------------------------------+
|  Force auto-trading on?       |
+-------------------------------+
|                               |
|  Midas paused auto-trading    |
|  because 3 signals fired:     |
|                               |
|   Realized vol 20d = 18.4     |
|     (threshold 18.0)          |
|   HY OAS +42bp in 5d          |
|     (threshold +30)           |
|   Stock/bond corr = +0.22     |
|                               |
|  Your brief says:             |
|   "Pause in turbulent markets |
|    and ask permission."       |
|                               |
|  If you force auto-trading    |
|  back on:                     |
|   - Midas will place trades   |
|     without asking, under     |
|     your existing thresholds  |
|   - The override expires      |
|     tonight at close          |
|   - Tomorrow it will pause    |
|     again if signals are      |
|     still firing              |
|   - This is logged in your    |
|     trade audit               |
|                               |
|  Why are you overriding?      |
|  [ __________________ ]       |  <- required text field,
|                               |     minimum 10 chars
|                               |
|  [ Cancel ]                   |
|  [ Force on (biometric) ]     |  <- tertiary style, not primary
+-------------------------------+
```

### Design rules

1. **No primary CTA on this screen.** Both buttons are secondary style. This is deliberate — nothing on this screen should look like a happy-path action.
2. **Required reason field.** Minimum 10 characters. The system does not classify or act on the reason (per `rules/agent-reasoning.md` — the LLM reads it if Alex revisits it in debate, but the decision path doesn't parse it). The reason is for the audit trail and for Alex's own future self.
3. **Second biometric required.** Distinct from the trade-approval biometric, and clearly labelled as "confirming an override of your own stated risk policy".
4. **Time-limited.** Override expires at end of trading day (user-local). Must be re-confirmed daily. This is the only place in the product with an automatic expiry.
5. **Prominent in the audit trail.** Every trade placed under an override is flagged in the Trade Log with a distinct icon and a link back to the override record and stated reason.
6. **No "don't ask again" option.** Every override is a fresh, deliberate action. Alex cannot disable the friction.

### Escape hatches

- Cancel → returns to the regime explanation screen. Auto-trading remains paused.
- Tap any signal in the "why Midas paused" list → opens debate on that signal. Alex can argue the regime call in debate before deciding whether to override.

### Success target

Override rate in production < 5% of regime flips. If it climbs above that, either the regime detector is producing false positives or the explanation UX is inadequate — either way, it's a bug.

---

## Decision 4 — Override the cost-model soft block

**Context**: Alex (or Midas) is about to place a trade where the cost model says the expected improvement is smaller than the expected cost — a net-negative trade. Midas soft-blocks this by default. Alex can override, but must acknowledge what they're doing.

### Layout

```
+-------------------------------+
|  This trade costs more        |
|  than it's worth.             |
+-------------------------------+
|                               |
|  Trade:                       |
|   SELL 40 IEF                 |
|   BUY 20 TLT                  |
|   ~$6,200                     |
|                               |
|  Expected cost:    $11        |
|  Expected benefit: $4         |
|  Net:             -$7         |
|                               |
|  Why Midas thinks this is     |
|  not worth it:                |
|   Duration tilt is small      |
|   Commission + spread eat     |
|   the expected gain           |
|                               |
|  If you still want to do it:  |
|  [ Override and place trade ] |
|  [ Cancel ]                   |
+-------------------------------+
```

### Rules

1. **Soft block, not hard block.** Alex is the executor; we don't forbid actions, we explain the cost. Per A2, v1 is signal-only and the user is the decision-maker.
2. **Plain-language cost explanation.** No "expected utility" or "information ratio" — this is "cost more than it's worth" in dollars.
3. **Override still requires biometric.** Same strength as a normal approval; the friction comes from the honest framing, not from extra gates.
4. **Logged distinctly.** Cost-model overrides have their own flag in the Trade Log.
5. **No "disable cost-model warnings".** This is not a togglable annoyance; it's a fundamental honesty layer.

### Escape hatches

- Cancel → returns to Portfolio Detail or proposal screen.
- "Why does Midas think this?" (text link below the cost block) → opens Debate with the cost model output pre-loaded.

---

## Decision 5 — Modify a proposal

**Context**: Alex generally agrees with a rebalance but wants to reduce the size of one trade, or exclude one instrument entirely.

### Layout (mobile, after tapping "Modify" on Decision 1)

```
+-------------------------------+
|  Modify proposal              |
|  Starting: 3 trades, $34      |
+-------------------------------+
|                               |
|  [x] SELL 250 SPY / BUY 820 GLD
|      Size: [===========] 100%  <- slider
|      $128,100                 |
|                               |
|  [x] SELL 100 QQQ / BUY 310 IEF
|      Size: [======-----] 60%   <- Alex reduced
|      $35,040                  |
|                               |
|  [ ] SELL 50 EEM / BUY 180 SHY <- Alex unchecked
|      Size: [===========] 100%  <- greyed
|      $22,300                  |
|                               |
|  Updated plan:                |
|   2 trades                    |
|   Net cost ~$22 (was $34)     |
|   Turnover 9% (was 14%)       |
|   Expected improvement:       |
|     +0.2% / yr (was +0.3%)    |
|                               |
|  Warning:                     |
|   Your modified plan leaves   |
|   equities at 40% (your cap   |
|   is 35%). You can override.  |
|                               |
|  [ Debate the change ]        |
|  [        APPROVE 2         ] |
|                               |
|  [ Cancel changes ]           |
+-------------------------------+
```

### Rules

1. **Slider for size, checkbox for inclusion.** Discrete enough to be clear, continuous enough to be useful.
2. **Live re-estimation.** Cost, turnover, expected improvement all update as Alex drags the slider or toggles checkboxes. This is the feedback loop that makes modification trustworthy.
3. **Soft blocks for cap violations.** If Alex's modifications violate a sleeve cap or concentration limit, show a warning with an override path. Do not hard-block — the user is the executor.
4. **"Debate the change"** passes the modified plan (not the original) to Debate. The LLM sees the user's proposed changes as context.
5. **Cancel returns to the original proposal**, not to the home screen. No accidental loss of state.

### CTA hierarchy

| Level | Label | Style |
|---|---|---|
| Primary | APPROVE N | Filled gold, live-updating count |
| Secondary | Debate the change | Outlined |
| Tertiary | Cancel changes | Text link |

### Escape hatches

- Every trade row has its own tap-to-expand detail and "why" tile.
- Sleeve cap warnings are explanatory, not blocking.
- Leaving the screen preserves modifications as a draft until the proposal expires.

---

## Cross-decision invariants

1. **Biometric on every commit. No exceptions.** Face ID / Touch ID / passkey on mobile; WebAuthn on web.
2. **Primary CTA bottom-of-screen, thumb-reachable, 56pt minimum, full-width or near-full-width.**
3. **Debate is always one tap away.** The user should never feel cornered into a yes/no.
4. **No time pressure.** No countdown timers. Proposals expire on the next rebalance window, stated plainly.
5. **No dark patterns.** No pre-checked bulk approvals. No "are you sure you want to cancel?" nag modals. No hidden reject paths.
6. **Every decision is logged with full context** — approval source, biometric method, signal snapshot hash, allocator version, device, IP country, linked debate ID (if any), linked override flags (if any).
7. **Every secondary and tertiary action can be reached with thumb-stretch.** Primary is always in the bottom quarter; secondary is above it; tertiary is text-only and in the bottom margin.
8. **Web parity**: desktop layouts use the same information hierarchy but take advantage of horizontal space — side-by-side before/after sleeve charts, always-visible cost detail, larger grounding tiles. The mobile card is the canonical form; the desktop version is a relaxation of it, not a different design.
