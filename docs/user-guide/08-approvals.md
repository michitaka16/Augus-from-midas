# 08 — Approving Trades

The approval card is where a signal becomes an action. It's the single most important UI in Midas because this is where you, the user, take or delegate control.

## Design principle: one screen, one decision

Most trading apps force you through multiple screens: review the signal, click trade, select account, confirm, wait. Midas collapses this to **one screen**: the approval card shows everything and a single tap executes.

```
┌─────────────────────────────────────────────────────┐
│  Normal Regime                         Confidence: 82%│
├─────────────────────────────────────────────────────┤
│  Growth Portfolio — Weekly Rebalance                 │
│  3 trades recommended. Cost: $4.52                   │
├─────────────────────────────────────────────────────┤
│  ☑ GLD   BUY 15 shares        $2,847   Cost: $1.02  │
│  ☑ TLT   SELL 8 shares         $832    Cost: $0.68  │
│  ☑ VWO   SELL 5 shares         $240    Cost: $0.22  │
├─────────────────────────────────────────────────────┤
│  Why this?    [Skip]              [Approve All] ✓   │
└─────────────────────────────────────────────────────┘
```

Everything you need to decide is on this card.

## When approval cards appear

### Weekly normal cadence
Sunday 7 PM ET, a new signal publishes. If it requires trades (target allocation differs from current by > $50 per sleeve), an approval card appears.

### Regime flip to turbulent
Immediately when regime flips to turbulent, a defensive approval card appears. Push notification fires to all subscribers.

### You changed portfolios
If you switch from Growth to Balanced on Tuesday, the Sunday signal's approval card will include the transition trades.

## Anatomy of the card

### Regime banner (top)
Colored strip matching the current regime. Click to see the 8 underlying signals.

### Portfolio header
- Portfolio name ("Growth Portfolio")
- Number of trades
- Total estimated cost

### Trade list
Each trade row:
- **Checkbox**: checked by default. Uncheck to skip this trade (other trades still execute).
- **Ticker**: the ETF symbol (e.g., GLD, TLT)
- **Direction**: BUY or SELL (color-coded green/red)
- **Shares**: the exact number to trade
- **Value**: dollar amount
- **Cost**: estimated cost for this trade (commission + slippage + impact)

### Actions
- **Why this?**: opens the Debate chat pre-filled with "Why this rebalance?" — useful if you want to understand the reasoning before approving
- **Skip**: closes the card without executing. The signal is marked "rejected". Your portfolio stays where it is.
- **Approve All**: the biometric prompt fires (Face ID / Touch ID / WebAuthn). On confirm, trades submit to IBKR.

## What to check before approving

### Checklist (2 minutes of review)

