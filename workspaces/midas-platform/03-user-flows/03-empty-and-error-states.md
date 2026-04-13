# Midas — Empty and Error States

Phase: 01-analysis / 03-user-flows
Author: uiux-designer
Date: 2026-04-09

Empty and error states are where trust is earned or lost. In Midas, the dominant state (calm markets) is an empty state, so "empty" must feel competent by default. Error states cover broker loss, data staleness, regime ambiguity, LLM unavailability, and cost-model soft blocks.

Every state in this document follows `rules/communication.md`: plain language, outcomes not implementation, no raw technical errors, no jargon without explanation.

---

## 1. The quiet market empty state

This is the dominant state of the product. 95% of days there is nothing to approve, nothing to alert on, nothing to debate. This state must feel **competent and present**, not empty or abandoned. A blank dashboard is a product failure.

### What not to do

- Blank space with a "you're all set!" tagline — reads as lazy.
- Motivational quotes — patronising, and Alex will delete the app.
- Fake activity (ticker tape, news feed) — violates the "I don't want to monitor it" brief.
- Celebratory graphics for calm days — dopamine loop, hard no.

### What to do

The quiet state shows six things, no more:

```
+-------------------------------+
|  Midas                  [M]   |
+-------------------------------+
|                               |
|  $1,284,430                   |  <- 1. portfolio value, big
|  +2.1% MTD  +3.2% vs 60/40 YTD|  <- 2. light context
|                               |
|  [ Calm trend ]               |  <- 3. regime chip
|  Last checked: 14:02 ET       |  <- 4. proof of wakefulness
|  Next review: Fri 08:30 ET    |  <- 5. anticipated event
|                               |
|  Nothing to approve today.    |  <- 6. explicit statement
|  Midas will let you know      |
|  when something changes.      |
|                               |
|  [ Ask Midas anything ]       |
+-------------------------------+
```

The critical element is **"Last checked: 14:02 ET"**. This single line is the anti-anxiety affordance: it proves Midas is awake without forcing the user to tap anything.

The secondary critical element is **"Next review: Fri 08:30 ET"**. This tells the user when to next expect attention. A product that makes expectations explicit earns the right to be quiet in between.

### Variants

| Condition | Copy |
|---|---|
| Calm trend, no pending review | "Nothing to approve today. Midas will let you know when something changes." |
| Paper mode, first 14 days | "Nothing to approve today. Midas is running on paper money for 10 more days." |
| Just approved trades this morning | "3 trades executed this morning. Nothing else to approve today." |
| Weekend | "Markets are closed. Midas will check for rebalance opportunities on Friday." |
| Holiday | "Markets are closed for [holiday]. Back to normal on [day]." |

The copy changes; the structure does not. The user learns the structure and can scan it in a glance.

---

## 2. Broker disconnect and paper-trading fallback

**Trigger**: IBKR OAuth token expired, revoked, or rate-limited. API key invalidated. Connection refused.

### State

```
+-------------------------------+
|  Can't reach Interactive      |
|  Brokers right now.           |
+-------------------------------+
|                               |
|  What this means:             |
|   Midas can still watch your  |
|   portfolio and propose       |
|   trades, but can't place     |
|   any real orders until you   |
|   reconnect.                  |
|                               |
|  What's happening:            |
|   Your connection to IBKR     |
|   stopped working at          |
|   2026-04-09 11:42 ET.        |
|   [ Reconnect to IBKR ]       |
|                               |
|  While you're disconnected:   |
|   Midas will keep proposals   |
|   waiting for you. None of    |
|   them will execute until     |
|   you reconnect and approve.  |
|                               |
|  Want to test without real    |
|  money? [ Switch to paper ]   |
|                               |
+-------------------------------+
```

### Design rules

1. **Plain-language impact first.** "Can't place real orders" is clearer than "Auth failure" or "IBKR 401".
2. **Reconnect is the primary CTA.** One tap to re-start the OAuth flow.
3. **Paper-mode switch is always offered.** A user who can't reconnect right now (traveling, no IBKR access) can still run Midas on paper and see what it would do. This is both a feature and a fallback.
4. **Pending proposals are held, not lost.** Explicitly stated. Nothing executes silently.
5. **Persistent banner until reconnected.** Same amber style as the regime-pause banner, different text: "Not connected to IBKR — [ reconnect ]".
6. **No raw error codes in the UI.** "401 Unauthorized" never reaches the user. It goes to logs with a correlation ID; the user sees "can't reach Interactive Brokers".

### Escape hatches

- Reconnect → re-runs OAuth / re-prompts for API key.
- Switch to paper → moves to a paper account without losing any configuration; Midas continues proposing trades against the paper portfolio.
- Contact support → link with correlation ID pre-filled.

---

## 3. Data fabric stale or high-latency

**Trigger**: The data fabric has not refreshed within its SLA window (e.g. EODHD quotes older than 30 minutes during market hours), or Perplexity news is unavailable, or a sleeve's pricing source is degraded.

