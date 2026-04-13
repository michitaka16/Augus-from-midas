# Midas — UI/UX Design Research

Phase: 01-analysis / research
Author: uiux-designer
Date: 2026-04-09

## 0. Design Brief in One Line

Midas is an autonomous multi-asset portfolio platform for a delegator who refuses to monitor markets, but insists on understanding — and, when it matters, arguing with — every material decision the system makes. The UX must hold two opposing states in tension: **zero-touch calm** in normal regimes, and **instant, high-trust approval** in turbulent ones. The differentiator is not charts; it is a conversation with a system that can prove its reasoning.

---

## 1. Persona

### Primary — "The Delegator Who Still Wants Control" (Alex, 42, HNW self-directed)

- **Capital**: $250k–$2M liquid, IBKR Pro account
- **Job**: Tech exec, founder, surgeon, or senior professional. 50+ hours/week in their actual field.
- **Relationship to markets**: Opinionated, reads macro weekly, has strong views on regimes, hates "trust me" black boxes. Has lost money to both "set and forget" robos (too generic, bled out in 2022) and DIY (emotional, over-traded in 2020).
- **Core tension**: Wants the system to act without them 95% of the time, but wants the ability to interrogate any decision down to the signal level, and to veto or argue when their macro view diverges from the system's.
- **Triggers for attention**: Regime shift, drawdown alert, proposed trade in a sleeve they care about, portfolio-level rebalance, news event they already heard about through their own channels.
- **Success measure**: "I opened the app twice this month, each time it took <90 seconds, I approved the right thing, and my portfolio beat a 60/40 benchmark net of costs."
- **Failure mode**: Opens the app, sees a trade they don't understand, cannot get a straight answer from the AI, closes the app, loses trust, cancels.

### Contrast personas (explicitly NOT the target)

| Persona | Product they use | Why Midas is wrong for them |
|---|---|---|
| **Set-and-forget retiree** | Betterment, Wealthfront, Schwab Intelligent | Midas exposes too much machinery. They want one number and a pie chart. |
| **DIY quant / active trader** | IBKR TWS, QuantConnect, Composer | Midas hides the order book and commits to weekly-cap rebalancing. Too slow, too opinionated, too high-level. |
| **Crypto degen** | Binance, Robinhood Crypto | Wrong asset universe, wrong risk profile, wrong time horizon. |

### The "debate" moment — what Alex actually wants

When the dashboard says "Rotate 8% from SPY to GLD", Alex wants to tap one button and have a conversation that looks like this:

> Alex: "Why gold? Real yields are rising."
> Midas: "Three signals triggered: (1) realized vol 20d crossed 18, (2) HY OAS widened 45bp in 5 sessions, (3) stock/bond 60d correlation flipped positive. The allocator re-weighted defensives. Gold over long bonds because the 10y term premium signal is still negative. Here is the regime-conditional backtest: [link]. If you disagree on real yields, here is what happens if I hold SPY instead: [counter-scenario]."

That is the product. Everything else is table stakes.

---

## 2. Information Architecture

### 2.1 Screen inventory (priority-ordered)

1. **Dashboard** — zero-monitoring default state
2. **Pending Approvals** — the attention funnel in turbulent mode
3. **Debate Chat** — the USP
4. **Portfolio Detail** — sleeve-level drill-down
5. **Backtest Explorer** — the proof layer
6. **Trade Log + Audit** — immutable ledger
7. **Settings** — risk profile, thresholds, approval prefs, sources
8. **Onboarding + Paywall** — covered in section 7

### 2.2 Dashboard — the "nothing to do" state

The dashboard's primary job is to **give Alex permission to close the app**. Most days, that is the correct action. Layout (desktop, dark mode):

