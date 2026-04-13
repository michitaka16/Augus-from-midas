# Product & Platform Model — Midas

**Workspace**: `midas-platform`
**Phase**: 01-analysis / step 3.2–3.4
**Date**: 2026-04-09
**Inputs**: `briefs/01-user-brief.md`, `briefs/02-assumptions.md`, `01-analysis/01-research/{01..06}.md`
**Framing**: Autonomous execution (effort in sessions, not human-days, per `rules/autonomous-execution.md`).

---

## 0. Executive Summary

Midas is **a single-tenant decision-support tool that is structurally designed to become a multi-tenant platform**, but the platform identity is **not** a marketplace of strategies in v1 — that lever is held in reserve. The core platform identity is a **shared data-and-compute fabric with a one-to-many publisher channel**: market data is pulled once and reused for every subscriber, model portfolios are computed once and broadcast identically to every subscriber, and the only per-user surface is preferences + approval state held client-side.

This is not an accident of architecture. It is the only shape that simultaneously satisfies (a) the user's brief ("common database for all users", "commercializable"), (b) the *Lowe v. SEC* publisher exemption that makes US v1 legal without RIA registration (`01-research/03-broker-and-regulatory.md` §3.1), and (c) the cost economics where EODHD does not scale per-user (`01-research/04-data-fabric.md` §6).

**Headlines:**

1. **Platform structure** — Producer-light, consumer-led, partner-mediated. v1 has **one producer** (Midas itself, publishing a small set of model portfolios). Producer-side opening (community-published strategies) is a v3 unlock, gated on RIA registration.
2. **Network effect features** — Accessibility (mobile push → biometric approve, target sub-90s), engagement (regime chip + grounded debate), personalisation (client-side only), connection (IBKR + EODHD + Perplexity + FRED + Apple/Google push), collaboration (deferred to v3).
3. **Commercialisation pivot** — Midas is born multi-tenant on the data plane but single-publisher on the recommendation plane. The pivot point is not "personal → multi-user" (the architecture handles both from day one); the pivot point is **"signal-only publisher → discretionary RIA"**, and that gate is regulatory, not technical.

---

## 1. Platform Model — Producers, Consumers, Partners

### 1.1 The participant inventory

| Role          | v1 (publisher)                                              | v2 (RIA discretionary)                                  | v3 (community / marketplace)                                          |
| ------------- | ----------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------- |
| **Producer**  | Midas itself (1 publisher, 1–3 model portfolios)            | Midas + certified RIA partners running in-house sleeves | Community strategy authors (paywalled, vetted)                        |
| **Consumer**  | Self-directed HNW IBKR users ("Alex", `01-research/05` §1)  | Same + delegators willing to grant trading authority    | Same + followers of community strategies                              |
| **Partner**   | IBKR (broker), EODHD (data), Perplexity (news), FRED (free) | + Identity/KYC vendor, + audit/SOC2 vendor              | + Notary/escrow for strategy IP, + payments-out for revenue share     |
| **Regulator** | Out-of-band; geofenced UK/SG/EU                             | SEC RIA, FCA, MAS as in-band counterparties             | Same + content-publishing rules around third-party performance claims |

The brief's phrase *"common database for all users"* maps to **the data fabric, not a marketplace**. v1 has zero peer-to-peer interaction. The "platform" in v1 is the shared compute and the shared data fabric, not a marketplace of producers.

### 1.2 The "seamless direct transaction" question

In a classic platform definition (Choudary, *Platform Revolution*), the test is: *what value transaction happens directly between participants on the platform?* For Midas v1, the answer is honest and small:

- **Subscriber → Midas (publisher)**: subscription fee in exchange for access to a model portfolio + the debate surface + the backtest explorer. This is a SaaS transaction, not a platform transaction.
- **Subscriber → IBKR**: order placement, custody, execution. Midas is the catalyst but not the counterparty. The user retains full custody (`01-research/03-broker-and-regulatory.md` §5.1).
- **Subscriber ↔ Subscriber**: **none**. There is no comments thread, no shared portfolio, no fork button, no upvote.

This is deliberately not a network-effects business in v1. The flywheel that compounds is the **data fabric** (more subscribers → more shared cache hits → lower per-user data cost, `01-research/04-data-fabric.md` §6) and the **calibration loop** (more live fills → better cost model, `01-research/02-strategy-methodology.md` §5.7), not a producer-consumer marketplace.

### 1.3 When peer transactions become permissible

Peer-to-peer producer-consumer transactions (one user publishes a strategy, another subscribes to it) are deferred to **v3** for two independent reasons:

