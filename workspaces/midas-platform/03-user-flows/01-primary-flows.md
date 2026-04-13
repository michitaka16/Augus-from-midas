# Midas — Primary User Flows

Phase: 01-analysis / 03-user-flows
Author: uiux-designer
Date: 2026-04-09

Six primary flows. Each has: trigger, steps, decision points, error/alt states, success criteria. Mobile-first; web parity called out where behaviour differs.

Core design stance (from the brief and from `05-uiux-design.md`): **95% of days nothing happens — the product must make "nothing happens" feel competent, not broken.** The dominant state is quiet. Attention is a rare, earned resource, and when it is spent, it must convert to a decision in under 90 seconds.

Plain-language UI copy is used throughout per `rules/communication.md`. All LLM behaviour in Flow 5 follows `rules/agent-reasoning.md` — no hardcoded intent routing, no keyword matching, the LLM does all classification.

---

## Flow 1 — First-run onboarding

**Trigger**: User downloads app / visits web app for the first time.

**Goal**: Reach a trusted signal-only state running against a paper IBKR account, with a realistic backtest the user has seen and approved of, in under 10 minutes.

### Steps

```
Step 1  Value screen (single screen, one CTA)
Step 2  Risk profile (three questions, not twenty)
Step 3  Capital tier selection
Step 4  IBKR connect (paper-first, OAuth preferred)
Step 5  Watchlist seed (sleeve-level, not ticker-level)
Step 6  Approval threshold
Step 7  Initial backtest preview (the proof moment)
Step 8  Biometric setup + signal-only disclosure
Step 9  Land on Dashboard in quiet state
```

### Step detail

**Step 1 — Value screen.** One line: "Delegate your portfolio. Debate every decision." One number: the headline backtest return net of costs, dated. One CTA: "Start with paper money."

```
+-----------------------------+
|            [ M ]            |
|                             |
|  Delegate your portfolio.   |
|  Debate every decision.     |
|                             |
|  +14.2% / year              |
|  net of costs, 2000-2025    |
|  [ see the backtest ]       |
|                             |
|  [ Start with paper money ] |
|                             |
|  Already have an account?   |
+-----------------------------+
```

Decision point: "see the backtest" opens a read-only Backtest Explorer preview before the user signs up. This is deliberate — the proof happens before the paywall.

**Step 2 — Risk profile.** Three questions, plain language, each with an outcome statement (per `rules/communication.md`):

1. "How would you feel if your portfolio dropped 20% in a month?"
   - "I'd buy more" / "I'd hold" / "I'd want out"
2. "When markets get weird, should I pause trading and ask you first?"
   - "Yes, always pause" / "Pause only on big moves" (default) / "Keep trading unless I say stop"
3. "How much of your portfolio can sit in any one sleeve?"
   - Slider: 20% / 35% (default) / 50%

The answers derive: max drawdown tolerance, turbulent-regime behaviour (A3 default = "pause on big moves"), concentration caps. Show the derived values on the next screen so the user can see what they set.

**Step 3 — Capital tier.** Three presets plus a custom range, mapped to IBKR Pro commission tier (A1 default: $50k–$1M). Informs min-trade sizing and cost model.

**Step 4 — IBKR connect.** OAuth is the preferred path. If OAuth unavailable, fall back to read-only API key with explicit disclosure. **Paper mode is the default for the first 14 days, non-negotiable in the UI.** Copy:

> Midas will watch your portfolio and recommend trades. For the first 14 days we use paper money so you can see what Midas would do before any real trades happen. IBKR holds your funds — Midas never does.

Decision point: "Skip paper mode" is hidden behind a secondary link with a stronger disclosure. Default path is paper-first.

Error states:
- IBKR OAuth redirect fails → show plain-language error ("Interactive Brokers didn't answer. Try again, or use the read-only key path."), offer retry and fallback.
- API key invalid → one line: "That key didn't work. Check it was copied without extra spaces."
- User skips → allowed; lands in Observer tier with delayed signals against a synthetic portfolio.