```
+-------------------------------------------------------------+
| Midas        Portfolio  Debate  Backtests  Log     Alex v   |
+-------------------------------------------------------------+
|                                                             |
|  $1,284,430                  +2.1% MTD   +14.8% YTD         |
|  Portfolio value             vs 60/40:  +3.2% YTD           |
|                                                             |
|  [ Regime: CALM TREND ]    Next review: Fri 11 Apr          |
|                                                             |
|  --- Sleeves ---------------------------------------------- |
|  Equities ETF    42%  ████████████████░░░░   +1.8%          |
|  Gov bonds       18%  ███████░░░░░░░░░░░░░   +0.2%          |
|  Precious met    12%  █████░░░░░░░░░░░░░░░   +3.4%          |
|  REITs            8%  ███░░░░░░░░░░░░░░░░░   -0.6%          |
|  ...                                                        |
|                                                             |
|  --- Planned actions ------------------------------------- |
|  No trades planned. Next rebalance check: Fri 08:30 ET.    |
|                                                             |
|  [ Ask Midas anything ]                                     |
|                                                             |
+-------------------------------------------------------------+
```

Key choices:

- **Portfolio value dominates** (~25% of viewport). It is the only number Alex cares about on a good day.
- **Regime chip** is the second-most prominent element. It is the single best predictor of whether Alex needs to engage.
- **Benchmark comparison** is always visible but secondary. The chart drawer is collapsed by default — this is anti-Robinhood. We do not want to encourage intraday checking.
- **"Planned actions" block** is a micro-feed, not a chart. On calm days it reads "no trades planned" and that is a feature, not a bug.
- **Persistent debate entry point** at the bottom: "Ask Midas anything" — always one tap away, never buried in a menu.

Mobile version collapses to a single vertical column. Portfolio value, regime chip, approvals badge, "Ask Midas" CTA. Sleeve breakdown is a tap-to-expand accordion. No chart on the home screen — force navigation to Portfolio Detail for any chart.

### 2.3 Pending Approvals — the attention funnel

Surfaced as a red badge on the nav and as a push notification (iOS/Android) and email (web fallback) when the regime detector flips to HIGH_VOL or when any proposed trade exceeds a user-set threshold. Layout per item:

```
+-----------------------------------------------------------+
|  PROPOSED TRADE  #2 of 4              2026-04-09 08:32 ET |
+-----------------------------------------------------------+
|  SELL  250 SPY   @ ~$512.40   (~$128,100)                 |
|  BUY   820 GLD   @ ~$156.20   (~$128,080)                 |
|                                                           |
|  Net cost estimate: $34.20 (commission $18, slippage $16) |
|  Portfolio impact: +1.2% defensive allocation             |
|  Expected turnover this month: 14% (cap 20%)              |
|                                                           |
|  WHY:                                                     |
|   - Regime detector: HIGH_VOL triggered 2026-04-09 06:14  |
|     (VIX 24.8, HY OAS +42bp 5d, corr flip)                |
|   - Allocator: defensive weight 18% -> 26%                |
|   - Cost gate: passed (2.7bp of NAV, cap 10bp)            |
|                                                           |
|  [ View backtest ]  [ View signals ]  [ Debate this ]    |
|                                                           |
|  [  REJECT  ]     [  DEBATE  ]     [  APPROVE  ]          |
+-----------------------------------------------------------+
```

Mobile: the "Approve" becomes a swipe gesture (swipe right) with biometric confirm (Face ID / fingerprint) on release. Swipe left rejects. Tap opens debate. **Bulk approve** is available with a checkbox per item: "Approve all 4" with per-item opt-out.

Hard rule: execution NEVER happens without biometric confirm on mobile or passkey / WebAuthn on web. This is both a trust affordance and a regulatory hedge (see A2).

### 2.4 Debate Chat — the differentiator

This is the screen that sells the product. Full-bleed chat layout with one distinguishing property: **every AI turn is anchored to structured grounding tiles**, not prose. Design:

