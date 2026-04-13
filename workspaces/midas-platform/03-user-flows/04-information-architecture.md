# Midas — Information Architecture

Phase: 01-analysis / 03-user-flows
Author: uiux-designer
Date: 2026-04-09

This document defines the top-level navigation, screen inventory, and information hierarchy for Midas across mobile (iOS / Android) and web. Mobile-first because of the "rapid decision-to-execution" brief requirement, with explicit web parity notes.

The governing principle: **screens are organised around user intent, not feature categories.** A user opening Midas is doing one of five things: checking in (quiet state), acting on a proposal, debating a decision, inspecting the portfolio, or configuring the system. The nav maps directly to those five intents.

---

## 1. Top-level navigation

### 1.1 Mobile: 5-tab bottom nav (hard cap)

```
+-----+----------+----------+--------+----------+
|Home | Portfolio| Proposals| Debate | Settings |
+-----+----------+----------+--------+----------+
```

| Tab | Primary screen | Purpose | Default state |
|---|---|---|---|
| **Home** | Dashboard | Check in, glance, quiet state | Portfolio value, regime chip, "last checked", "next review", "nothing to approve today" |
| **Portfolio** | Portfolio Detail | Drill into sleeves, holdings, drift, rationale | Sleeve donut + sleeve list |
| **Proposals** | Pending Approvals | Act on proposed trades | Empty state 95% of the time; badge when non-empty |
| **Debate** | Debate history + new | Inspect reasoning, argue with the system | List of prior debates + "Ask Midas anything" |
| **Settings** | Account, Risk, Regime, Sources, Billing | Configure | Grouped sections |

### 1.2 Why 5 tabs and not 4 or 6

- Four tabs would merge Proposals into Home, which means the dominant quiet state gets visually polluted by a "0 pending" chip. The quiet state must be truly quiet.
- Six tabs push the tertiary tab outside comfortable thumb reach on mobile and force one of them (typically Debate) into a submenu. Debate is the USP; it is non-negotiable as a top-level tab.
- Five tabs keeps each tab thumb-reachable, gives Debate top-level presence, and leaves Proposals as a dedicated action tab with a badge.

### 1.3 What is NOT a top-level tab (and why)

| Not a tab | Where it lives | Why not top-level |
|---|---|---|
| Backtest Explorer | Portfolio Detail → "Backtest this sleeve", and from Proposal "View backtest", and from Debate grounding tiles | Desktop-primary, infrequently used on mobile, always reachable contextually |
| Trade Log | Settings → Trade history, and contextually from any trade-related screen | Compliance spine, not a daily destination |
| Notifications / Alerts | System-level (push + iOS/Android notification center) | The app's alerts live in the system tray, not inside the app |
| News | Nowhere — deliberately | Violates "I don't want to monitor it". News is a Debate grounding source, not a surface. |

### 1.4 Web: sidebar + persistent header

Web is analysis-heavier. The tab structure is the same five items, but presented as a collapsible left sidebar, with a persistent header showing portfolio value, regime chip, and "Ask Midas" quick access.

```
+--------+---------------------------------------+
|        |  Midas   $1,284,430  [Calm trend]  [Ask Midas]  [Alex v]
+--------+---------------------------------------+
|  Home  |                                       |
|  Port. |                                       |
|  Prop. |         Main content area             |
|  Debate|                                       |
|  Set.  |                                       |
|        |                                       |
|  ----  |                                       |
|  Back- |                                       |
|  test  |                                       |
|        |                                       |
|  Trade |                                       |
|  log   |                                       |
+--------+---------------------------------------+
```

Desktop gets two **extra secondary items in the sidebar** that are not top-level on mobile:

- **Backtest Explorer** — the proof layer, desktop-primary per the research doc (table-dense, grid-heavy)
- **Trade Log** — the compliance spine, desktop-primary for export and filter workflows

These are reachable contextually on mobile but not top-level. On desktop they earn sidebar slots because the screen real estate and interaction model support them.

### 1.5 Command palette (web only)

Desktop gets a `cmd+k` command palette for power use: jump to any sleeve, open any prior debate by date, run a backtest by scenario name, toggle paper/live, open Settings section directly. Not on mobile.

---

## 2. Screen inventory

Priority-ordered. Numbers correspond to rough usage frequency per week for the primary persona.

### Tier 1 — Daily or near-daily

1. **Dashboard (Home)** — quiet state, glance, close. 5–15 seconds. See Flow 2.
2. **Proposals / Pending Approvals** — surfaced by notification; checked ~1–2x per week in calm regimes, daily in turbulent. See Flows 3, 4.
3. **Debate** — invoked from a proposal or ad-hoc ~1–5x per week. See Flow 5.