**Step 5 — Watchlist seed.** Sleeve-level, not ticker-level. Checkboxes for: Broad equities, Government bonds, Corporate bonds, Precious metals, REITs, Commodities, Dividend funds, Emerging markets. All checked by default. The user's sleeve caps from Step 2 apply. No ticker picking — this is deliberate; Midas owns instrument selection.

**Step 6 — Approval threshold.** One slider with three labels:

```
Ask me before every trade    |    Ask me for trades over $X    |    Let Midas handle small rebalances
[----------|----------------------------------------|---------]
                                     $ 5,000 (default)
```

Default: ask above $5,000 or >2% of NAV, whichever is smaller. This is the single knob that governs the attention budget.

**Step 7 — Initial backtest preview.** The proof moment. A multi-horizon grid showing what this user's exact configuration would have returned across 1y/3y/5y/10y rolling windows and four regime buckets (calm bull, calm bear, high vol, crisis). Each cell: mean return, p25/p75, max drawdown, cost drag. Tappable for detail.

This screen is desktop-primary. On mobile it collapses to a summary card ("In a crisis regime, this setup would have drawn down 12% and recovered in 7 months") with a "see full backtest on web" link.

Decision point: "This isn't aggressive enough / too aggressive." → "Adjust risk profile" sends user back to Step 2 with the current answers preserved. Expect ~30% of users to round-trip here at least once; this is a feature.

**Step 8 — Biometric setup + disclosure.** Face ID / Touch ID / passkey enrolment. Non-skippable. Followed by the v1 signal-only disclosure (per A2):

> Midas recommends. You approve. Interactive Brokers executes. Midas is not a registered investment advisor and does not provide personalised advice. You remain the decision-maker on every trade.

Checkbox + continue. Logged with timestamp for audit.

**Step 9 — Dashboard.** Lands in the quiet state (Flow 2). If no regime events are active and no rebalance is pending, the first thing the user sees is "No trades planned. Next rebalance check: [next Friday] 08:30 ET." This is intentional — the first real impression is calm.

### Success criteria

- User reaches Dashboard with a linked paper IBKR account and a visible backtest.
- Time-to-dashboard < 10 minutes for the happy path.
- At least one sleeve cap, one approval threshold, and one biometric enrolled.
- Signal-only disclosure accepted and logged.

### Failure modes to design against

- User bounces at IBKR OAuth — we lose them to a third-party UI we don't control. Mitigation: clear "what's about to happen" pre-screen, explicit "you'll come back here" copy, return-URL handling.
- User skips the backtest preview — they never see the proof. Mitigation: make Step 7 non-skippable on first run.
- User sets approval threshold to "every trade" and immediately hates it — notification fatigue kills trust. Mitigation: explain the trade-off in plain language on the slider ("every trade means ~2-4 pings per month in calm markets, ~20+ in turbulent ones").

---

## Flow 2 — Daily quiet state (the dominant flow)

**Trigger**: User opens app on a typical day. No regime event, no pending approval, no rebalance due.

**Goal**: Confirm in under 15 seconds that nothing needs attention, and leave feeling the product is awake and working. The failure mode is an empty dashboard that feels broken or abandoned.

### Steps

```
Step 1  Open app → Dashboard
Step 2  Glance: portfolio value, regime chip, "nothing to do"
Step 3  Optional: ask Midas a question, or close app
```

### Mobile layout (above the fold)

```
+-----------------------------+
|  Midas                 [M]  |
+-----------------------------+
|                             |
|  $1,284,430                 |
|  +2.1% this month           |
|  +3.2% vs 60/40 YTD         |
|                             |
|  [ Calm trend ]             |
|  Last checked: 14:02 ET     |
|  Next review: Fri 08:30 ET  |
|                             |
|  Nothing to approve today.  |
|  Midas will let you know    |
|  when something changes.    |
|                             |
|  [ Ask Midas anything ]     |
|                             |
+-----------------------------+
|  Home  Portfolio  Debate  > |
+-----------------------------+
```

### Design rules for the quiet state