```
+-----------------------------------------------------------+
|  Debate: SELL SPY / BUY GLD (2026-04-09)         [ x ]    |
+-----------------------------------------------------------+
|                                                           |
|  YOU                                                      |
|  Why gold? Real yields are rising.                        |
|                                                           |
|  MIDAS  [ confidence: MEDIUM ]                            |
|  I'm tilting to gold because three signals crossed their  |
|  thresholds simultaneously — not because I'm betting on   |
|  real yields.                                             |
|                                                           |
|  +-- Grounding (3 sources) ---------------------------+   |
|  |  [SIGNAL] realized_vol_20d = 18.4  (threshold 18) |   |
|  |  [SIGNAL] hy_oas_5d_change = +42bp (threshold 30) |   |
|  |  [SIGNAL] stock_bond_corr_60d = +0.22 (flip)      |   |
|  |  [BACKTEST] regime=HIGH_VOL, GLD over SPY:        |   |
|  |     +3.1% mean / +6.8% p75 / -1.2% p25 (n=38)     |   |
|  |  [COST] est 2.7bp of NAV, under 10bp cap          |   |
|  +---------------------------------------------------+   |
|                                                           |
|  If you disagree on the regime call, here is what         |
|  happens if I hold SPY instead:                           |
|  [ Run counter-scenario -> ]                              |
|                                                           |
|  ---------------------------------------------------------|
|  [ Your reply...                         ] [ Send ]       |
+-----------------------------------------------------------+
```

Non-negotiable patterns (mapping to Shape of AI):

- **Citations, not prose** — every claim is anchored to a signal ID, a backtest ID, or a cost calculation. If the AI cannot cite, it cannot claim. Unattributed numbers are a bug, not a feature.
- **Confidence indicator per turn** — LOW / MEDIUM / HIGH, tied to backtest sample size and signal agreement. No fake precision ("87.3% confidence" is banned).
- **Resist sycophancy** — when the user pushes back, the AI does not capitulate. It offers a counter-scenario: "If you believe X, here is the portfolio I would hold." The user then explicitly overrides, and the override is logged.
- **Yielding control** — user can always say "override: hold SPY" and the system records the override with rationale. The system does not silently agree; it logs the disagreement.
- **Never invent numbers** — if a backtest for the exact scenario does not exist, the AI says so and offers to run it. The compute cost and ETA are surfaced before the run.
- **Memory with control** — debates are persisted and can be resumed. Alex can view, edit, and delete prior debates from Settings.

This screen is also the **primary entry point for ad-hoc questions**: "What would you do if VIX hit 40?" "Why am I underweight EM?" "Explain the last rebalance." Free-form input; structured grounding output.

### 2.5 Portfolio Detail

Sleeve-level view with drill-down. Top: donut of sleeves. Tap a sleeve to expand into its holdings, each with: current weight, target weight, drift, rationale chip ("defensive tilt", "momentum leader", "dividend income"). Every rationale chip is tappable and opens a Debate prefilled with "why is X in the Y sleeve?" Desktop adds a side panel with regime-conditional return decomposition.

### 2.6 Backtest Explorer

Multi-horizon grid (1y / 3y / 5y / 10y rolling) across regime buckets (calm bull, calm bear, high-vol, crisis). Each cell shows: mean return, p25/p75, max drawdown, turnover, cost drag. Tap a cell for the equity curve and the trade log for that window. Export to CSV. This screen is **desktop-primary** — mobile shows a compact summary card and defers detail to web.

### 2.7 Trade Log + Audit

Immutable, append-only. Every row: timestamp, instrument, side, qty, price, commission, slippage, signal snapshot hash, allocator version, approval source (auto / user / override), backtest reference, debate reference (if any). Filter by date, sleeve, approval source. Export to CSV and PDF for tax and regulatory purposes. This is the product's compliance spine and must be designed as such from day one.

### 2.8 Settings

Grouped into five sections, each mapping to a governance dimension of the system:

1. **Risk profile** — sleeve caps, max drawdown tolerance, concentration limits
2. **Regime thresholds** — advanced users can tune VIX / OAS / correlation triggers; defaults are shipped and gated behind an "I know what I'm doing" toggle
3. **Approval preferences** — auto-approve thresholds ($ and % of NAV), turbulent-mode behaviour, quiet hours
4. **Data and news sources** — EODHD key, Perplexity key, backup toggles
5. **Account and billing** — tier, payment method, debate credits (see section 7)