### Tier 2 — Weekly

4. **Portfolio Detail** — sleeve drill-down, weekly check or on demand.
5. **Weekly Summary** — Sunday evening, one-read accountability surface. See Flow 6.

### Tier 3 — As needed

6. **Backtest Explorer** — before major decisions, during debate, during onboarding. Desktop-primary.
7. **Trade Log + Audit** — compliance, tax, export. Desktop-primary.
8. **Settings** — once at onboarding, occasionally thereafter.

### Tier 4 — One-time / rare

9. **Onboarding** — Flow 1. Once per account.
10. **Regime explanation screen** — on turbulent-regime trigger. See Flow 4.
11. **Override screens** — cost-model override, turbulent-regime override.
12. **Security / biometric setup** — onboarding and when biometric is reset.

---

## 3. Information hierarchy within each screen

The same principle applies across all screens: **the thing most users need first is biggest and highest. The thing power users need is one tap away, not visible by default.**

### 3.1 Dashboard (Home)

Rank order (top to bottom, largest to smallest):

1. Portfolio value ($1,284,430) — the one number Alex wants on a good day
2. Daily/monthly context (+2.1% MTD, +3.2% vs 60/40 YTD) — light, small
3. Regime chip (CALM TREND) — colour-coded, second-most prominent
4. "Last checked" + "Next review" — anti-anxiety timestamps
5. "Nothing to approve today" explicit statement
6. "Ask Midas anything" entry point
7. Sleeve breakdown (collapsed on mobile, expanded on desktop)

Explicitly absent: charts, news, ticker tape, notifications feed, alerts widget.

### 3.2 Proposals / Pending Approvals (list view when multiple)

Rank order:

1. Count of pending items (badge)
2. For each item: instrument and size, net cost, portfolio impact (sleeve delta), why (3 bullets max), CTAs
3. Grouping by rationale when multiple (regime flip produces 4 defensive trades)
4. Bulk-approve affordance

Empty state: "No proposals waiting. Midas will check again [next review time]." Same clarity as the dashboard empty state.

### 3.3 Proposal detail (single trade)

See `02-critical-decisions.md` Decision 1 for full layout. Hierarchy: trades count and cost → sleeve delta → expected improvement → why → CTAs.

### 3.4 Debate

Hierarchy:

1. Context strip at top (what are we debating?)
2. Suggested openers (when the debate is new)
3. Conversation history (scrollable)
4. Current AI turn with grounding tiles
5. Input field and send button (sticky bottom)
6. In-debate action bar (Approve / Modify / Reject the original proposal) — sticky, unobtrusive but always reachable

### 3.5 Portfolio Detail

Hierarchy:

1. Portfolio value + YTD/MTD context
2. Sleeve donut
3. Sleeve list with: current weight, target weight, drift, rationale chip
4. Tapping a sleeve → sleeve detail page with holdings, weights, rationale, "debate this sleeve" button
5. Desktop adds a side panel: regime-conditional return decomposition

### 3.6 Backtest Explorer (desktop-primary)

Hierarchy:

1. Filter bar: horizon (1y / 3y / 5y / 10y rolling), regime bucket (calm bull / calm bear / high vol / crisis), sleeves
2. Grid: one cell per (horizon × regime bucket), showing mean, p25/p75, max drawdown, turnover, cost drag
3. Detail pane: equity curve + trade log for the selected cell
4. Export: CSV, PNG chart

Mobile: compact summary card with a "see full backtest on web" link. We don't try to make a Bloomberg-grade grid work on a phone.

### 3.7 Trade Log + Audit

Hierarchy:

1. Filter bar: date range, sleeve, approval source (auto / user / override), instrument
2. Table: timestamp, instrument, side, qty, price, commission, slippage, signal snapshot hash, allocator version, approval source, linked debate
3. Row expand: full signal snapshot, cost model output, any linked debate
4. Export: CSV, PDF (for tax / regulatory)

Mobile: reverse-chronological list with tap-to-expand. No filters visible by default; filters behind a sheet.

### 3.8 Settings

Five sections, ordered by frequency of visit:

1. **Risk profile** — sleeve caps, max drawdown tolerance, concentration limits, approval threshold
2. **Approval preferences** — turbulent-mode behaviour, quiet hours, notification delivery
3. **Regime thresholds** (advanced) — gated behind "I know what I'm doing" toggle
4. **Data and news sources** — EODHD key, Perplexity key, backup toggles, data fabric status
5. **Account and billing** — tier, payment method, debate credits, export data, delete account