1. **Regulatory**: a community strategy author distributing personalised signals to other users is, under SEC interpretation, an investment adviser even if the platform is just the conduit. v3 requires Midas to be either an RIA or a regulated platform that vets community authors as IARs/sub-advisers. The legal frame is the SEC marketing rule + the publisher exemption narrowing established in 2019–2024 enforcement actions (`01-research/03-broker-and-regulatory.md` §4).
2. **Trust**: backtest-to-live decay is the canonical retail-quant failure mode (`01-research/01-competitive-landscape.md` §6.3). Letting users publish backtests they tuned themselves recreates the exact problem. v3 community publishing requires a forced **out-of-sample track record gate** before any strategy can be published, and that gate needs ~12 months of paper-mode telemetry. Midas does not have that telemetry until v1 has been in production for at least a year.

### 1.4 v1 platform shape, drawn

```
                         +-----------------------+
                         |   Midas (publisher)   |
                         |  - 1 to 3 portfolios  |
                         |  - Same bytes to all  |
                         +-----------+-----------+
                                     |
                  GET /v1/portfolios/{id}/signals/latest  (CDN-cacheable)
                                     |
        +----------------------------+----------------------------+
        |                            |                            |
    Subscriber A                 Subscriber B                 Subscriber C
   (own IBKR acct)              (own IBKR acct)              (own IBKR acct)
        |                            |                            |
        v                            v                            v
   +----------+               +----------+                  +----------+
   |   IBKR   |               |   IBKR   |                  |   IBKR   |
   +----------+               +----------+                  +----------+
```

The architecture in `01-research/06-framework-architecture.md` §6.3 makes the CDN-cacheability of `/signals/latest` a **legal tell** — the moment that response varies per user, Midas has slipped out of *Lowe* and into adviser status. This is the structural constraint that defines the v1 platform shape.

---

## 2. AAA Framework — Automate, Augment, Amplify

The AAA framing (Automate operational cost, Augment decision cost, Amplify expertise cost) maps cleanly onto Midas because the brief explicitly demands all three: *"I don't want to monitor it"* (Automate), *"debate with the AI"* (Augment), *"backtest comprehensively across all market conditions"* (Amplify).

### 2.1 Automate — what operational cost disappears

For a self-directed HNW investor today, the operational tax of running a multi-asset rotation portfolio looks like:

| Operational cost (today)                                             | Midas removes how                                                                                                                              |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Watching 8 sleeves daily for drift, regime, news                     | Regime ensemble runs at every market close; user only opens app when notified (`01-research/05-uiux-design.md` §2.2 dashboard's "no trades planned" default state) |
| Computing rebalance weights against current allocation               | `AdaptiveAllocatorNode` runs server-side once per cadence; user sees the delta, not the math                                                   |
| Estimating commissions, slippage, gap risk before placing each order | `TransactionCostNode` produces a per-trade bps breakdown shown inline on the approval card                                                     |
| Executing 3–5 trades per rebalance with correct sizing               | Order tickets pre-filled; biometric approve is the only user action                                                                            |
| Tax-lot bookkeeping and audit trail                                  | Immutable `audit_log` with content hashes; CSV/PDF export to accountant                                                                        |
| Reading 20+ news sources and pricing them into the decision          | Perplexity ingestion + grounded debate surface — news feeds the explainer, not the click                                                       |
| Survivorship-bias-free backtest of any change                        | CPCV walk-forward on the same node graph that runs live (`01-research/06-framework-architecture.md` §3 parity)                                 |

The shape of the automation is **scheduled batch** with **on-demand pulls**. There is no real-time data plane in v1 (`01-research/04-data-fabric.md` §1.4) and no real-time alerting beyond regime-flip and approval-pending events. The user's time budget per month should be **<10 minutes in normal regimes, <30 minutes in turbulent regimes**, which is the operational target the persona in `01-research/05-uiux-design.md` §1 is built around.

### 2.2 Augment — what decision cost disappears

The decision costs the brief's user is paying today and that Midas augments:

| Decision cost (today)                                       | Midas augments how                                                                                                                                                                                |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Is this volatility a regime shift or just noise?"          | Regime ensemble emits a label with the contributing signal stack visible. The user sees *which* signals tripped, not just the conclusion                                                          |
| "Should I trim equity here?"                                | The recommendation is presented with three alternatives in the debate surface: hold, partial trim, full rotation, each with a regime-conditional backtest distribution                            |
| "What position size makes sense given my account size?"     | The model portfolio is in weights; the user's client computes the dollar delta against their actual IBKR balance — server is unaware (the publisher constraint, `01-research/06-framework` §6.2) |
| "Am I being talked into this by my own confirmation bias?"  | The DebateAgent's sycophancy guard (`01-research/05-uiux-design.md` §4.2): when the user pushes back, the system offers a *counter-scenario* not capitulation                                      |
| "What does the historical record say about THIS situation?" | `fetch_counterfactual_backtest` runs the same Core SDK workflow with the user's hypothetical override and returns a CPCV percentile distribution                                                  |
| "Can I trust this number?"                                  | Every claim in the debate is anchored to a signal ID, backtest run ID, or cost model output. Unattributed numbers are blocked by the grounding contract (`01-research/06-framework` §2.2)         |

This is the **debate-with-AI loop**, and it is the single feature no competitor in `01-research/01-competitive-landscape.md` §1 ships. Titan has narrative, but it is broadcast video, not interactive. Composer has backtests, but only for strategies the user built themselves. The augment-loop differentiator is that **the user can argue with a system that can prove its reasoning to the signal level**.

### 2.3 Amplify — what expertise cost disappears

The expertise cost is the most interesting because it is the largest. Today, to do what Midas does, the brief's user would need to either hire a CFA portfolio manager (USD 2k–10k/month, opaque mandates) or assemble it themselves over years of self-study. Midas amplifies:

| Expertise that becomes accessible                                                                                                                                                                                                  | What it would cost otherwise                                                                                                |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Multi-signal regime detection (HY OAS, VIX3M backwardation, cross-sector PC1 variance, drawdown override) — `01-research/02-strategy-methodology.md` §2.9                                                                          | A discretionary macro PM, or 200+ hours of self-study following Faber, Asness, Antonacci, López de Prado                    |
| Adaptive Asset Allocation with vol targeting and L1 turnover penalty calibrated in cost-model bps                                                                                                                                  | A quant developer + a cost model + a backtest harness + a covariance shrinkage estimator. ~6+ months of focused FTE work     |
| Walk-forward + CPCV + 756d embargo + Deflated Sharpe + PBO — the López de Prado *Advances in Financial Machine Learning* canon, applied correctly                                                                                  | A second quant developer who has read the book and knows where it lies. ~3 months on top of the above                       |
| Almgren-Chriss square-root impact + IBKR Pro tiered commission + SEC §31 + FINRA TAF, calibrated weekly against realised fills                                                                                                     | An execution-trading desk. Not available to retail at any price                                                             |
| Survivorship-free, point-in-time fundamentals join (the `(report_date, as_of_date)` discipline in `01-research/04-data-fabric.md` §2.2)                                                                                            | A data engineer + a Bloomberg or FactSet license. USD 25k+/year minimum                                                     |

The amplification target is **a $50k–$1M retail account gets the same methodological rigor as a $50M institutional mandate, at $79–149/month** (`01-research/01-competitive-landscape.md` §6.2). That price differential is the entire commercial argument for the product.

### 2.4 The AAA stack as a wedge

| Layer    | Competitor that has it             | Competitor that has all three | Midas |
| -------- | ---------------------------------- | ----------------------------- | ----- |
| Automate | Wealthfront, Betterment, Schwab IP | None                          | Yes   |
| Augment  | Titan (narrative only, broadcast)  | None                          | Yes   |
| Amplify  | Composer (DIY only), Allocate Smartly (signals only) | None                          | Yes   |

No existing direct competitor stacks all three. The wedge is the stack itself, not any single layer.

---

## 3. Network-Effect Behaviors → Concrete Midas Features

The five behaviors (accessibility, engagement, personalisation, connection, collaboration) translate into concrete features. The honest grading: **v1 ships strong on accessibility, engagement, personalisation, connection — and deliberately ships zero collaboration**, deferring it to v3.

### 3.1 Accessibility — idea to execution latency

**Target**: a regime-flip notification → trade approved and in-flight at IBKR in **<90 seconds, fully on mobile**. This is the persona success measure from `01-research/05-uiux-design.md` §1.

Concrete features:

| Feature                                                          | Source                                |
| ---------------------------------------------------------------- | ------------------------------------- |
| Push notification on regime flip and pending approvals (APNS/FCM via Expo) | `01-research/05-uiux-design.md` §2.3, §5.3 |
| Single-screen approval card (instrument, size, cost, why-3-bullets, action bar — fits above the fold on mobile) | `01-research/05-uiux-design.md` §2.3, §3.1 |
| Biometric confirm (Face ID / Touch ID / passkey) — non-bypassable | `01-research/05-uiux-design.md` §3.3   |
| Bulk approve with per-item opt-out (no pre-checked "approve everything") | `01-research/05-uiux-design.md` §3.2  |
| Persistent "Ask Midas" entry point at the bottom of every screen — debate is always one tap away | `01-research/05-uiux-design.md` §2.2  |
| Idempotent server-side scheduler so a retry never double-publishes | `01-research/06-framework-architecture.md` §1 row 6 |

What is deliberately absent from accessibility: **swipe-to-execute without biometric, dopamine notifications, gamification**. Robinhood's pattern is rejected as actively harmful at this capital tier (`01-research/05-uiux-design.md` §3.4). Accessibility is measured in seconds-to-decision, not engagement-per-day.

### 3.2 Engagement — info that helps the user act

The engagement target is the **opposite of mass-market**: most days, the right action is to close the app. The dashboard's primary job is to give the user permission to do that (`01-research/05-uiux-design.md` §2.2).

Concrete features:

| Feature                                                                   | Why                                                                                                                                |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Regime chip as the second-most-prominent dashboard element                | The single best predictor of whether the user needs to do anything                                                                 |
| Benchmark comparison (vs 60/40) always visible, secondary                 | Trust signal: is Midas paying for itself net of cost?                                                                              |
| Per-trade cost breakdown (commission, half-spread, impact, gap risk)      | The brief §7 demand made tangible — every cost is shown inline at recommendation time                                              |
| Backtest explorer with multi-horizon grid (1y/3y/5y/10y × regime buckets) | Lets the user verify the strategy under stress windows they care about                                                             |
| Debate surface with grounding contract                                    | The augment loop — every claim cited, sycophancy guard, counter-scenario tool, confidence indicator per turn                       |
| Trade log + audit view                                                    | Immutable, content-hashed, exportable for taxes and (v2) regulatory exam                                                           |

What is deliberately absent: intraday charts on the home screen, social feeds, "your portfolio is up 2% today!" notifications, streaks, badges. Engagement is measured in **decisions made well**, not minutes-per-day.

### 3.3 Personalisation — within the impersonal-publisher constraint

This is the architectural tightrope. The server *must* be impersonal to preserve the publisher exemption (`01-research/03-broker-and-regulatory.md` §3.1, `01-research/06-framework-architecture.md` §6). But the user obviously has preferences. How is this reconciled?

**Personalisation lives client-side or in a quarantined server schema that never joins to signals.**

| Personalisation                                                           | Where it lives                                                                                          |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Which model portfolio(s) the user subscribes to                           | `subscriptions` table in the quarantined schema (PACT envelope B, `01-research/06-framework` §5.1)      |
| Notification cadence and approval thresholds (e.g. "auto-approve <2% of NAV") | `notification_prefs` table, quarantined schema                                                          |
| Auto-approve thresholds in $ and % of NAV                                 | Same                                                                                                    |
| Quiet hours                                                               | Same                                                                                                    |
| Dollar-delta calculation between current model portfolio weights and the user's actual IBKR balance | **Client-side**, against balances fetched directly from IBKR via OAuth — Midas server never sees balances |
| Tax-lot awareness, wash-sale avoidance                                    | **Deferred to v2** (requires server-side personalisation = RIA)                                         |
| Custom risk tolerance affecting which sleeves are eligible                | **Deferred to v2** for the same reason                                                                  |

The personalisation surface in v1 is therefore intentionally narrow. It is filter-and-route ("which signals do I want to see, when, and how"), not signal-mutate ("change the signal for me"). The architectural enforcement is at the Postgres role level: the publisher role has *NO SELECT* on `users.*`, so a developer cannot personalise the signal even by accident (`01-research/06-framework` §6.1).

### 3.4 Connection — what Midas is wired to

Connection is the strongest dimension in v1 because the brief locks in the partner stack and the architecture honours it.

| Partner          | Role                                                            | Source                                              |
| ---------------- | --------------------------------------------------------------- | --------------------------------------------------- |
| **IBKR**         | Custody + execution. v1 via OAuth (sandbox → production gated on regulatory standing) | `01-research/03-broker-and-regulatory.md` §1.5      |
| **EODHD**        | Primary global EOD + fundamentals + intraday + corporate actions | `01-research/04-data-fabric.md` §1.1                |
| **Yahoo (yfinance)** | Reconciliation/fallback; never sole source for a production decision | `01-research/04-data-fabric.md` §1.2                |
| **Perplexity**   | News and research grounding for the debate surface             | `01-research/04-data-fabric.md` §1.3                |
| **FRED**         | Macro series, credit spreads, yield curve — free and stable     | `01-research/04-data-fabric.md` §1.4                |
| **Apple/Google push** | APNS/FCM via Expo for approval notifications                | `01-research/05-uiux-design.md` §5.3                |
| **Stripe** (or equivalent) | Subscription billing — never inside IBKR (avoids inadvertent custody) | `01-research/03-broker-and-regulatory.md` §5.1      |
| **CBOE** (free EOD VIX) | VIX, VIX3M term structure for regime ensemble              | `01-research/02-strategy-methodology.md` §2.1       |

What is deliberately absent in v1: any second broker, any non-IBKR custodian, any community sharing, any social platform integration. The connection surface is **investing infrastructure only**, not lifestyle integration.

The shared data fabric (`01-research/04-data-fabric.md` §2) is the place where connection produces the platform's only true network effect: **EODHD is pulled once and serves every subscriber**. This is the bet documented in §1.4 of the data fabric doc — at 1000 users, EODHD is still ~$100/month total because the fabric is shared, while Perplexity scales per-user but cache hit rate rises with concurrency. The architecture compounds value as users are added without compounding cost linearly.

### 3.5 Collaboration — deliberately deferred

Collaboration in v1 is **zero**. There is no comment thread on a recommendation, no shared portfolio, no fork of someone else's strategy, no upvote, no follower count. This is not an oversight; it is a constraint.

| Collaboration feature  | Reason for v1 absence                                                                                                                               | Earliest version |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| Share-link to a debate | Requires a per-user identity model + content moderation. The user's brief did mention sharing with an accountant — flagged in `01-research/05` §9 Q1 | v2 (light)       |
| Comments on a signal   | Public comments on a published signal create an "investment community" the SEC would treat as a publication channel that may carry implicit advice  | v3               |
| Strategy fork / publish | Producer-side opening — see §1.3. Requires RIA or a vetted-author program                                                                          | v3               |
| Leaderboards            | Performance comparison creates marketing-rule liability and gamifies a domain that should not be gamified                                          | Never            |
| Social feed             | The brief's user is the contrast persona to Public.com. Social cruft is rejected as a persona-misalignment risk                                    | Never            |

The single small concession in v1 is that the trade log + debate transcript can be **exported** (CSV / PDF) for the user to share with their own accountant out-of-band. This is the export-not-share principle: the user is trusted to share data they own, the platform does not host the channel.

---

## 4. 80/15/5 Decomposition

The COC soft rule (80% reusable agnostic core / 15% client-specific self-service / 5% bespoke) maps onto Midas as follows. The mapping is meaningful here because the **80% is exactly what becomes the multi-tenant SaaS** when commercialisation begins, and the 15% is exactly the personalisation surface that lives client-side or in the quarantined schema.

### 4.1 The 80% — reusable, agnostic core

This is the platform. Identical for every subscriber. Everything in the publisher PACT envelope (`01-research/06-framework-architecture.md` §5.1).

| Component                                                  | Framework                                | Why agnostic                                                                                |
| ---------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------- |
| Data fabric — EODHD/Yahoo/Perplexity/FRED ingestion        | Core SDK workflows + DataFlow            | Same data serves every subscriber; pulled once, cached, reused                              |
| Postgres + Timescale + pgvector (single instance, single pool) | DataFlow                                 | One pool, one schema, RLS for the per-tenant subset                                         |
| Backtest engine                                            | Core SDK custom nodes                    | Strategy logic is the same code as live (the parity invariant)                              |
| Regime detection ensemble                                  | Core SDK + numeric only                  | Pure deterministic — no LLM in the decision path                                            |
| Adaptive Asset Allocation + HRP fallback                   | Core SDK custom node                     | Same allocator, same vol targets, same turnover penalty                                     |
| `TransactionCostNode`                                      | Core SDK custom node                     | Same IBKR fee schedule + Almgren-Chriss impact + half-spread for everyone                   |
| Signal broadcast API (`/v1/portfolios/{id}/signals/latest`) | Nexus                                    | Same bytes for every subscriber. CDN-cacheable. The legal tell                               |
| `DebateAgent` (Kaizen)                                     | Kaizen, LLM-first                        | Same agent, same signature, same tools. Per-user scope is in the conversation, not the code |
| Audit chain store                                          | DataFlow append-only + EATP-style hashes | Tamper-evident audit, identical schema for all                                              |
| Web shell, mobile shell, design system                     | Next.js, React Native, shared tokens     | Same UI for all                                                                             |

This 80% is **the SaaS product**. Build it once, run it for everyone. Cost scales with data volume and Perplexity calls, not with user count beyond the variable Perplexity line (`01-research/04-data-fabric.md` §6).

### 4.2 The 15% — client-specific self-service

This is what each user configures themselves through Settings, with no engineer involvement. Lives in the quarantined `users` schema or client-side state.

| Self-service surface                                                           | Where it lives                       |
| ------------------------------------------------------------------------------ | ------------------------------------ |
| Risk profile inputs (sleeve caps, max drawdown tolerance, concentration limits) | Quarantined `users` schema, applied client-side as a filter on the published signal |
| Approval thresholds ($ and % of NAV) and quiet hours                           | Same                                 |
| IBKR OAuth credentials                                                         | Encrypted, per-user, never shared    |
| Notification preferences (push, email, web)                                    | `notification_prefs`                 |
| Watchlist of sleeves the user wants extra alerts on                            | Same                                 |
| Subscription tier and billing                                                  | Stripe + `subscriptions`             |
| Debate transcript history (per-user, exportable, deletable)                    | Per-user, with audit retention disclosed |
| Paper-mode toggle                                                              | Per-user state                       |

Note that **none** of this 15% touches the signal generation. Risk profile is applied as a *display filter* — if the user has a 25% sleeve cap and the published portfolio has 30% in equities, the client surfaces a warning, but the signal is not mutated. This is what keeps the publisher posture intact.

### 4.3 The 5% — bespoke customisation

This is genuinely small in v1. Almost nothing is customised per user beyond the 15% above. The 5% corresponds to:

| Customisation                                                  | When it appears                                    |
| -------------------------------------------------------------- | -------------------------------------------------- |
| Custom regime thresholds (advanced users tuning VIX/OAS/correlation triggers behind an "I know what I'm doing" toggle) | Operator/Principal tier (`01-research/05-uiux-design.md` §7.2)                                     |
| Custom model portfolio definitions (the user defines their own sleeve list and the publisher runs it for them) | **v2 only**. Requires per-user signal generation = RIA |
| Proprietary signal adapters (a user wants to feed in their own factor)                                         | **v3**. Requires the producer-side opening           |
| Bespoke regime overlays (e.g. a user wants a custom drawdown gate)                                             | Operator/Principal tier as configuration; not as code |

The 5% is intentionally small in v1 because every bespoke surface is a potential personalisation footprint that pushes Midas out of the publisher posture. v2 expands the 5% only after the regulatory frame changes.

### 4.4 The 80/15/5 in autonomous-execution sessions

Per `rules/autonomous-execution.md`, effort estimates frame in autonomous sessions, not human-days. Rough order-of-magnitude (greenfield first session multiplier ~2-3x because institutional knowledge is being built, then drops):

| Layer                                  | Sessions to v1                                      |
| -------------------------------------- | --------------------------------------------------- |
| 80% core (data fabric, strategy engine, allocator, regime ensemble, cost model, signals API, debate agent, audit, web/mobile shells) | ~12-18 sessions in parallel agent teams             |
| 15% self-service (Settings, preferences, billing, paper mode, IBKR OAuth flow) | ~2-3 sessions                                       |
| 5% bespoke (operator/principal-tier knobs)                                      | ~1 session                                          |
| **v1 total**                           | **~15-22 sessions** (calendar dependent on parallelism, not headcount) |

This is roughly the equivalent of a "9-12 month, 4-engineer team" estimate divided by the 10x multiplier — i.e. ~3-5 calendar weeks of focused autonomous execution with the agent teams working in parallel. The structural gates (briefs approval, /todos approval, /release authorisation) are calendar-bound and may extend this; the execution itself is not.

---

## 5. Commercialisation Pivot

The user's brief says *"consider commercializing it"*. The honest answer is that **Midas is born commercialisable on the architecture but constrained on the regulatory plane**, and the pivot is best understood as three sequential gates rather than a single jump.

### 5.1 The pivot is regulatory, not technical

The architecture in `01-research/06-framework-architecture.md` is already multi-tenant. There is no day-one rewrite required to go from "Takahide as the sole user" to "Takahide + 50 paying subscribers" — the data fabric is shared by design, the publisher endpoint is CDN-cacheable, the per-user state is already in a quarantined schema with PACT envelope separation. **What changes between personal-Midas and SaaS-Midas is everything except the strategy and data layer.**

| Layer                          | Personal-use (1 user)                                              | v1 SaaS (publisher, ≤1k users)                                                                                              | v2 SaaS (RIA discretionary)                                                                                |
| ------------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Data fabric                    | Same                                                               | Same                                                                                                                        | Same                                                                                                       |
| Strategy engine                | Same                                                               | Same                                                                                                                        | Same                                                                                                       |
| Per-user IBKR credentials      | One set, in `.env`                                                 | OAuth flow per user; encrypted at rest; scoped to trading + read, no money-movement                                          | Same + IBKR Advisor master account structure                                                               |
| Per-user strategy encryption   | N/A                                                                | N/A in v1 (same model portfolio for all)                                                                                    | Per-user customisation possible; encryption for proprietary overlays                                       |
| Billing                        | None                                                               | Stripe; tiered (Observer/Operator/Principal per `01-research/05` §7.2)                                                      | Same + AUM-based fee option                                                                                |
| Identity / auth                | Single user                                                        | Email + passkey/WebAuthn; multi-factor for execution                                                                        | Same + KYC vendor + OFAC/sanctions screening                                                                |
| Regulatory licensing           | None (personal use)                                                | None in US under publisher posture; geofence UK/SG/EU                                                                       | RIA registration (~3-9 months, USD 15-50k); FCA/MAS licences for non-US                                    |
| Audit trail                    | Local logs                                                         | DataFlow append-only + content hashes + EATP-style chain (recommended); 7-year retention                                    | Same + SEC exam-ready exports + SOC 2 Type II                                                              |
| Customer support               | None                                                               | Email/Intercom; ~1 FTE-equivalent for 500-1000 users                                                                        | Same + compliance officer on call                                                                          |
| Disclosures                    | None                                                               | "Signal-only, not personalised advice" on every screen + landing page; ToS + Privacy + Risk Disclosure                      | Form ADV Parts 1, 2A, 2B, 3 (CRS); ongoing                                                                 |
| Insurance                      | None                                                               | E&O optional but recommended                                                                                                | E&O required (~USD 5-15k/year); cyber recommended                                                          |
| SOC 2                          | N/A                                                                | Not required, but Type I is a useful trust signal at ~USD 30k                                                               | Type II expected (~USD 50-100k initial + ~USD 30k/year)                                                    |
| Geofencing                     | N/A                                                                | UK + SG + EU blocked at signup (IP + ToS + KYC questionnaire); US-only initially                                             | Per jurisdiction as licences are obtained                                                                  |
| Cross-account / household view | N/A                                                                | Deferred to Principal tier in v2                                                                                            | Available                                                                                                  |
| Tax-aware recommendations      | N/A                                                                | Forbidden (would breach publisher posture)                                                                                  | Available                                                                                                  |

### 5.2 The pivot points, named

There are three:

1. **Pivot 1 — personal → v1 SaaS publisher**. Triggered by: any non-Takahide user wanting paid access. What changes: billing, OAuth-per-user, identity, disclosures, geofencing, support. **Not** changing: the strategy code, the data fabric, the publisher endpoint shape, the debate agent. **Effort**: ~3-5 sessions on top of personal-Midas. **Regulatory blocker**: none in US under publisher posture; geofence everything else.

2. **Pivot 2 — v1 SaaS → v2 RIA discretionary**. Triggered by: enough subscribers wanting "just trade for me" that the publisher friction becomes a churn driver, AND the live track record exists to defend RIA marketing claims. What changes: RIA registration, IBKR Advisor master account, per-user signal personalisation becomes legal, tax-awareness becomes legal, multi-account/household becomes legal, marketing rule compliance becomes binding (this should already be designed in per `01-research/03-broker-and-regulatory.md` §4). **Regulatory blocker**: state RIA (3-6 months) or SEC RIA (4-9 months) plus E&O insurance plus a compliance officer plus ongoing form ADV updates. **Effort**: ~4-6 sessions of code changes + ~6 months of legal/regulatory parallel track.

3. **Pivot 3 — v2 → v3 community / multi-publisher**. Triggered by: a deliberate strategic decision to become a marketplace rather than a single-publisher RIA. What changes: vetted author program, IAR sub-adviser arrangements, performance-track-record gates, content moderation, revenue share, escrow for strategy IP, per-strategy backtest publication infrastructure to SEC marketing rule spec. **Regulatory blocker**: significantly heavier than v2 — Midas becomes a platform that hosts third-party advisers, which is a regulated activity in itself. **Effort**: substantial; not before v1 has 12+ months of live telemetry and v2 has been operating for at least a year.

### 5.3 The "born multi-tenant" verdict

The user asked the right question slightly wrong. The question is not *"when do I commercialise?"* — the answer is "the architecture is commercialisable from day one because the data fabric is shared and the publisher endpoint is impersonal". The question is *"when am I willing to take on the regulatory weight of letting other people use this?"* — and that answer has three thresholds:

- **Pivot 1 today**: take payment from US-resident HNW users, sell access to a model portfolio + the debate surface + the backtest explorer, never see their balances, never personalise their signals. Legal, light, the 80/15/5 architecture supports it.
- **Pivot 2 in ~6-12 months**: register as an RIA, take discretionary trading authority, personalise per user. Heavier, but unlocks the bigger market.
- **Pivot 3 not before year 2**: open to community publishers. Highest leverage but also highest regulatory burden.

**Recommendation**: build to v1 SaaS publisher *now*, gate-by-gate, with the schema and architecture already shaped for v2. Do not skip the publisher posture — it is the fastest legal path to revenue, it disciplines the architecture in ways that make v2 cheaper, and it lets the live calibration loop on the cost model and the live track record on the strategy accumulate the evidence v2 needs.

### 5.4 What must not be done in v1 to keep v2 cheap

A few "future taxes" that v1 should pre-pay even though they aren't strictly required:

| Pre-pay in v1                                                              | Reason                                                                                                                  |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Build backtest reporting to SEC Marketing Rule spec (net-of-fee, standardised time periods, hypothetical disclaimers) | `01-research/03-broker-and-regulatory.md` §4 — binds the moment Midas registers; nothing to retrofit                    |
| Make the no-custody invariant a project rule that fails the build if any code path takes IBKR money-movement scope   | `01-research/03-broker-and-regulatory.md` §5.1 — single biggest compliance simplification                                |
| Audit log with content hashes from day one                                                                          | SEC exam readiness; cheap now, expensive to backfill                                                                    |
| PACT envelope split between publisher and client-personalisation roles                                              | The schema and role grants ARE the publisher posture; deferring this means an emergency rewrite when the first state RIA exam happens |
| Geofence UK/SG/EU at signup                                                                                         | A single non-US user under v1 is a regulatory incident; the geofence is cheap                                           |
| Backtest ↔ live parity enforced structurally (one node graph)                                                       | The single biggest credibility risk is backtest-to-live decay; the parity is cheap if architected, expensive if retrofit |

---

## 6. Cross-References

- `briefs/01-user-brief.md` — *"common database for all users"*, *"commercializable as a product"*
- `briefs/02-assumptions.md` — A1 (capital tier $50k–$1M), A2 (v1 signal-only, v2 RIA path)
- `01-analysis/01-research/01-competitive-landscape.md` §6 — target user, $79–149/mo SaaS pricing, no competitor stacks all four (regime + multi-asset rotation + backtest transparency + debate AI + IBKR-native)
- `01-analysis/01-research/02-strategy-methodology.md` §2.9, §3, §4, §5 — regime ensemble, AAA allocator, multi-horizon, cost model
- `01-analysis/01-research/03-broker-and-regulatory.md` §1.5 (IBKR OAuth), §3.1 (US Lowe publisher posture), §4 (Marketing Rule), §5.1 (no custody invariant)
- `01-analysis/01-research/04-data-fabric.md` §2 (single-engine Postgres + DataFlow), §6 (per-user cost shape that enables the shared-fabric bet)
- `01-analysis/01-research/05-uiux-design.md` §1 (Alex persona), §2.3 (approval card), §2.4 (debate surface), §3 (decision-to-execution patterns), §7.2 (tier structure)
- `01-analysis/01-research/06-framework-architecture.md` §1 (component → framework mapping), §2 (LLM-first DebateAgent), §3 (backtest↔live parity), §5 (PACT envelopes), §6 (impersonal publisher)

---

## 7. Open Questions for the Gate

1. **Does the user want v1 to be paying-customer-ready, or personal-only with a "switch the lights on" pivot later?** The architecture is the same either way; the difference is whether to do Pivot 1 in the same session train as personal-Midas or as a separate later effort.
2. **Is geofencing UK/SG/EU acceptable at v1 launch?** The brief did not specify residency. Global day-one launch turns v1 into v2 (licensing track) and adds 6+ months.
3. **Is the publisher posture (impersonal model portfolios on the server, personalisation client-side only) acceptable as a constraint, or does the user want personalised advice from day one?** Personalised v1 = state RIA, ~3-6 months delay.
4. **Should v3 (community/marketplace) be on the roadmap at all, or is Midas a single-publisher product forever?** This affects how much investment goes into vetted-author primitives, content moderation hooks, and revenue-share infrastructure now vs never.
5. **Does the user want the Operator/Principal tier customisation surface (custom regime thresholds, multi-account view) as a v1 feature or a v2 feature?** Building it in v1 is cheap on the architecture but adds ~1-2 sessions of UI surface.