1. **The biggest number is portfolio value.** Not the regime, not a chart, not a CTA.
2. **The regime chip is the second-most prominent element.** It is the single best predictor of whether Alex needs to engage. Colour-coded: calm = muted green, alert = amber, turbulent = red.
3. **"Last checked" and "Next review" are always visible.** This is the single most important anti-anxiety affordance: it proves Midas is awake without forcing the user to ask.
4. **The empty state reads as a statement, not an absence.** "Nothing to approve today. Midas will let you know when something changes." This is a promise being kept, not a blank screen.
5. **No chart on the home screen on mobile.** Force navigation to Portfolio Detail for any chart. This is anti-Robinhood: we actively discourage intraday checking.
6. **"Ask Midas anything" is always one tap away.** The debate entry point is persistent.
7. **No dopamine loops.** No streaks, no badges, no "you're up today!" celebrations. Alex will delete the app.

### Decision points

- Tap portfolio value → Portfolio Detail with sleeve breakdown.
- Tap regime chip → Regime explanation modal: which signals are firing, what thresholds matter, when was last flip.
- Tap "Next review" → plain-language explanation ("Midas checks for rebalance opportunities once a week on Fridays at 08:30 ET. You'll get a notification if anything needs your approval.").
- Tap "Ask Midas anything" → Flow 5 (Debate) with empty context.

### Web parity

Desktop dashboard shows the same five elements plus a collapsed (default) sleeve breakdown and a collapsed (default) equity curve. No auto-refresh. No ticker tape. No news feed on the home screen.

### Success criteria

- User opens app, spends 5–15 seconds, closes app or taps into one specific thing.
- Zero notifications delivered on a day with no regime event and no pending approval.
- User subjectively reports: "it felt calm, I knew it was working, I didn't need to do anything."

### Failure modes

- Dashboard feels empty → user distrusts it → opens app more, not less. Mitigation: the "Last checked" timestamp is the single most important element of the quiet state.
- User wants a chart, forces one onto home → engagement loop creeps in. Mitigation: hold the line. Charts are one tap away, not zero taps away.

---

## Flow 3 — Rebalance proposal (the weekly moment)

**Trigger**: Scheduled weekly rebalance check (Friday 08:30 ET by default) fires and the allocator produces one or more trade proposals that exceed the user's approval threshold. Push notification delivered to mobile; email fallback on web.

**Goal**: Convert the notification to an approve/modify/reject/debate decision in under 90 seconds, with the user feeling they understood what they approved.

### Steps

```
Step 1  Push notification
Step 2  Tap → one-screen proposal summary (above-fold on mobile)
Step 3  Decision:
          - Approve (biometric) → execution → confirmation
          - Debate → Flow 5 → return with context → decision
          - Modify → adjust sizes or exclude items → re-estimate cost → decision
          - Reject → logged with optional reason → confirmation
Step 4  Execution (paper or live)
Step 5  Confirmation screen with receipts
```

### Notification

Plain language, outcome-first:

> Midas wants to rebalance your portfolio. 3 trades, estimated cost $34. Tap to review.

Non-engagement tone: never "your portfolio is up", never an exclamation mark, never a number that tries to provoke.

### One-screen proposal summary (mobile, above-fold)

```
+-------------------------------+
|  Rebalance proposal           |
|  2026-04-09  08:32 ET         |
+-------------------------------+
|                               |
|  3 trades                     |
|  Net cost: ~$34  (2.7 bp)     |
|  Turnover: 14%  (cap 20%)     |
|                               |
|  What changes:                |
|   Equities ETF   42% -> 38%   |
|   Gov bonds      18% -> 22%   |
|   Precious met   12% -> 12%   |
|                               |
|  Expected improvement:        |
|   +0.3% / yr risk-adjusted    |
|   Drawdown risk: -1.1%        |
|                               |
|  Why: calm-trend weekly tilt  |
|   [ see signals ]             |
|                               |
|  [ Debate ]  [ Modify ]       |
|                               |
|  [      A P P R O V E      ]  |
|                               |
|  [ Reject ]                   |
+-------------------------------+
```

### Information hierarchy rules

