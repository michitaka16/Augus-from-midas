# Competitive Landscape — Midas Platform

**Workspace**: `midas-platform`
**Phase**: 01-analysis / 01-research
**Date**: 2026-04-09

> **Sourcing note**: WebSearch and WebFetch were unavailable in this research session. All figures below are drawn from the author's training data (accurate through mid-2025) and publicly-known product positioning. **Fees, minimums, and feature flags must be re-verified by a human at the analysis gate** before any of them become assumptions in downstream phases (`02-plans/`, costing models, or pricing decisions). Items flagged `[VERIFY]` are the highest-priority checks.

---

## 1. Direct Competitors — Delegated Portfolio Managers

These products all pitch "we manage a diversified portfolio for you." They are the closest thing to Midas in intent, but the brief's requirements (8 sleeves, regime-aware freeze, debate-with-AI, multi-horizon backtest transparency) are mostly absent from this category.

### 1.1 Wealthfront

- **Positioning**: Largest pure-play automated investing platform in the US. "Set it and forget it" for tech-savvy millennials; strong on tax automation.
- **Fee model**: 0.25% AUM, no trading commissions, $500 minimum. Cash product at separate APY. [VERIFY: fee schedule may have shifted in 2025–26.] [^1]
- **Asset classes**: US stocks, foreign developed, emerging markets, dividend stocks, TIPS, municipal bonds, corporate bonds, natural resources, real estate. ~11 ETF sleeves depending on risk score.
- **Rebalancing logic**: Threshold-based drift rebalancing (rebalance when any sleeve drifts past a band, typically 5%). No regime awareness. Runs continuously in the background.
- **Regime awareness**: **None published.** Portfolio glidepath is static for a given risk score.
- **UX strengths**: Path (goals-based planner), Autopilot (cash sweep), direct-indexing for taxable accounts above $100k.
- **UX gaps**: No "why did you do this today" explainability. No conversational layer. Backtests not exposed to user.
- **Regulatory**: SEC-registered RIA; Wealthfront Brokerage LLC member FINRA/SIPC.

### 1.2 Betterment

- **Positioning**: Original US robo-advisor, now diversified into 401(k) and cash. Positions itself on goals + guidance.
- **Fee model**: 0.25% for Digital; ~0.40% for Premium (adds CFP access), typically $100k minimum for Premium. [VERIFY]
- **Asset classes**: Similar ~12-ETF globally-diversified stock/bond sleeves; strategies include Core, Socially Responsible, Goldman Sachs Smart Beta, BlackRock Target Income, Innovative Technology.
- **Rebalancing**: Drift-based plus cash-flow rebalancing (new deposits used to buy the underweight sleeve, minimizing taxable sells).
- **Regime awareness**: **None.** Strategies are static allocations; no freeze logic.
- **UX strengths**: Tax-coordinated portfolio across taxable/tax-deferred. Goal-based UI.
- **UX gaps**: Strategy selection is a menu pick, not a dialogue. No backtest display. No debate capability.
- **Regulatory**: SEC RIA; Betterment Securities broker-dealer.

### 1.3 M1 Finance