1. **Does the regime make sense?**
   - If the regime is Normal and the market feels calm → probably fine
   - If the regime is Normal but you just saw a big news event → check Debate for the system's reasoning
   - If the regime is Turbulent but you feel calm → trust the system (it's seeing signals you may not see)

2. **Is the turnover reasonable?**
   - Typical weekly turnover: 2-10% of portfolio
   - 15-20% turnover: unusual but possible if regime changed
   - 30%+ turnover: investigate via Debate. Possibly a data issue.

3. **Is the cost estimate reasonable?**
   - For a $100k portfolio: $3-$15 weekly
   - For a $1M portfolio: $30-$150 weekly
   - If costs exceed 0.1% of portfolio in a single rebalance → investigate

4. **Do any trades look weird?**
   - Very small trades (shares < 2): the minimum trade filter failed, ignore
   - Very large single-sleeve moves (> 15% of portfolio): check turnover penalty, may indicate regime change
   - Rebalance into an illiquid sleeve in turbulent regime: should be blocked by the cost model, but verify

5. **Does the allocation match the regime?**
   - Normal regime → 80%+ invested across 6 sleeves
   - Cautious → 60-70% invested, more bonds
   - Turbulent → 100% cash (if this isn't what you see, something's wrong)

## The three decision options

### 1. Approve All

Execution path:
1. Click "Approve All"
2. Biometric prompt (Face ID / Touch ID / WebAuthn)
3. Orders submit to IBKR as market orders
4. App polls IBKR for fill status (max 60s, 30 poll attempts)
5. Each fill is recorded in the audit trail
6. Dashboard updates with new positions
7. You get a push notification: "Trades executed"

If any order fails, the app stops and alerts you. Partial fills are recorded.

### 2. Skip

Execution path:
1. Click "Skip"
2. Confirmation dialog: "Your portfolio will not be rebalanced this week."
3. Click Confirm
4. Signal marked `rejected` in the database
5. No trades execute. Your current positions stay.
6. Next Sunday, a new signal will be generated — your portfolio will have drifted from the old target, and the new signal will include catch-up trades.

Skipping is your right. The only cost is drift — you're no longer at the target allocation, so your risk/return profile has shifted slightly.

### 3. Hold (turbulent regime only)

Execution path:
1. Click "Hold"
2. Approval marked `held` with current timestamp
3. Escalation timer RESETS to 24h from now
4. You can come back later to approve or reject
5. If you do nothing before the new timer expires, auto-defensive fires

Hold is useful when you want to think about it longer but don't want the auto-timeout to fire immediately.

## Partial approval (per-trade opt-out)

Each trade in the card has a checkbox. Uncheck to skip that specific trade while still approving the others.

Example:
- The signal wants to SELL 10 shares of TLT and BUY 15 shares of GLD
- You have a tax reason to hold TLT (large gain, want to wait for long-term treatment)
- Uncheck the TLT sell, keep the GLD buy checked
- Click Approve All
- Only the GLD buy executes

**Warning**: Per-trade opt-outs break the portfolio balance. If you only execute half the rebalance, your vol target and regime posture are no longer what the system designed. Use sparingly.

## The turbulent escalation protocol

When the regime flips to turbulent, a defensive approval card appears. This is the most important card you'll ever see.

### The timer

- **T+0h**: Card appears. Push notification fires.
- **T+12h (default)**: Reminder push fires.
- **T+24h (default)**: Auto-defensive executes.

You can adjust the timeout in Settings between 12h and 72h. Shorter = more protection but less time to think. Longer = more control but more risk if you miss the notification.

### The defensive allocation

The turbulent defensive is always:
- 80% short-term Treasuries (SHY)
- 20% cash
- 0% everything else

This is the "preserve capital" posture. You'll lose nothing to rates, won't earn much, and will wait out the storm.

### Options during turbulent

1. **Approve**: Execute the defensive. Your portfolio moves to cash+SHY. You'll re-enter when regime returns to cautious or normal.
2. **Reject**: Keep your current positions. You're explicitly saying "I want to stay exposed". Document your reasoning — the system won't protect you here.
3. **Hold**: Acknowledge, delay, reset timer. Useful if you want to debate the AI first.
4. **Do nothing**: Auto-defensive fires at timeout. This is the safe default.

### After approval

Once the defensive executes, the approval card disappears. The dashboard shows:
- Red banner
- Portfolio: 100% cash/SHY
- Next signal: generated when regime returns to cautious (not on weekly cadence)

The system will stay defensive until the ensemble score drops below 0.65 for 2 consecutive days.

## What happens after you approve

### Immediate (seconds)
- Orders submitted to IBKR
- Audit trail entry written
- Push notification sent to you
- Dashboard updates to "Executing..."

### Within 60 seconds
- Fills confirmed (ETFs are liquid — usually instant)
- Each fill recorded in audit trail
- Dashboard shows new positions

### End of day
- Your IBKR statement reflects the trades
- Tax lots are recorded by IBKR (not Midas)

### Next Sunday
- New signal generates based on your (now-updated) allocation
- If the target hasn't changed, the new signal's approval card will be empty (no trades needed)

## Audit trail entries

Every approval step creates audit entries:

1. `signal_published` — the signal was created
2. `approval_requested` — the card was shown to you
3. `approval_decided` — you clicked Approve/Skip/Hold
4. `order_submitted` — each individual order went to IBKR
5. `order_filled` — each fill confirmation
6. `escalation_step` (if turbulent) — timer events

Each entry is chain-hashed (SHA-256 linked to previous). The audit trail is tamper-evident.

## Mobile approvals

The mobile approval card is functionally identical to the web version but optimized for one-handed use:

- Regime banner at top
- Large BUY/SELL indicators
- Swipe-right on a trade to toggle include/exclude
- Big "Approve All" button at the bottom
- Face ID / Touch ID prompt on approve

Push notifications deep-link directly to the card. Tap the notification → biometric → approve in under 10 seconds.

## Common mistakes to avoid

### "Approve All" without reading
You should take 30 seconds to check the trades. Not 5 minutes — but don't rubber-stamp. If something's wrong, better to catch it before execution.

### Skipping repeatedly
If you skip 3 weeks in a row, your portfolio has drifted significantly. The next signal will require a larger rebalance to catch up — higher cost. Either engage with signals regularly or switch to a more passive portfolio (Balanced → Conservative).

### Rejecting turbulent defensives
Some users feel "I know better, the regime is wrong, I'll stay in equities". 80% of the time they're right — markets recover quickly. 20% of the time they lose 15-30% of portfolio value. The system is designed for the 20% case. Reject with caution.

### Holding during turbulent
"Hold" is not a decision. It's a postponement. If you're using Hold more than once per turbulent event, you're not engaging with the system — either approve the defensive or explicitly reject it.

### Adjusting individual trade checkboxes without reason
Every checkbox off breaks the portfolio balance. Use only when you have a specific tax/personal reason. Don't uncheck because "I don't feel good about selling TLT".

---

**Next**: [09 — Debating the AI](09-debate.md)