1. **Count of trades and net cost lead.** This is the first thing Alex wants to know: "how much am I about to spend, on how many things."
2. **Delta (before → after) before detail.** Show allocation change at sleeve level first. Ticker-level detail is one tap away.
3. **Expected improvement is stated, not sold.** "+0.3% risk-adjusted" with a drawdown-risk delta, no hype.
4. **"Why" is three bullets maximum.** Full reasoning is behind "see signals" and "Debate".
5. **Approve is the primary CTA, large, bottom-of-screen, thumb-reachable.** Debate and Modify are secondary. Reject is tertiary, small, text-only.
6. **No price charts on the approval card.** Charts are for analysis, not decisions. Decision fatigue is the enemy.

### Decision points

- **Approve** → biometric prompt (Face ID / Touch ID / passkey). On success → execution. Biometric is non-bypassable. This is the regulatory hedge and the trust affordance simultaneously.
- **Debate** → Flow 5 with full proposal context pre-loaded. On return, if the user made an override decision in debate, that override is reflected here before final approve.
- **Modify** → expand trade list with per-trade opt-out checkboxes (Flow 4 bulk-approve pattern). Cost re-estimates live. If the user's modifications violate a sleeve cap, show a soft block: "This leaves equities at 48%, over your 35% cap. Override?"
- **Reject** → optional one-line reason input (not required, logged if provided). Confirmation: "Rejected. Midas won't propose this again for 7 days unless signals change materially."

### Execution and confirmation

After biometric approval, trades are sent to IBKR. For paper mode, the paper API is used; the UI is identical. Copy is identical. This is intentional — paper mode should feel like live mode minus the money.

Execution screen shows a live status list:

```
  SELL 250 SPY   filled @ $512.38  ✓
  BUY  820 GLD   filled @ $156.22  ✓
  SELL 100 QQQ   pending...
```

Errors during execution (partial fill, IBKR rejection) are surfaced immediately with plain-language explanation and a "what now?" recommendation. Never silent failure. See `03-empty-and-error-states.md` for the full error matrix.

Final confirmation screen:

```
  Done.
  3 trades executed in 4 seconds.
  Actual cost: $31.40 (estimated $34).
  New allocation: [ sleeve chart ]
  [ See trade log ]   [ Back to home ]
```

### Success criteria

- P50 time from notification to decision < 90 seconds.
- P90 < 3 minutes.
- Approval completion rate on initial proposal > 80% (the rest go to debate, modify, or reject).
- Actual execution cost within ±20% of estimate (cost model quality gate).

### Failure modes

- User taps notification, sees proposal, is confused, closes app → lost trust. Mitigation: the "Why" bullets and one-tap "Debate" escape hatch.
- Biometric fails repeatedly → user locked out of their own trade. Mitigation: passkey fallback, then password + SMS.
- IBKR partial fill leaves portfolio in an intermediate state → user anxiety. Mitigation: explicit "pending" state, automatic retry, clear "what Midas will do next" copy.

---

## Flow 4 — Turbulent regime trigger

**Trigger**: The regime detector (A3 ensemble: VIX, VIX term structure, realized vol, cross-asset correlation, credit spreads, yield curve, drawdown) flips from CALM or CALM_TREND to HIGH_VOL or CRISIS. Auto-trading is frozen per the A3 action contract. Push notification is sent immediately, not batched to the weekly window.

**Goal**: Alex understands within 30 seconds: (a) that auto-trading is paused, (b) why, (c) what Midas recommends doing about it, (d) what their options are. Everything else waits.

### Steps

```
Step 1  Regime detector fires (backend event)
Step 2  Push notification + persistent app banner + email
Step 3  User opens app → regime explanation screen
Step 4  Decision:
          - Review Midas's recommended defensive trades
          - Debate the regime call itself
          - Do nothing (trading stays frozen until regime clears or user overrides)
          - Override: force auto-trading back on (requires second biometric + explicit disclosure)
Step 5  If reviewing trades → Flow 3 per-trade, but with bulk-approve grouping
Step 6  Ongoing banner remains until regime clears
```