---

## 3. Rapid Decision-to-Execution Patterns

References studied: Robinhood (swipe-to-buy, but we reject its dopamine loop), IBKR GlobalTrader (rich but slow), Public (social cruft, but their "why I bought" prompts are interesting), Composer (symbolic strategy DSL, debate-friendly), Stripe Dashboard (approval density), Mercury (banking approvals, closest analog).

### 3.1 One-screen approval card

All information required to approve a trade must fit on a single mobile screen above the fold. The card in section 2.3 is the canonical form. Information hierarchy from top: instrument and size, net cost, portfolio impact, why (3 bullets max), action bar.

**What is deliberately absent**: intraday price chart, order book, heatmap, social sentiment. These belong in Portfolio Detail and Debate, not on the approval card. Decision fatigue is the enemy.

### 3.2 Bulk approve with per-item opt-out

When a regime flip generates 3–8 correlated trades, forcing Alex to approve each one individually is user-hostile. Pattern:

```
[ 4 proposed trades ]
  [x] SELL 250 SPY / BUY 820 GLD
  [x] SELL 100 QQQ / BUY 310 IEF
  [x] SELL 50 EEM  / BUY 180 SHY
  [ ] TRIM 30 XLE               (user unchecked this one)
  [  Approve 3  ]     [  Debate selected  ]
```

Bulk approve is always opt-in per item, never opt-out. No pre-checked "approve everything".

### 3.3 Biometric confirm

Face ID / Touch ID / passkey on every execution. Non-bypassable. The 200ms of friction is the feature — it is the difference between a product that can be regulated and one that cannot.

### 3.4 What we are NOT doing

- No swipe-to-execute without biometric. Robinhood's pattern is actively irresponsible at this capital tier.
- No notifications designed to drive engagement. Notifications are strictly informational: "4 trades pending approval due to regime change". No "your portfolio is up 2% today!".
- No gamification, streaks, or badges. Alex will delete the app.

---

## 4. Debate-with-AI Interaction Patterns

Detailed in section 2.4; this section formalises the rules.

### 4.1 The grounding contract

Every AI claim in Debate must be one of:

1. **Signal citation** — a named signal with a numeric value and a threshold
2. **Backtest citation** — a specific backtest run ID with sample size and percentile outcomes
3. **Cost citation** — a specific cost model output with assumptions
4. **Explicit uncertainty** — "I don't have a backtest for this exact scenario. I can run one (ETA 40s, cost: 1 credit)."

Anything else is a prose hallucination and is a P0 bug.

### 4.2 Sycophancy guard

When the user pushes back, the system MUST NOT change its recommendation without a new signal. Instead it offers:

- **Counter-scenario** — "Here is the portfolio if I defer to your view."
- **Override log** — "You can force this. I will record the override with your stated reason."
- **Agreement only on new information** — "You mentioned the Fed minutes. I don't have those in my sources. If you share a link, I can re-evaluate."

The AI is allowed to be wrong, but it must be wrong for stated reasons, not out of deference.

### 4.3 Tone and identity

- Name: "Midas" (system), not a human name. No avatar face. A geometric mark, dark-mode gold on near-black.
- Voice: analytical, concise, numerate. No emoji, no exclamation marks, no "Great question!".
- Disclosure: every AI message is prefixed with the system mark; no ambiguity about whether a message is human or machine.

### 4.4 Memory and consent

Cross-session memory is on by default. Alex can view, search, export, and delete any debate. Deletion removes it from retrieval but audit records (trade log) are preserved per regulatory need and clearly disclosed.

---

## 5. Cross-Platform Stack Recommendation

### 5.1 Requirements

- Web desktop: analysis-primary, backtest explorer, trade log, settings-heavy
- iOS and Android: approval-primary, debate, dashboard, light analysis
- Single design system across all three
- Small team, fast iteration, commercial-grade polish

### 5.2 Options considered

