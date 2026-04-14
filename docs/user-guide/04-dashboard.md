# 04 — The Dashboard

The Dashboard is the home screen. It's designed to be a **calm state** — glance at it for 10 seconds and you should know whether anything needs your attention.

## The design principle

> "Permission to close the app."

Most finance apps try to pull you in — red numbers, constant updates, "3 new insights!" badges. Midas does the opposite. If everything is fine, the Dashboard tells you so in one glance and you leave. Only when something actually matters does the Dashboard demand engagement.

## Anatomy of the Dashboard

### 1. Header (top left)

```
Dashboard
Your portfolio is on track.
```

or

```
Dashboard
3 pending approvals need your attention.
```

The subtitle flips between these two based on pending approvals. That's the whole engagement logic — no badges, no pop-ups, no FOMO.

### 2. Regime Banner (full width, colored)

A single horizontal strip showing the current market regime:

- **Green**: Normal regime. Risk-on. System is running smoothly.
- **Yellow**: Cautious. Elevated stress. System has reduced exposure.
- **Red** (pulsing): Turbulent. Crisis mode. System has frozen. You need to decide.

Click the banner to drill into the 8 underlying signals (HY OAS, VIX, yield curve, etc.) and see which ones are elevated.

### 3. Three stat cards (middle)

| Card | What it shows | When to care |
|---|---|---|
| **Regime** | Current level + date | If it just flipped, check why |
| **Latest Signal Cost** | $ cost of most recent rebalance | If unusually high (>$20 for $100k portfolio), check Debate |
| **Pending Approvals** | Count of signals waiting for your decision | If > 0, go to Approvals |

Each card is clickable and navigates to the relevant detail view.

### 4. Current Allocation (bar chart)

Horizontal bars showing the target weight across 10 sleeves. Example:

```
Equity Sectors     ████████████░░░░░░░░  25%
Precious Metals    ████████░░░░░░░░░░░░  15%
Gov Bonds (Int)    █████░░░░░░░░░░░░░░░  10%
...
Cash               ████░░░░░░░░░░░░░░░░  10%
```

Colors follow a consistent palette:
- Blue: Equity sectors
- Yellow: Precious metals
- Purple: Government bonds
- Pink: REITs
- Red: Emerging markets
- Cyan/orange/teal: Other sleeves

The cash allocation fills whatever the vol-target scaling didn't invest. Higher cash = lower realized volatility.

### 5. Action buttons (bottom)

Two buttons:
- **Debate with AI** → goes to the Debate chat
- **View Backtests** → goes to the Backtest Explorer

That's it. No "Trade Now", no "Invest More", no upsells. The Dashboard's job is to show state, not drive conversions.

## What the Dashboard polls and how often

- **Regime state**: Every 60 seconds (when the tab is active). No polling when the tab is backgrounded — Midas respects your battery and doesn't burn server resources on users who aren't looking.
- **Signal data**: Same 60s cadence.
- **Pending approvals count**: Same 60s cadence.

You'll see the data update smoothly without a "Loading..." state unless the very first load fails.

## What you shouldn't see on the Dashboard

Things that would be red flags:
- **Your individual holdings or balance**. Midas is a publisher, not a broker. Your balance lives at IBKR.
- **Other users' data**. Every API endpoint that serves Dashboard data is impersonal (no user_id in the request path).
- **"Recommended actions"** or "Insights" feed. Midas doesn't generate prompts to act unless an actual signal is pending. No engagement manipulation.
- **Ads, cross-sells, "Try Premium"** overlays. Subscription is flat-rate. There's no tier to upsell.

## Reading the regime like a pro

The Dashboard's regime banner is the summary of 8 signals. Click it to expand:

```
Regime: Normal (score: 0.28, confidence: 82%)

  HY OAS                345 bps         [low stress]
  VIX3M backwardation   0.92            [contango, low stress]
  Cross-sector PC1      0.34            [stable correlations]
  VIX level             14.2            [below mean]
  200d SMA persistence  +42 days above  [uptrend confirmed]
  21d realized vol      11.3%           [below average]
  3m10y yield curve     +1.48%          [positive slope, healthy]

  Drawdown from peak: -2.1%
  SPY/TLT 21d corr:   -0.31 (bonds hedging equity)
  Active overrides:   none
```

This tells you not just the regime, but the distance from flipping. If HY OAS is at 480 and approaching 500, you know a flip to cautious is near even though the banner is still green.

## When the regime flips: what happens

### Normal → Cautious

- Banner turns yellow
- Push notification: "Regime: Cautious"
- Next signal will have reduced risk (K=4 sleeves instead of 6)
- No immediate trade — waits for next weekly signal

### Cautious → Turbulent

- Banner turns red, pulses
- **All subscribers get notified immediately**
- Signal generation triggers NOW (not waiting for Sunday)
- Approval card appears with a defensive allocation (cash + short bonds)
- Escalation timer starts (default 24h)
- If you don't respond, auto-defensive executes at timeout

### Turbulent → Cautious

- Banner turns yellow
- Next weekly signal will re-enter risk gradually
- No emergency action

### Any → Normal

- Banner returns green
- Normal weekly cadence resumes

## The "calm state" test

Spend 30 seconds on the Dashboard. Can you answer, without clicking anything:

1. What regime are we in?
2. Do I need to do anything right now?
3. How exposed is my portfolio to risk?
4. Did anything change recently?

If yes to all four → the Dashboard is working.
If no → either the UI needs improvement or your portfolio is in crisis mode.

---

**Next**: [05 — Model Portfolios](05-portfolios.md)