### Notification

```
  Midas paused auto-trading.
  Markets turned turbulent this morning.
  Tap to see why and review 4 defensive trades.
```

Tone is matter-of-fact, not alarming. No exclamation marks, no "URGENT". Alex is a senior professional, not a day-trader; we respect their attention.

### Regime explanation screen

This is the screen most likely to determine whether Alex trusts the product long-term. It must be comprehensible to a smart non-quant, complete enough for a quant, and honest about uncertainty.

```
+---------------------------------+
|  Auto-trading is paused         |
|  Regime: HIGH VOL               |
|  Since: 2026-04-09 06:14 ET     |
+---------------------------------+
|                                 |
|  Why Midas paused:              |
|                                 |
|   Realized vol (20d): 18.4      |
|     (threshold 18.0)            |
|   Credit spreads widened:       |
|     HY OAS +42 bp over 5 days   |
|     (threshold +30 bp)          |
|   Stocks and bonds moved        |
|     together: correlation       |
|     flipped to +0.22            |
|                                 |
|  What this means:               |
|   Midas will not place any      |
|   trades without your OK until  |
|   at least 2 of these 3 signals |
|   clear.                        |
|                                 |
|  What Midas recommends now:     |
|   Shift 8% from equities to     |
|   gold and short bonds.         |
|   4 trades. Est. cost $58.      |
|                                 |
|  [ Review 4 trades ]            |
|  [ Debate the regime call ]     |
|  [ Do nothing for now ]         |
|                                 |
|  Advanced: [ Force auto-on ]    |
|                                 |
+---------------------------------+
```

### Decision points

- **Review 4 trades** → Flow 3 variant with bulk-approve grouping. Trades are grouped by rationale ("defensive tilt", "de-risk equities") with checkboxes per-trade. Biometric still required. See `02-critical-decisions.md` for bulk-approve interaction detail.
- **Debate the regime call** → Flow 5 with pre-loaded context: the three signals that fired, the threshold each crossed, the regime detector's full signal table, and a "what would you have to believe for Midas to be wrong?" scaffold.
- **Do nothing** → allowed. Portfolio holds. Trading remains frozen. Banner persists. User can return any time. This is the default path for a user who sees the explanation and agrees to wait.
- **Force auto-on (override)** → explicit second biometric + disclosure: "You're asking Midas to keep trading in a turbulent regime. Your brief says to pause in turbulent markets. Are you sure?" Logged to audit. Override expires at end of trading day; must be re-confirmed daily.

### Persistent banner

Until the regime clears, every screen shows a thin amber banner at the top:

```
  Auto-trading paused — HIGH VOL regime since 09:14     [ details ]
```

Tapping → returns to the regime explanation screen. The banner disappears automatically when at least 2 of the 3 triggering signals clear for 24 consecutive hours. Clearing is also notified, but as a low-priority message ("Midas resumed auto-trading. Markets calmed.").

### Ambiguous-regime state

If the detector is uncertain (signals are borderline, ensemble is split), Midas MUST pause and say so explicitly. See `03-empty-and-error-states.md` for the "I'm not sure — pause?" state. This is a first-class design state, not an error.

### Success criteria

- P50 notification-to-explanation-screen < 30 seconds (with push).
- Banner visibility 100% of the time while regime is active.
- Zero silent auto-trades while in HIGH_VOL or CRISIS regime (hard invariant).
- Debate open rate from turbulent-regime notifications > 40% (this is where the "debate with AI" USP earns its place).

### Failure modes

- User taps notification, sees technical jargon, closes app → lost. Mitigation: plain-language "What this means" bullet is mandatory.
- User forces override, trades badly, blames Midas → trust loss. Mitigation: override is logged, disclosure is explicit, override is time-limited and must be renewed. Audit trail is reviewable in Trade Log.
- Regime flips back and forth rapidly (flapping) → notification fatigue. Mitigation: debounce at detector level (24h minimum regime dwell time), not at UI level.

---

## Flow 5 — Debate with AI