| Option | Pros | Cons |
|---|---|---|
| **Flutter everywhere (incl. Flutter Web)** | One codebase, one design system, strong native feel on mobile, excellent charting via fl_chart / Syncfusion | Flutter Web is still weak on text rendering, SEO, and desktop keyboard ergonomics. Backtest explorer on desktop suffers. |
| **React (Next.js) web + React Native mobile** | Best-in-class web, strong mobile, shared TypeScript types, huge component library ecosystem (shadcn, Radix, TanStack) | Two UI codebases, two design system implementations, drift risk |
| **Next.js web + Flutter mobile** | Best web + best mobile | Two languages, two design systems, worst of both worlds for a small team |
| **PWA only** | Cheapest | No biometric ergonomics, no push notifications on iOS worth relying on, no App Store presence for commercial credibility |

### 5.3 Recommendation: Next.js (web) + React Native (Expo) mobile

Justification:

1. **Desktop analysis is a first-class use case**. Backtest explorer, trade log, and debate with long reasoning chains all benefit from real web. Flutter Web is not there yet for text-heavy financial UIs.
2. **Shared TypeScript domain models** between web and mobile via a `packages/core` workspace. Same API client, same zod schemas, same debate types. This closes most of the design-system drift risk.
3. **Expo** gives biometric (expo-local-authentication), push (expo-notifications), and OTA updates (EAS Update) with minimal native code. Critical for approval UX and regulatory patching.
4. **shadcn/ui + Tailwind** on web, **Tamagui or NativeWind** on mobile, unified via design tokens in `packages/tokens`. Single source of truth for color, spacing, typography.
5. **Commercial credibility**: App Store + Play Store presence is table stakes for a paid financial product. PWA-only is a non-starter.

Rejected Flutter because: the debate screen (which is text-and-citation heavy) and the backtest explorer (which is grid-heavy) are both web-native interaction models, and Flutter Web's text rendering and selection behavior still trails HTML. The mobile win does not compensate.

---

## 6. Design System

### 6.1 References

- **Linear** — information density, keyboard-first, muted palette, dark mode by default
- **Stripe Dashboard** — table density, number formatting, approval flows, status chips
- **Mercury** — banking approvals, bulk actions, audit log UI, trust signals
- **Arc** — sidebar and command palette ergonomics
- **Composer** — symbolic strategy display, backtest result layout

Deliberately NOT referenced: Robinhood (dopamine UX), Public (social cruft), any crypto exchange.

### 6.2 Tokens