Trade Log is reachable from Settings → Trade history on mobile (since it's not a top-level tab).

---

## 4. Navigation rules

1. **Every tab preserves its own navigation stack.** Switching tabs does not reset the stack. Tapping the tab a second time returns to the tab root.
2. **Back button behaviour is platform-native.** iOS: swipe-back and top-left back. Android: system back. Web: browser back.
3. **Deep links are first-class.** Push notifications deep-link to the exact proposal, not to the app root. Similarly for weekly summaries and regime alerts.
4. **Persistent entry points**:
   - "Ask Midas anything" is accessible from Home (tap) and from the web header (always).
   - The regime chip is tappable on every screen where it appears and always opens the regime explanation.
   - The pending-approvals badge lives on the Proposals tab icon; tapping it jumps to the list.
5. **No hidden hamburger menus.** Five tabs on mobile, sidebar on web — everything reachable without a hidden layer.
6. **No infinite scrolling.** Trade Log and Debate history paginate by day, not by infinite scroll. Users should be able to reach the end of a list.

---

## 5. Notification architecture

Notifications are **strictly gated**. Per the research doc and the brief ("I don't want to monitor it"), the only allowed notification triggers are:

| Trigger | Priority | Channel |
|---|---|---|
| Regime flip to HIGH_VOL or CRISIS | High | Push + email |
| Proposed trade requiring approval | Normal | Push + email (digest) |
| Proposed trade rejected by IBKR (after user approval) | High | Push |
| Rebalance completed (confirmation) | Low | In-app only, no push |
| Weekly summary | Low | Push (lowest priority) or in-app only, user choice |
| Debate offline / degraded | In-app banner only | No push |
| Broker disconnect | High | Push |

**Explicitly forbidden**:

- Price-movement notifications ("SPY is up 2% today!") — violates the brief
- Engagement nudges ("You haven't opened Midas in 3 days") — would cause delete
- Marketing ("Try our new feature!") — never in the product
- Social / gamification — out of scope

---

## 6. Mobile-first rationale and web parity

### Why mobile-first

The brief requires "rapid decision-to-execution". The highest-stakes decisions — approving rebalances, responding to regime flips — happen when Alex is away from their desk. In meetings, in transit, at a coffee break. The product either works on a phone for decisions, or it fails the brief.

### What mobile does best

- Decisions under time pressure (Flows 3, 4)
- Glance-and-close (Flow 2)
- Debate as a focused conversation
- Biometric as the commit gate

### What desktop does best

- Backtest Explorer (dense grid, mouse hover, multi-cell selection)
- Trade Log (sortable columns, bulk export, filter chains)
- Portfolio Detail (side-by-side charts, drilling into holdings)
- Settings (forms are easier on a keyboard)
- Long debate threads with deep tool traces

### Web parity requirements

- Every decision that can be made on mobile can also be made on web.
- Every screen that exists on mobile exists on web (but some are secondary nav on desktop).
- Web has strict parity for: Dashboard, Proposals, Debate, Settings.
- Web has enhanced versions for: Portfolio Detail, Backtest Explorer, Trade Log.
- Design tokens (color, typography, spacing) are shared across web and mobile via a single source-of-truth, per `05-uiux-design.md` section 5.3.

---

## 7. Information density rules

| Screen | Density |
|---|---|
| Dashboard | **Low** — deliberate breathing room, the quiet state must feel calm |
| Proposals | **Medium** — enough to scan, not so much that items blur |
| Debate | **Medium** — text-heavy, but grounding tiles are dense |
| Portfolio Detail | **Medium-high** — sleeve list with numbers |
| Backtest Explorer | **High** — deliberately Bloomberg-dense on desktop, 11px mono numbers, maximum signal per pixel |
| Trade Log | **High** — tabular, compact rows, many columns |
| Settings | **Low** — forms with breathing room, clear labels |

The density choice per screen is deliberate and follows the research doc section 6.3.

---

## 8. What we are explicitly not building (IA exclusions)

To prevent scope creep and preserve the "delegator" positioning:

- **No social features.** No sharing to a feed. No leaderboards. No "what other Midas users are doing".
- **No news feed.** News is a grounding source for Debate, not a surface.
- **No watchlists for individual tickers.** Midas manages sleeves, not stock-picking.
- **No intraday charts on the home screen.** Charts are one tap away in Portfolio Detail.
- **No order book or direct order entry.** Midas is not a trading terminal.
- **No paper/live toggle in the main UI.** Paper mode is an account state, set at onboarding or via Settings. It doesn't belong in the main nav because switching between them is not a daily action.
- **No dark-mode toggle in the main UI.** System-following is the default; the toggle is in Settings for users who want to override.

These exclusions are as important to the product identity as the inclusions.