**Trigger**: User taps "Debate" on a proposal, a regime alert, a sleeve in Portfolio Detail, a historical trade in the Trade Log, or the persistent "Ask Midas anything" entry point on the Dashboard.

**Goal**: The user gets an answer they trust, grounded in specific signals, backtests, and cost calculations — or an explicit "I don't know, here's what it would take to find out." No hallucinated numbers, ever. No sycophantic capitulation.

**Critical rule**: All debate behaviour — including intent understanding, topic classification, when to run a backtest, when to surface a counter-scenario, when to decline — is **done by the LLM through reasoning, not by hardcoded code paths**. Per `rules/agent-reasoning.md`: no `if "backtest" in message`, no regex extraction of tickers, no dispatch tables. The LLM sees the raw message plus structured context and decides everything. Tools (fetch_signal, run_backtest, fetch_cost_model, fetch_trade_history) are dumb data endpoints.

### Context handoff

When Debate opens, it is pre-loaded with a structured context bundle that depends on entry point:

| Entry point | Pre-loaded context |
|---|---|
| From rebalance proposal | Full proposal object: instruments, sizes, cost estimate, portfolio impact, allocator version, signal snapshot, backtest reference |
| From regime alert | Current regime state, signal values + thresholds, regime history (prior 90 days), detector ensemble output |
| From sleeve in Portfolio Detail | Sleeve name, current weight, target weight, drift, holdings list, rationale chips |
| From historical trade in Trade Log | Full trade record, allocator version at time of trade, signal snapshot hash, approval source, any prior debate on this trade |
| From "Ask Midas anything" (Dashboard) | Empty — user drives the topic |

This context is passed to the LLM as structured grounding data, **not** as pre-classified intent. The LLM decides what matters.

### Steps

```
Step 1  User taps Debate → chat opens with context visible at top
Step 2  User types question (or taps a suggested opener)
Step 3  LLM reasons → may call tools (signals, backtest, cost model)
Step 4  LLM response rendered with grounding tiles (signal / backtest / cost)
Step 5  User follows up, challenges, or asks for counter-scenario
Step 6  Exchange continues until user is satisfied
Step 7  User returns to originating screen → decision
Step 8  Debate is persisted and resumable
```

### Layout

```
+---------------------------------+
|  Debate: Rebalance 2026-04-09   |
|  [ context: 3 trades, $34 est ] |
+---------------------------------+
|                                 |
|  Try asking:                    |
|   "Why now and not next week?"  |
|   "What if I hold SPY instead?" |
|   "Show me the backtest."       |
|                                 |
|  YOU                            |
|  Why gold? Real yields rising.  |
|                                 |
|  MIDAS   [ confidence: MEDIUM ] |
|  I'm tilting to gold because    |
|  three signals crossed their    |
|  thresholds at the same time —  |
|  not because I'm betting on     |
|  real yields.                   |
|                                 |
|  +-- Grounding -----------+     |
|  | SIGNAL realized_vol_20 |     |
|  |  = 18.4 (thresh 18.0)  |     |
|  | SIGNAL hy_oas_5d_chg   |     |
|  |  = +42bp (thresh 30)   |     |
|  | SIGNAL stock_bond_corr |     |
|  |  = +0.22 (flipped)     |     |
|  | BACKTEST regime=HIGH   |     |
|  |  VOL, GLD>SPY: +3.1%   |     |
|  |  mean, n=38            |     |
|  +------------------------+     |
|                                 |
|  If you disagree on the regime, |
|  here is what happens if I hold |
|  SPY instead:                   |
|  [ Run counter-scenario ]       |
|                                 |
+---------------------------------+
|  [ Your reply...      ] [ Send ]|
+---------------------------------+
```

### Non-negotiable interaction patterns

1. **Grounding contract.** Every factual claim the LLM makes must be anchored to a grounding tile (signal, backtest, cost calculation) or marked as explicit uncertainty. Unattributed numbers are a P0 bug. If the LLM wants to make a claim it cannot ground, it must say: "I don't have a source for that. I can run a backtest (ETA ~40 seconds) — want me to?"