- **Mode**: Dark-first. Light mode shipped but not the marketing hero.
- **Background**: near-black (#0A0B0D), surface (#121418), elevated surface (#1A1D22)
- **Accent**: restrained gold (#C9A961) for the Midas mark, brand CTAs, regime chips. Not a gradient, not neon.
- **Semantic**: green (#3FB77A) for gains, red (#E5484D) for losses, amber (#F5A524) for regime alerts. WCAG AA contrast on all surfaces.
- **Typography**: Inter for UI text, JetBrains Mono for numbers and signal IDs. Modular scale: 12 / 14 / 16 / 20 / 28 / 40. **Numbers are always mono, always right-aligned in tables.**
- **Radius**: 6px for small, 10px for cards, 16px for sheets. No `rounded-2xl` everywhere.
- **Shadows**: flat. Depth from surface elevation, not drop shadows.
- **Motion**: 150ms ease-out for state changes, 250ms for sheet transitions. No bounce, no elastic.

### 6.3 Information density

Desktop tables show 14px body, 12px meta, 40px row height. Dense but not cramped. Mobile bumps to 16px body, 44pt tap targets. Backtest explorer grid is 11px mono numbers — deliberately Bloomberg-dense for the one screen where Alex wants maximum signal per pixel.

### 6.4 AI slop self-audit

Running the fingerprint check on this spec:

- Typography: Inter for UI + JetBrains Mono for numbers with a real modular scale — PASS
- Color: restrained gold on near-black, no purple-to-blue gradients — PASS
- Layout: table-dense dashboard, not cards-in-cards — PASS
- Effects: flat, no glassmorphism, deliberate radius choices — PASS
- Motion: short ease-out, no bounce — PASS

Verdict: PASS. No AI slop fingerprints.

---

## 7. Commercialization UX Hooks

### 7.1 Onboarding

Five steps, gated:

1. **Value pitch** — one screen: "Delegate your portfolio. Debate every decision." One number: the backtest headline net of costs.
2. **Risk profile** — three questions, not twenty. Sleeve caps derived, shown transparently.
3. **IBKR link** — OAuth or API key flow. Explicit disclosure: Midas does not custody funds, IBKR executes.
4. **Paper mode** — default on for first 14 days. Every trade surfaces on the approval screen but executes against a paper account. This is both a trust builder and a regulatory hedge.
5. **Go live** — requires paper mode completion, biometric setup, and explicit acceptance of a signal-only disclosure (v1 per A2).

### 7.2 Tier structure

| Tier | Price | Features |
|---|---|---|
| **Observer (free)** | $0 | Dashboard read-only against paper portfolio, delayed regime signals (24h lag), 3 debate turns per week, full backtest explorer |
| **Operator** | $49/mo | Live IBKR linkage, real-time regime signals, approval flows, biometric execution, 100 debate turns per month, full trade log export |
| **Principal** | $149/mo | Unlimited debates, custom regime thresholds, multi-account (household), priority support, early access to new sleeves |
| **Advisor (future)** | custom | Multi-client, RIA-compliant (v2 path, gated on licensing) |

Rationale:

- **Free tier gives away the backtest explorer and delayed signals** — this is the marketing hook. Power users bring their own data and share screenshots. The paywall is on **execution and live signals**, which is what actually makes money.
- **Debates are metered, not free** — they cost real compute (backtest runs, LLM calls with tool use). Observer gets 3/week, Operator 100/month, Principal unlimited. This is the honest economic shape.
- **Execution is paid** — this is the critical value, and also where regulatory obligation begins. Free-tier users cannot trigger live trades.

### 7.3 Paywall placement

- Never between Alex and their portfolio value. Dashboard read is always free for linked accounts.
- At the **execution boundary** — clicking Approve on a live (not paper) trade the first time hits the paywall.
- At the **debate quota boundary** — a non-intrusive meter in the debate screen, with clear upgrade copy.
- At the **live signal boundary** — delayed signals show a "Live signals — upgrade" chip next to the regime indicator.

### 7.4 Trust signals for commercialization

- IBKR execution disclosure on every trade screen ("Midas does not custody your funds. IBKR executes.")
- Security page: biometric, WebAuthn, SOC 2 roadmap, data fabric disclosure
- Public backtest page (marketing): reproducible, downloadable, dated. The product's credibility lives or dies on this.
- Explicit "signal-only, not advice" disclosure in v1 per A2, with a clear v2 roadmap toward RIA registration.

---

## 8. Top UX Risks

1. **Debate hallucination** — if the AI ever invents a number or a backtest result, the product is dead. Mitigation: strict grounding contract (section 4.1) enforced at the model layer, never post-hoc. P0.
2. **Approval fatigue in turbulent mode** — a regime flip generating 8 trades across 4 sleeves can overwhelm. Mitigation: bulk approve with per-item opt-out, grouped by rationale, plus a "trust this rebalance wholesale" escape hatch behind a second biometric.
3. **Notification creep** — the temptation to ping Alex about every signal will kill the "I don't want to monitor it" promise. Mitigation: notifications are strictly gated to (a) regime flips, (b) proposed trades requiring approval, (c) execution confirmations. Everything else is in-app only.

---

## 9. Open Questions for the User

1. Does Alex want to share debates (read-only link) with an accountant or partner? If yes, we need a share-link design from day one.
2. Paper mode default of 14 days — is this acceptable, or does Alex want a "skip to live" button with a stronger warning?
3. Debate credits — is per-debate metering acceptable, or does Alex expect unlimited at the Operator tier? Economics depend on LLM and backtest compute costs.
4. Multi-account / household view — is this a v1 requirement or deferrable to Principal tier in v2?