- **Positioning**: "Pie"-based self-directed investing + optional borrow/spend. Target user: DIY investor who wants automation wrappers around their own picks.
- **Fee model**: Free tier, M1 Plus at ~$3/mo (moved from $125/yr). No AUM fee — M1 monetizes via PFOF, margin spread, and cash interest. [VERIFY — M1's pricing has changed 3+ times since 2022.]
- **Asset classes**: Whatever the user selects — stocks, ETFs, crypto. M1 does not recommend; user designs the Pie.
- **Rebalancing**: "Dynamic rebalancing" on new deposits/withdrawals, plus one-click manual rebalance. No automatic drift rebalancing unless on Plus.
- **Regime awareness**: **None — not the product's job**; user is the allocator.
- **UX strengths**: Pie visual is iconic. Fractional shares.
- **UX gaps**: No advice, no backtest, no regime logic — this is automation, not intelligence.
- **Regulatory**: M1 Finance LLC, SEC RIA + broker-dealer.

### 1.4 Composer.trade

- **Positioning**: **The closest competitor to Midas by a significant margin.** "No-code quant" — build conditional trading strategies ("Symphonies") with branching logic, backtest them, run them live.
- **Fee model**: Freemium; paid plans roughly $20–80/mo depending on tier. Backed by Alpaca for execution.[^2]
- **Asset classes**: US-listed ETFs and stocks primarily. Crypto limited.
- **Rebalancing**: **Symphony-defined.** Users can wire conditions like "if SPY 200-day trend down, move to gold + bonds." This is genuinely regime-aware at the *user's* specification.
- **Regime awareness**: **Yes, but delegated to the user.** Composer does not ship a packaged regime model; it gives you the primitives to build one.
- **UX strengths**: Visual strategy builder, inline backtests per Symphony, community-shared strategies.
- **UX gaps**: **Requires quant literacy.** A buy-side discretionary user who wants delegation will bounce off the Symphony builder. No "debate with AI" layer. Backtest explanations are numeric, not narrative.
- **Regulatory**: Composer is RIA; Alpaca is the broker-dealer.

### 1.5 Interactive Advisors (IBKR's own robo)

- **Positioning**: IBKR's in-house managed portfolio arm. Pitched inside the IBKR account ecosystem.
- **Fee model**: 0.08%–1.5% AUM depending on portfolio (smart beta, ESG, wealth-manager-run models). Low minimums ($100–$5,000). [VERIFY]
- **Asset classes**: Multi-asset ETF portfolios, some active wealth-manager-run models.
- **Rebalancing**: Model-driven, quarterly or drift-based depending on portfolio.
- **Regime awareness**: None published at product level.
- **UX strengths**: Native integration with IBKR account — **this is directly relevant to Midas** since the brief requires IBKR. A user asking "why not just use Interactive Advisors?" is the sharpest challenge the product faces.
- **UX gaps**: Traditional model-portfolio UX, no conversational layer, no regime freeze.
- **Regulatory**: Interactive Brokers Corp is SEC RIA.

### 1.6 Titan

- **Positioning**: "Actively managed for everyone" — hedge-fund aesthetic, narrated quarterly updates, higher-fee active equity and alternatives.
- **Fee model**: Flat fee tiers (around $5/mo up to ~1% depending on account size and product). Offers access to alts (private credit, VC feeders). [VERIFY]
- **Asset classes**: Active equity (Flagship US, Opportunities, International), crypto, alts.
- **Rebalancing**: Discretionary by Titan's investment team.
- **Regime awareness**: Discretionary commentary, not algorithmic.
- **UX strengths**: Best-in-class narrative layer — in-app video explainers from PMs after major moves. **This is the closest analogue to Midas's "debate with AI" in existing products.**
- **UX gaps**: Human PM bottleneck; no self-directed customization; no backtests.
- **Regulatory**: Titan Global Capital Management is SEC RIA.

### 1.7 Frec

- **Positioning**: Direct-indexing at low minimums; tax-loss harvesting on custom indices.
- **Fee model**: 0.10% for direct-index products. [VERIFY]
- **Asset classes**: Direct-indexed US equity baskets; cash.
- **Rebalancing**: Tax-loss-aware drift rebalance on underlying constituents.
- **Regime awareness**: None.
- **Relevance to Midas**: Orthogonal — Frec is a tax-optimization play, not a multi-asset rotation play. Useful only as a reference for how a v2 taxable-account Midas could bolt on TLH.

### 1.8 Public.com Premium

- **Positioning**: Social brokerage with a premium tier offering analyst reports, fixed income, and some AI features.
- **Fee model**: $10/mo for Premium; trading is free (PFOF). [VERIFY]
- **Asset classes**: Stocks, ETFs, crypto, Treasuries, some alts.
- **Rebalancing / management**: Self-directed; Public does not run portfolios.
- **Regime awareness**: None; it's a brokerage, not an advisor.
- **Relevance**: A distant competitor — Public is a lifestyle brokerage, Midas is a delegated manager.

### 1.9 Schwab Intelligent Portfolios

- **Positioning**: Schwab's zero-management-fee robo (monetized via cash drag and fund expense ratios on Schwab ETFs).
- **Fee model**: $0 AUM management; $5,000 minimum. Premium tier (~$30/mo + $300 one-time) adds CFP. [VERIFY]
- **Asset classes**: 20+ ETF sleeves across equity, fixed income, commodities, cash.
- **Rebalancing**: Drift-based, tax-aware.
- **Regime awareness**: **None.** Portfolio allocations are static by risk score.
- **UX strengths**: Free; trusted brand; broad sleeve coverage.
- **UX gaps**: Mandatory cash allocation (typically 6–10%) is the hidden cost and has drawn criticism. No narrative, no backtest, no regime freeze.
- **Regulatory**: Charles Schwab Investment Advisory is SEC RIA.

### 1.10 Summary matrix — direct competitors

| Product | Fee | Multi-asset (≥6 sleeves) | Regime-aware | Backtest to user | AI/debate layer | IBKR-compatible |
|---|---|---|---|---|---|---|
| Wealthfront | 0.25% | Yes (~11) | No | No | No | No (own custody) |
| Betterment | 0.25–0.40% | Yes (~12) | No | No | No | No |
| M1 Finance | $0 / $3 mo | User-defined | No | No | No | No |
| Composer.trade | $20–80/mo | User-defined | **User-built** | **Yes (per strategy)** | No | No (Alpaca) |
| Interactive Advisors | 0.08–1.5% | Yes | No | No | No | **Native** |
| Titan | $5/mo–~1% | Partial (mostly equity) | Discretionary narrative | No | Narrative video | No |
| Frec | 0.10% | No (equity only) | No | No | No | No |
| Public Premium | $10/mo | Self-directed | No | No | Some | No |
| Schwab Intel. Portf. | $0 (cash drag) | Yes (20+) | No | No | No | No |
| **Midas (target)** | **TBD** | **Yes (8)** | **Yes** | **Yes** | **Yes** | **Yes** |

**Reading**: No existing direct competitor combines all four of (regime awareness, multi-asset rotation, backtest transparency, conversational AI layer) on top of IBKR. Composer is closest but requires quant literacy. Titan has narrative but is discretionary-human. Interactive Advisors has IBKR integration but is a conventional static-model robo.

---

## 2. Adjacent Tools — DIY Quant

These target a different user (the quant hobbyist or advisor building strategies), but Midas borrows concepts from them and must explain clearly how it is *not* one of them.

### 2.1 Portfolio Visualizer

- **What**: Web tool for backtest, Monte Carlo, factor regression, asset allocation. Freemium.
- **User**: Advisors and retail DIY quants.
- **Relevance to Midas**: The **gold standard** for showing backtest output in a retail-comprehensible way. Midas should borrow its equity curve + drawdown + rolling-returns chart conventions (Section 5.3).
- **Gap**: No live execution. Pure research.

### 2.2 QuantConnect

- **What**: Cloud-hosted algo research + paper/live trading platform. Python/C#.
- **User**: Coding quants, small funds.
- **Relevance**: Midas is *not* this. QuantConnect demands a quant developer; Midas targets a delegator.

### 2.3 Allocate Smartly

- **What**: Tracks 60+ published tactical asset allocation (TAA) strategies (Dual Momentum, Permanent Portfolio, Ivy, Adaptive Asset Allocation, etc.) with live signals.
- **User**: Self-directed TAA practitioner.
- **Relevance**: **High.** Midas's 8-sleeve rotation logic is essentially a tactical asset allocation, and Allocate Smartly has built the subscription playbook for this space ($35–50/mo). Their strength: published academic strategies with transparent rules. Their gap: signal-only; no execution; no regime freeze; no AI explainer.

### 2.4 TrendXplorer

- **What**: Research blog and model portfolio site on trend-following and momentum TAA.
- **Relevance**: Content marketing inspiration. Not a product.

### 2.5 Composer (as DIY)

Already covered in §1.4. Composer spans both categories — a DIY-quant tool monetized as a delegated-execution SaaS.

---

## 3. Signal / Research SaaS

### 3.1 SigFig

Originally a portfolio tracker, pivoted to white-label wealth tech for banks. No longer a direct retail competitor — worth noting only because it demonstrates the "signal-only pivot to B2B" escape hatch if Midas retail economics fail.

### 3.2 Kwanti

Portfolio analytics for financial advisors. Strong on factor analysis, stress testing, proposal generation. B2B, not a Midas competitor, but a reference for stress-test UI patterns the brief demands (§6 Risk Management, §7 Cost Modeling).

### 3.3 RocketDollar

Self-directed IRA custody for alternatives. Mis-grouped here — not a signal SaaS. Irrelevant to Midas.

---

## 4. IBKR Native Tools — The "Free Already" Challenge

IBKR is the brief's chosen broker, so any feature IBKR already provides for free is a feature Midas must *outclass*, not replicate.

### 4.1 PortfolioAnalyst

- Free with any IBKR account.
- **Provides**: Attribution, risk metrics (beta, Sharpe, drawdown, VaR), benchmark comparison, rolling returns, factor exposures, tax reports.
- **Does not provide**: Forward-looking regime detection, rebalance recommendations, backtests of *alternative* allocations, execution automation, narrative explanation.

### 4.2 TWS (Trader Workstation)

- Free; professional-grade execution UI.
- **Provides**: Every order type, algo execution, scanner, option chains, basket trader.
- **Does not provide**: Any advisory logic. TWS is a cockpit, not an autopilot.

### 4.3 Implication for Midas

IBKR already solves **execution, attribution, and risk measurement for free**. Midas cannot charge for those. Midas must charge for the three things IBKR deliberately does not build: **(a) portfolio design under regime awareness, (b) the backtest-validated rotation strategy itself, (c) the conversational explainability layer.** Section 5 turns these into the USP list.

---

## 5. Gaps and USPs for Midas

### 5.1 Regime-Aware Freeze-and-Ask

**The gap**: Every direct competitor in §1 either (a) runs a static-allocation model that does nothing differently in turbulence, or (b) requires the user to hand-code regime logic (Composer). **None of them freeze automation and ask for explicit consent when the ensemble flips to "turbulent."** This directly maps to the brief §2 ("Turbulent markets: don't trade without my permission") and is probably the single feature the user would notice first in a side-by-side demo.

### 5.2 Debate-with-AI Conversational Layer

**The gap**: Titan has narrative (quarterly PM videos) and that's the entire competitive set. No robo allows the user to say "why gold this week? show me the regression" and get an auditable answer tied to the live signal stack. The brief §8 explicitly calls this out. Kaizen / signature-based agents can make this concrete: the LLM reasons over the signal pack, explains in plain language, and cites the numbers — without doing any routing or decisions itself (see `rules/agent-reasoning.md`).

### 5.3 Multi-Horizon Backtest Transparency Exposed to End User

**The gap**: No delegated-manager product in §1 shows the user the backtest. Portfolio Visualizer shows backtests but does not execute. Composer shows per-strategy backtests but only if you built the strategy. Midas's brief §6 demands walk-forward, purged k-fold, and multiple rolling windows (1y, 3y, 5y, 10y) *exposed to the user*. This is a trust-builder that no delegated product offers.

### 5.4 Realistic Cost Modeling in the UI

**The gap**: Every competitor abstracts cost to "0.25% AUM, no commissions." They do not show the user slippage, spread, price impact, or gap risk inline at recommendation time. Brief §7 is explicit. This is hard to fake — implementing it well requires the IBKR SMART cost model plus an impact model (e.g., Almgren–Chriss-style square-root), and very few retail products do it.

### 5.5 8-Sleeve Multi-Asset Rotation

**The gap**: Wealthfront / Betterment / Schwab use 10–20 ETF sleeves *statically*. Composer users *can* build rotation but typically across 2–4 tickers. None ship a **pre-built, backtested, regime-aware rotation across the exact 8 sleeves in the brief**: broad equity, precious metals, gov bonds (all durations), corporate IG, REITs, commodities, dividend, emerging markets. This is Midas's packaged product.

### 5.6 IBKR-Native Execution with Advisory Overlay

**The gap**: Interactive Advisors is IBKR-native but static. Every other §1 competitor forces a custody move. Midas stays in IBKR — user keeps their account, tax lots, margin, reporting — and layers advice on top. Reduced switching cost is a significant wedge for the HNW user who already has an IBKR account.

---

## 6. Market-Fit Critique

### 6.1 Who Is the Target User?

The brief's user is **self-directed HNW ($50k–$1M, per A1) who wants delegation but not full discretion**. This is a well-defined but underserved niche:

- **Not** the Wealthfront/Betterment user (they want full delegation and don't care about methodology).
- **Not** the QuantConnect/Composer user (they want to build it themselves).
- **Not** the Titan user (willing to trust a human PM's judgment without seeing the math).
- **Yes** the IBKR-power-user who reads Allocate Smartly, runs their own Portfolio Visualizer backtests, and wishes there were a product that did it for them *while leaving them as the final approver*.

This user population is real but narrow. Empirically it's the overlap of: (a) IBKR account holders (~2.5M globally as of 2024, skewing HNW and global), (b) people who read investment research blogs, (c) people who are not themselves quant coders. A rough TAM estimate: **50k–250k addressable users globally.** This supports a premium SaaS, not a mass-market robo.

### 6.2 Is There Room?

Yes, but the room is shaped like a **premium subscription, not a % AUM robo**. Reasoning:

- At 0.25% AUM on $50k–$1M, revenue is $125–$2,500/user/yr. But Midas's v1 is *signal-only* (A2) — the user executes trades. Charging AUM on assets you do not custody is legally awkward and operationally weak.
- At $50–200/mo SaaS (Composer / Allocate Smartly range), revenue is $600–$2,400/user/yr — comparable to mid-fee AUM — with cleaner regulatory posture (software subscription, not investment management).
- **Feasible price point: $79–149/mo**, with a research/backtest-only tier at $29–49/mo for funnel. This matches the brief's "go big or go home" user's willingness to pay for an edge and is defensible vs. the Allocate Smartly anchor.

### 6.3 Risks to Product-Market Fit

1. **The "why not Interactive Advisors" question.** IBKR's own robo exists, is cheap, and is already trusted by the target user. Midas must demonstrate clearly (in the landing page, not just in docs) the three things it does that Interactive Advisors does not: regime freeze, backtest transparency, debate AI.
2. **Regulatory migration trap.** Signal-only (v1) is legal and ships fast, but every pricing pressure pushes toward v2 (discretionary / RIA). The moment a user says "just trade for me automatically," Midas is in RIA territory. The roadmap must be honest about this (A2 already is).
3. **Backtest-to-live decay.** Every TAA product in §2.3 (Allocate Smartly's tracked strategies) shows the same pattern: strategies that backtest beautifully degrade in live performance. Midas's credibility collapses the first time the live track record visibly diverges from the published backtest. This is why the freeze-and-ask logic is *also* a reputation-protection feature, not only a user-experience feature.
4. **The user-as-executor friction.** Signal-only means the user clicks "approve" on every trade. If rebalance cadence is weekly and there are 3–5 trades per rebalance, that's 15–20 clicks per month. At turbulent regimes (freeze + per-trade approval) it gets heavier. The UX for "approve all / approve individually / reject" has to be surgical or users churn.

### 6.4 Verdict

There is a real, defensible wedge. It is **not** a mass-market robo — it is a **premium decision-support SaaS for the IBKR self-directed HNW user who wants a regime-aware rotation manager and wants to see the math**. The combination of regime freeze + backtest transparency + debate-AI is not assembled anywhere else, and the IBKR-native posture removes the single biggest objection (switching custodians). Pricing should anchor to a SaaS subscription in the $79–149/mo range, not AUM. Regulatory posture must stay signal-only in v1 with a deliberate RIA path for v2 if user demand for automation dominates.

---

## Footnotes / Sources

> All items below should be re-verified by a human before downstream phases consume them. WebSearch/WebFetch were unavailable during this research pass.

[^1]: Wealthfront fee schedule and portfolio construction: author's training data current through mid-2025; see wealthfront.com/investing and wealthfront.com/methodology whitepaper for authoritative current values. [VERIFY]
[^2]: Composer.trade product and pricing: author's training data current through mid-2025; composer.trade/pricing for current tiers. Alpaca Securities LLC is the broker-dealer of record for Composer strategies. [VERIFY]

### Verification queue for analysis gate

1. Wealthfront current fee, minimum, and sleeve count.
2. Betterment Digital vs Premium fees and current Premium minimum.
3. M1 Plus current price (has changed repeatedly).
4. Composer.trade pricing tiers and any 2025–26 product changes.
5. Interactive Advisors fee range by portfolio family and current minimums.
6. Titan current fee schedule (flat-fee vs AUM threshold).
7. Frec direct-indexing fee and asset coverage.
8. Schwab Intelligent Portfolios cash allocation range (the hidden-cost argument).
9. Allocate Smartly current subscription price — anchors Midas SaaS pricing.
10. IBKR PortfolioAnalyst current feature list — confirms the "already free" baseline.