2. **Confidence indicator per turn.** LOW / MEDIUM / HIGH, tied to backtest sample size and signal agreement. No fake precision. No "87.3% confidence".

3. **Sycophancy guard.** When the user pushes back, the LLM does not cave. It offers:
   - A counter-scenario ("here's what happens if I defer to your view")
   - An override path ("you can force this; I'll log the override with your stated reason")
   - Agreement only on new information ("if you share a source for the Fed minutes, I'll re-evaluate")

4. **Tool use is visible.** When Midas runs a backtest or calls the cost model, the user sees it happening ("Running backtest for SPY-hold counter-scenario, ~30s…") with the ability to cancel. No invisible compute.

5. **LLM is the router, classifier, and evaluator.** The code around `self.run()` (or Kaizen equivalent) does no pre-filtering. The raw user message plus the structured context bundle is passed to the LLM, which decides which tools to call, how to reply, and whether to push back.

6. **Human-in-the-loop control from within Debate.** At any point the user can tap "Approve the original proposal", "Modify and approve", "Reject", or "Override and hold current" directly from within the chat. The decision is logged with a reference to the debate. The debate does not have to end before the decision.

7. **Conversation persistence and resume.** Every debate is saved with full tool traces. The user can reopen it from the Trade Log, from Portfolio Detail, or from a "prior debates" index in Settings. Weekly summaries (Flow 6) reference prior debates by ID.

8. **Memory with control.** Cross-session memory is on by default. The user can view, search, export, and delete any debate from Settings. Deletion removes from retrieval; audit trade-log references are preserved per regulatory need, and this is clearly disclosed.

### Suggested openers (wayfinding)

To solve the blank-canvas problem, every debate opens with 2–4 context-appropriate suggested questions, generated by the LLM from the pre-loaded context. **These are suggestions, not a menu — the user can still ask anything.** Never pre-classify user input against these suggestions in code.

### LLM-unavailable fallback

See `03-empty-and-error-states.md`. When the LLM provider is down, Debate becomes a static grounding viewer: the user can see the signals, backtests, and cost model outputs that drove the proposal, but cannot have a conversation. This is honest and preserves the approval flow.

### Success criteria