### State

```
+-------------------------------+
|  Prices are a bit old.        |
+-------------------------------+
|                               |
|  The last price update was    |
|  14 minutes ago. Midas        |
|  usually refreshes every      |
|  2-5 minutes during market    |
|  hours.                       |
|                               |
|  What this affects:           |
|   Your portfolio value may    |
|   be slightly off (shown      |
|   with a stale-price tag).    |
|                               |
|  What this does NOT affect:   |
|   Midas will not place any    |
|   trades on stale prices.     |
|   Rebalance checks are        |
|   paused until data catches   |
|   up.                         |
|                               |
|  Midas is trying to catch up. |
|  [ Force refresh now ]        |
+-------------------------------+
```

### Design rules

1. **Portfolio value is tagged, not hidden.** Adding a small "stale" tag next to the number is more honest than showing nothing.
2. **Explicit "what this does not affect".** The key thing Alex needs to know is that nothing bad will happen silently. Midas will not trade on stale data.
3. **Force refresh is offered but not promised to work.** It re-requests from the primary source (EODHD); if the primary is down, it falls back to Yahoo Finance and shows a "using backup source" chip.
4. **No apology copy.** "Sorry for the inconvenience" is unhelpful. Stating the condition and the consequence is the help.

### Variants

| Condition | Copy |
|---|---|
| EODHD delayed, Yahoo available | "Using backup price source (Yahoo Finance). May be slightly less accurate." |
| Both sources delayed | "Prices are a bit old. Midas will not trade on stale data." |
| News unavailable (Perplexity down) | "News analysis is temporarily unavailable. Midas will use signal-only reasoning until it comes back." |
| Market closed, data as-of close | "Market is closed. Showing close of [date] [time]." (No error — this is expected.) |

---

## 4. Regime detector ambiguous

**Trigger**: The A3 regime ensemble is split — some signals say CALM, others say HIGH_VOL, and no clear majority. This is a first-class state, not an error.

### State

```
+-------------------------------+
|  Midas isn't sure what kind   |
|  of market this is.           |
+-------------------------------+
|                               |
|  The signals are split:       |
|                               |
|   CALM votes (2):             |
|    VIX 16.2  (threshold 18)   |
|    Correlation stable         |
|                               |
|   HIGH VOL votes (2):         |
|    HY OAS +31bp in 5d         |
|    Realized vol 17.9 rising   |
|                               |
|   Undecided (1):              |
|    Yield curve flattening     |
|                               |
|  What Midas is doing:         |
|   Playing it safe — treating  |
|   this like a turbulent       |
|   regime. Auto-trading is     |
|   paused until the signals    |
|   agree.                      |
|                               |
|  [ Debate this ]              |
|  [ See all signals ]          |
|                               |
|  [ Override: treat as calm ]  |
+-------------------------------+
```

### Design rules

1. **Ambiguity is disclosed, not hidden.** The user sees the exact vote split.
2. **Default is the safer side.** When in doubt, Midas pauses auto-trading. This matches the user brief ("don't trade without my permission" in turbulent markets) and is the right bias when you can't tell.
3. **"Playing it safe" is plain language, not "fail-safe default".**
4. **Override requires the same treatment as Decision 3 in `02-critical-decisions.md`** — reason field, second biometric, time-limited.
5. **Debate is prominent.** This is a moment where the user most wants to understand the system's reasoning, and Debate is the tool for that.

### When this state clears

Automatically, when 3 of 5 signals agree on a regime for at least 4 hours of continuous data. The user is notified when it clears: "The signals agreed. Midas is back to [CALM_TREND]." — low-priority notification, not a push.

---

## 5. LLM unavailable — debate fallback

**Trigger**: The LLM provider is down, rate-limited, or returning errors. The debate screen cannot have a conversation.

### State

```
+-------------------------------+
|  Debate is offline.           |
+-------------------------------+
|                               |
|  The AI that handles debate   |
|  isn't answering right now.   |
|  Midas will keep running      |
|  and proposing trades — you   |
|  just can't have a            |
|  conversation with it until   |
|  it comes back.               |
|                               |
|  In the meantime, you can     |
|  still see:                   |
|                               |
|  [ Signals that drove this    |
|    proposal ]                 |
|  [ Backtest for this regime ] |
|  [ Cost model breakdown ]     |
|                               |
|  These are the same grounding |
|  facts Midas uses — you can   |
|  inspect them without the     |
|  chat.                        |
|                               |
|  [ Back to proposal ]         |
+-------------------------------+
```

### Design rules