- User can get from "I don't understand this trade" to "I understand it and can decide" without leaving the debate screen.
- Zero hallucinated numbers in ground-truth audits.
- Sycophancy incidents (LLM changes recommendation without new information) caught in red-team testing at < 1%.
- Debate open rate from rebalance proposals: 20–40% in calm regimes, 40–70% in turbulent regimes.
- Decision-from-within-debate rate > 60% (users don't have to leave the debate to act).

### Failure modes

- LLM hallucinates a backtest number → product is dead. Mitigation: strict grounding enforced at the tool-use layer. LLM can only quote numbers returned from a tool call in the current session.
- LLM capitulates when user pushes → users stop trusting it. Mitigation: sycophancy guard, counter-scenario pattern, explicit override-log design.
- User asks something the LLM can't answer → dead end. Mitigation: explicit "I don't know, here's what it would take" path, never fake an answer.
- Tool call latency kills the exchange. Mitigation: stream partial answers, show tool progress, cap backtest runs to ~30s in debate (longer runs queue and notify).

---

## Flow 6 — Post-trade review (weekly summary)

**Trigger**: Every Sunday evening (user-local time, user-configurable). Notification delivered with lowest-priority channel setting — this is not urgent.

**Goal**: Give Alex a 90-second weekly accountability read: what executed, what didn't, how costs came out vs estimate, P&L attribution, and a soft outlook for next week. This is the honest audit layer that earns permission for the autonomous mandate.

### Notification

```
  Your weekly Midas summary is ready.
  3 trades this week. Up 0.4%. No action needed.
```

### Screen layout

```
+---------------------------------+
|  Week of 2026-04-05             |
|  Portfolio: $1,284,430          |
|  Week:  +0.4%  (+$5,120)        |
|  vs 60/40: +0.1%                |
+---------------------------------+
|                                 |
|  What executed                  |
|   3 trades, actual cost $31     |
|   (estimated $34, -$3 under)    |
|   [ see trade log ]             |
|                                 |
|  What didn't                    |
|   1 proposal rejected by you    |
|   (XLE trim) — S&P energy up    |
|   1.8% since, cost of your      |
|   override: +$430 vs Midas plan |
|   [ see debate ]                |
|                                 |
|  Where returns came from        |
|   Precious metals    +2.1%      |
|   Gov bonds          +0.8%      |
|   Equities ETF       +0.1%      |
|   REITs              -0.3%      |
|                                 |
|  Cost this week                 |
|   Commissions   $18             |
|   Slippage      $13             |
|   Total         $31  (2.4 bp)   |
|                                 |
|  Looking to next week           |
|   Regime: CALM TREND (stable)   |
|   Next rebalance check: Fri     |
|   Midas doesn't expect any      |
|   major moves unless HY OAS     |
|   widens above 380 bp.          |
|                                 |
|  [ Ask Midas about this week ]  |
+---------------------------------+
```

### Design rules

1. **Honest scorekeeping, including against the user's own overrides.** If Alex rejected a trade and it cost them, that cost is shown plainly with a link to the original debate. This is uncomfortable and necessary — it is how the product earns trust over time.
2. **Cost vs estimate is always shown.** If the cost model drifts, Alex should see it in the weekly summary before it becomes a surprise. Also gates the cost model quality SLO.
3. **P&L attribution at sleeve level, not ticker level.** Ticker-level detail is in Portfolio Detail and Trade Log, one tap away.
4. **Outlook is plain language, not a prediction.** "Midas doesn't expect any major moves unless HY OAS widens above 380 bp." This gives Alex a testable falsifier, not a forecast.
5. **"Ask Midas about this week"** opens Debate with the weekly summary context pre-loaded. If Alex wants to dig into why XLE was trimmed, they can, from within the summary.
6. **Notification is lowest priority.** Never push, never badge — the weekly summary waits in the app. Alex reads it on their schedule.

### Decision points

- Tap "see trade log" → Trade Log filtered to this week.
- Tap "see debate" (on the override row) → resumes the debate that led to the override.
- Tap "Ask Midas about this week" → Flow 5 with weekly-summary context.
- Do nothing → the summary is archived after 7 days but always accessible from Settings → History.

### Success criteria

- User opens weekly summary at least 2 out of 4 weeks per month.
- Cost-model drift (actual vs estimate) stays within ±20% at P90.
- Override-cost visibility is never hidden, regardless of direction.
- User can trace any number on the summary back to a specific trade, signal, or backtest within 2 taps.

### Failure modes

- Weekly summary becomes a dopamine surface ("up 2%!") → violates the zero-engagement-loop principle. Mitigation: tone rules, no celebratory language, no green fireworks, no streaks.
- User never reads the summary → accountability layer breaks. Mitigation: acceptable. The summary's primary job is to exist and be verifiable, not to be opened every week. Trust comes from knowing it exists and having spot-checked it, not from religiously reading it.

---

## Cross-flow design invariants

These apply across all six flows:

1. **Biometric gate on every execution.** Non-bypassable. Face ID / Touch ID / passkey on mobile; WebAuthn / passkey on web.
2. **No silent auto-trading in HIGH_VOL or CRISIS regime.** Hard invariant, enforced at the allocator, surfaced at the UI.
3. **Paper mode is identical to live mode except for the execution target.** No secondary "paper" visual styling, no watermark. This is deliberate — paper mode should build real confidence.
4. **Every AI claim is grounded.** Every trade has a signal snapshot. Every debate has a tool trace. Every backtest has a run ID. No unattributed numbers.
5. **Plain-language copy per `rules/communication.md`.** No raw technical errors. No jargon without explanation. Outcomes, not implementation.
6. **LLM-first reasoning per `rules/agent-reasoning.md`.** Zero hardcoded intent routing in any decision path the LLM should own.
7. **Mobile-first for decision flows (2, 3, 4); desktop-first for analysis flows (Backtest Explorer, Trade Log). Debate (5) is equal-weight on both.**