1. **Debate degrades to a static grounding viewer.** The signals, backtest, and cost model tiles (the same ones Debate would cite in chat) are viewable directly. The conversation is gone, but the evidence isn't.
2. **Approval is still possible.** Users can still approve, modify, or reject the underlying proposal from the originating screen. Debate being offline does not block the main flow.
3. **Honest about what's missing.** "The AI isn't answering" — not "temporarily unavailable", not "we're experiencing technical difficulties". Plain.
4. **No retry loop in the UI.** The backend retries with exponential backoff. The UI shows the current state; when debate comes back, the next open of the screen shows it working.
5. **No fallback to a less-capable LLM that could hallucinate.** Per `rules/agent-reasoning.md` and the grounding contract, it's better to have no debate than debate with untrustworthy output.

### What is NOT offered

- No "here's a cached answer from a similar prior debate" — too much risk of giving Alex a wrong answer from a different context.
- No "type your question and we'll answer when the AI is back" queue — this would be a lie if the model output is time-sensitive.
- No fake AI that simulates responses — dead product.

---

## 6. Cost model soft block: net-negative trade

Covered in detail in `02-critical-decisions.md` Decision 4. Summarised here:

**Trigger**: The cost model's expected cost exceeds the expected benefit of a proposed trade.

**State**: Soft block screen shown inline in the approval flow. "This trade costs more than it's worth." Override path available with biometric. No hard block — the user is the executor (A2).

**Design rule**: The block is honest framing, not a dark pattern. It explains the math in dollars, not in "information ratio" or "expected utility". The override is available but unglamorous.

---

## 7. Other error states worth naming

### 7.1 Execution partial fill

**Trigger**: IBKR fills only part of an order (liquidity, price move, halt).

```
  2 of 3 trades executed.
  SELL 250 SPY   filled @ $512.38  ✓
  BUY  820 GLD   filled @ $156.22  ✓
  SELL 100 QQQ   partial (60 of 100)
                 @ $411.20

  What Midas will do:
  Midas will try the remaining 40
  shares at the next price update.
  If it can't fill within 15
  minutes, you'll be asked again.

  [ Cancel remaining ]  [ Wait ]
```

Plain-language explanation of the state, explicit next action, and a cancel path. No silent retry. No blocking modal.

### 7.2 Execution rejected by IBKR

**Trigger**: IBKR rejects the order (insufficient buying power, restricted instrument, risk check).

```
  Interactive Brokers turned down
  one of the trades.

  Trade: SELL 250 SPY
  Reason (from IBKR):
   Not enough settled cash for
   the next leg.

  What Midas will do:
  Midas will propose a smaller
  version in the next rebalance
  window, or you can debate it
  now.

  [ Debate ]  [ OK ]
```

Translates the IBKR reason code into plain language. Never shows the raw code. Always offers a next action.

### 7.3 Backtest unavailable for requested scenario

**Trigger**: User asks in Debate for a backtest scenario that hasn't been run and would take >30s to compute.

```
  MIDAS
  I don't have a backtest for the
  exact scenario "2020 COVID
  recovery with 50% gold weight".

  I can run one now.
  Estimated time: 45 seconds
  Cost: 1 debate credit

  [ Run it ]  [ Not now ]
```

Per the grounding contract: explicit uncertainty, explicit compute cost and ETA, user consent required before running. No silent compute, no fake answer from a similar backtest.

### 7.4 User hits debate credit limit

**Trigger**: Observer (3/week) or Operator (100/month) tier runs out of debate turns.

```
  You've used your 100 debates
  this month.

  Your quota resets on 2026-05-01.

  While you wait, you can still:
   - See the signals behind any
     proposal
   - See the backtests
   - Approve, modify, or reject
     trades

  Want unlimited debates?
  [ Upgrade to Principal ]
```

No hard paywall in the middle of a conversation — the current debate continues until the user leaves it. The limit applies to new debates. No "are you sure you want to leave this debate?" nags.

### 7.5 Biometric fails 3 times in a row

```
  Face ID didn't recognise you.

  [ Try again with passcode ]
  [ Use a passkey ]
  [ Cancel the trade ]
```

After 3 failures, biometric is temporarily disabled for 15 minutes and the user must use passcode + passkey fallback. Failures are logged for security review.

---

## Cross-state design invariants

1. **Every error state states the impact in plain language first.** Implementation detail, if shown at all, comes second and behind a link.
2. **Every error state names what Midas will do next.** Users should never wonder "what happens now?"
3. **Every error state has a path forward.** Retry, fallback, manual path, or explicit "wait and try later".
4. **No raw error codes, stack traces, or HTTP statuses in the UI.** These go to logs with a correlation ID. If a user needs to contact support, the correlation ID is available from Settings → Help.
5. **No blocking modals with a single OK button.** Every dialog has a meaningful choice or is dismissible.
6. **No apologies.** "Sorry for the inconvenience" is filler. Stating the state, the impact, and the next action is the respect.
7. **No silent failures.** If something didn't work, the user finds out immediately.
8. **Empty ≠ broken.** The quiet-market state is an empty state that must feel competent. The design work is to make "nothing to do" feel like "everything is fine", because that is the truth most days.
