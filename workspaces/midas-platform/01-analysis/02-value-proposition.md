# Value Proposition & Unique Selling Points — Midas Platform

**Workspace**: `midas-platform`
**Phase**: 01-analysis, step 3.1
**Date**: 2026-04-09
**Method**: Critical synthesis of briefs + competitive landscape + strategy + regulatory research. Scrutinized against the question "is this actually unique, or does Composer/Wealthfront/Interactive Advisors already ship it?"

---

## 1. Target Buyer Profile

### The buyer

The **IBKR-holding self-directed HNW investor with $50k–$1M in liquid assets** who has already outgrown both ends of the market:

- They **tried a robo** (Wealthfront, Betterment, Schwab Intelligent Portfolios) and found it too passive. A static 60/40 sleeve that ignores 2022's stock-bond correlation flip taught them that "set and forget" is an abdication, not a strategy.
- They **priced an RIA** at 1% AUM and refused to pay $5k–$10k/year to someone who rebalances quarterly and sends a PDF.
- They **read Allocate Smartly, Portfolio Visualizer, and the tactical asset allocation literature**. They know what momentum, trend filters, and vol targeting are. They are not intimidated by the word "Sharpe."
- They are **not quant coders**. They bounced off QuantConnect and found Composer's Symphony builder closer but still a weekend project.
- They keep their assets at **IBKR** because they want global markets, margin, real execution, and tax-lot control.

Concretely: a 35–55 year old who earns $200k–$500k, has a taxable brokerage plus a rollover IRA at IBKR, trades themselves during the week, and on Sunday night wishes there were "a thing that did what I would do if I had 40 hours to do it."

### Who does NOT buy

- **The "set and forget" millennial with $20k in a Roth.** They are a Wealthfront customer forever. Midas is overkill and overpriced.
- **The $10M+ client.** They want a human RIA and a tax attorney. Midas doesn't displace that relationship.
- **The Composer power user who already builds Symphonies.** They don't need packaged strategies; they want primitives.
- **The discretionary trader who runs their own screens.** They trust their own signal and see Midas as a crutch.
- **Anyone not on IBKR.** Custody migration friction kills the sale; Midas's IBKR-native wedge only works for people already there.

### Sizing check

Per landscape §6.1: ~2.5M IBKR accounts globally, skewed HNW and international. The addressable overlap — IBKR holder + reads investment blogs + not a quant coder + $50k–$1M tier — is roughly **50k–250k users globally**. This is a premium SaaS TAM, not a mass-market one. At $79–149/mo and 5–10% penetration, that's a $25M–$225M annual revenue ceiling. Enough to build a real business; nowhere near enough to justify a robo-style growth-marketing playbook.

---

## 2. Core Value Propositions

Each claim is anchored in the buyer's stated pain, not in what the product can technically do.

### VP1. "You stop trading before the crash, not after it."

**Claim**: Midas freezes auto-rebalance and asks your permission the moment its regime ensemble flips to turbulent — before you're down 20%, not after.

**Why it matters**: Every robo the buyer tried kept mechanically rebalancing into the drawdown in 2022. Their own backtests tell them the difference between "-35% drawdown" and "-12% drawdown" is worth far more than 50 bps of fees. A regime gate that catches 2 out of 3 major drawdowns is worth five years of Wealthfront's 0.25% fee.

**Mechanism**: Weighted ensemble of HY OAS (credit stress), VIX3M backwardation (vol term structure), cross-sector PC1 variance (correlation breakdown), trend filter, realized vol, and a hard drawdown kill-switch at -8% / -12% (methodology §2.9). When it trips, auto-execution halts and every trade requires explicit user approval.

**Quantified**: Historically, VIX3M backwardation and HY OAS > 700 bps have preceded most >15% S&P drawdowns since 2005 with a few weeks' lead. If the gate cuts one -25% drawdown to -10% over a decade, that's ~1,500 bps of preserved capital on the equity sleeve — roughly 10 years of a 0.25% robo fee saved in a single event.

### VP2. "Every recommendation comes with the backtest that earned your trust."

**Claim**: Before you click execute, Midas shows you what this exact rotation would have done in 2008, 2020, 2022, and 2023 — walk-forward, purged, and stress-tested per crisis.

**Why it matters**: The buyer has been burned by "trust us" advisors and by backtests that collapsed live. They will not approve a trade they cannot audit. No robo shows a backtest. Portfolio Visualizer shows backtests but cannot execute.

**Mechanism**: Walk-forward with expanding-window retraining, combinatorial purged cross-validation, 756-day embargo, point-in-time regime data, per-crisis stress windows, Deflated Sharpe Ratio, Probability of Backtest Overfitting (methodology §6). Reported as a distribution, not a point estimate.

**Quantified**: Time-to-trust collapses from weeks (manual Portfolio Visualizer + spreadsheet) to minutes (inline per-trade). For a Sunday-night investor, this is 2–4 hours of weekly work eliminated — roughly 150 hours/year.

### VP3. "Ask why. Get an answer that cites the numbers."

**Claim**: Click any recommendation and ask "why gold this week and not TLT?" Midas replies in plain language, citing the exact signal values that drove the decision.

**Why it matters**: The buyer's biggest complaint about robos is the black box. About Titan: the only narrative explanation comes quarterly on video, after the trades. About RIAs: the explanation costs $500/hour. Midas gives the buyer the conversation they wish they could have every Sunday night.

**Mechanism**: The signal stack, regime label, momentum ranks, covariance matrix, and cost estimate are fed to an LLM through a structured signature. The LLM reads, reasons, and explains — it does not route, classify, or decide (see `rules/agent-reasoning.md`). The decision logic is in the allocator; the LLM only narrates. Auditable because the narration cites signal values the user can cross-check in the UI.

**Quantified**: N/A directly, but this is the primary retention lever. Users who feel heard don't churn. Users who don't understand why the system did something churn within 3 months.

### VP4. "Your costs are in the recommendation, not in a footnote."

**Claim**: Every rebalance preview shows you the IBKR commission, the SEC/FINRA fees, the expected half-spread, the estimated market impact, and the turnover penalty that decided whether the trade was worth making.

**Why it matters**: The buyer explicitly said transaction costs are a concern. No robo shows this. Composer shows backtest costs as a single percentage assumption. The buyer has seen what naive momentum strategies look like after costs — most of the paper alpha disappears.

**Mechanism**: Cost model from research §5 — IBKR Pro Tiered schedule + Section 31 + FINRA TAF + half-spread scaled by VIX + Almgren-Chriss square-root impact. The turnover penalty in the weekly optimizer is calibrated in bps so no trade fires unless expected improvement > 2x round-trip cost. Weekly calibration loop against realized fills catches backtest-vs-live drift.

**Quantified**: A cost-aware turnover penalty takes realized turnover from ~400%/year (naive momentum) to ~150–250%/year. At a 10 bps round-trip, that's 150–250 bps/year of saved decay on the portfolio — 6–10x the fee a robo charges.

### VP5. "Your IBKR account. Your custody. Your tax lots. Our advice."

**Claim**: Midas never touches your money, never holds your securities, and never moves cash. You keep your IBKR account exactly as it is. We send the signal; you confirm the trade.

**Why it matters**: The buyer already has an IBKR account and does not want to move it. Every robo forces a custody transfer, triggering tax events, losing tax lots, and severing margin relationships. Switching cost is the single biggest reason they haven't left their DIY spreadsheet. Midas removes the switching cost entirely.

**Mechanism**: IBKR OAuth with scopes restricted to trading and read-only portfolio queries — no money-movement scope, no SLOA, no fee deduction from IBKR (regulatory §5.1). Midas charges the user through a separate Stripe channel, keeping the custody rule untouched.

**Quantified**: Eliminates the ~$2k–$10k tax drag of a taxable-account custody migration for the median $250k buyer, plus weeks of operational friction. This alone justifies the first year of subscription.

### VP6. "Cadence matches the regime. Never more than once a week. Sometimes never."

**Claim**: In calm trends, Midas rebalances every two weeks. In normal, weekly. In turbulent, it stops trading and asks you. It does not churn your account to prove it's working.

**Why it matters**: The buyer's explicit brief line: "concerned about over-trading." Every robo the buyer tried drifted into high-frequency rebalancing as AUM grew, because PFOF rewards flow. Midas has the opposite incentive — it charges a fixed subscription, so fewer trades = happier customer.

**Mechanism**: Weekly cadence cap (brief §4), regime-dependent cadence within cap (assumption A6), L1 turnover penalty, 10-day minimum hold on sold sleeves, 10% weight-change cap per sleeve per week, regime hysteresis (strategy §4.3).

**Quantified**: Against a naive weekly-momentum strategy, these guardrails cut turnover by ~50% at negligible Sharpe cost — directly translating to 100–200 bps/year of preserved return in a cost-honest backtest.

---

## 3. Unique Selling Points (Survived Scrutiny)

I tested every candidate USP against the question: "Does Wealthfront / Betterment / Schwab / Composer / M1 / Interactive Advisors / Titan / Allocate Smartly / Portfolio Visualizer / Frec / Public already ship this?" Survivors only.

### USP1. Regime-aware freeze-and-ask on a multi-asset rotation

**The combination**: auto-rebalance runs in normal regimes; when the regime ensemble flips turbulent, automation halts and per-trade approval is required until it clears.

**Scrutiny**:
- Wealthfront, Betterment, Schwab, Interactive Advisors, M1: **none** freeze on regime. They rebalance on drift alone. Verified in landscape §1 matrix.
- Composer: users can **build** regime logic into a Symphony, but it ships no packaged regime model and has no "freeze and require consent" pattern — the Symphony just executes whatever branch the user wrote.
- Titan: discretionary humans may de-risk in turbulence, but the user has no control over when and no approval gate.
- Allocate Smartly: signal-only; no execution; no freeze gate; no consent flow.

**Verdict**: **SURVIVES.** This is the single most defensible USP. It directly operationalizes the buyer's explicit stated preference ("don't trade without my permission in turbulent markets").

### USP2. Backtest transparency exposed to the end user at recommendation time

**The combination**: every trade preview links to the walk-forward, purged, stress-tested backtest of this exact allocation under this exact regime — not a marketing page, but the live engine's own validation.

**Scrutiny**:
- Wealthfront, Betterment, Schwab, Interactive Advisors, M1, Titan, Public: **none** expose backtests to users.
- Composer: shows backtests, but only for strategies **the user built themselves**. A buyer who doesn't want to be a strategy author gets nothing.
- Portfolio Visualizer: gold-standard backtests, but it's a research tool — it cannot execute.
- Allocate Smartly: shows published TAA strategy backtests, but it's signal-only and the backtests are aggregate, not per-trade.

**Verdict**: **SURVIVES.** No delegated manager + execution product combines shipped strategies with per-decision backtest exposure.

### USP3. Conversational explainability tied to live signal state

**The combination**: the user asks "why this, why now" on any recommendation; the system answers in plain language citing the actual signal values driving the decision.

**Scrutiny**:
- Wealthfront, Betterment, Schwab: no conversational layer, period.
- M1: no advice, nothing to explain.
- Composer: strategies are self-documenting via their Symphony definition — but there is no dialogue, and a non-quant user cannot read a Symphony tree.
- Titan: narrative explanations exist as quarterly PM videos — one-way, delayed, not conversational, not tied to a specific decision, not on-demand.
- Interactive Advisors: static disclosure documents.
- Allocate Smartly / Portfolio Visualizer: blog posts and docs, not a conversational layer.

**Verdict**: **SURVIVES** — with a caveat. The USP is not "we have a chatbot" (commodity). It is "the chatbot is pinned to the live signal stack and cites numeric values the user can verify in the same screen." That precision is what makes it defensible. A generic "ask our AI anything" chat is NOT this USP.

### USP4. IBKR-native advisory with cost-honest UI

**The combination**: lives inside the buyer's existing IBKR account (no custody move) AND surfaces full cost attribution (commission + reg fees + half-spread + impact) inline on every recommendation.

**Scrutiny**:
- Wealthfront, Betterment, Schwab, M1, Titan, Frec: require custody migration. Non-starters for the IBKR buyer.
- Interactive Advisors: IBKR-native and the sharpest objection — but it runs static model portfolios, hides costs as "all-in AUM fee," and has no regime awareness. Same custody, different product.
- Composer: custody at Alpaca, not IBKR. Custody move required.
- Portfolio Visualizer / Allocate Smartly: not execution-integrated; cost modeling is the user's problem.

**Verdict**: **SURVIVES.** The combination is unique. IBKR-native alone is not enough (Interactive Advisors exists). Cost-honest UI alone is not enough (quant tools do it). The combination — native to IBKR and cost-honest at decision time — is unbuilt.

### Candidate USPs that DID NOT SURVIVE

- **"Multi-asset rotation across 8 sleeves."** Wealthfront (11 sleeves), Schwab (20+ sleeves), Betterment (12 sleeves) all ship multi-asset. The number of sleeves is not the wedge. The **regime-aware rotation** between them is the wedge, already captured in USP1.
- **"AI-powered."** Every fintech since 2023 claims this. Commodity marketing term.
- **"Weekly rebalancing."** Every robo rebalances at least this often. Commodity.
- **"Walk-forward backtests."** Portfolio Visualizer and Allocate Smartly have shown these to the target buyer for a decade. The wedge is **exposing the backtest at execution time**, captured in USP2.

---

## 4. Anti-USPs (Do NOT Lean On These In Marketing)

Every product on earth has these. Treat them as table stakes. If Midas's landing page mentions any of them as a differentiator, the buyer clicks back.

- **"Sector rotation."** Every robo does it. Sector ETFs exist since 1998.
- **"ETF diversification."** The default state of every robo-advisor for 15 years.
- **"Backtesting."** Portfolio Visualizer, QuantConnect, Composer, Allocate Smartly all ship backtests. Midas's wedge is *where* the backtest lives (pinned to the live trade), not *that* it exists.
- **"Tax-loss harvesting."** Wealthfront, Betterment, Schwab, Frec all do it, many better than Midas v1 will. Midas v1 should not even claim it.
- **"Low fees."** Schwab Intelligent Portfolios charges $0 AUM. M1 is free. Midas at $79–149/mo is **not** the cheap option, and pretending otherwise insults the buyer's intelligence.
- **"Modern UX."** Every fintech ships a modern UX. This is oxygen, not a feature.
- **"Multi-asset."** Covered by every major robo. The wedge is the *regime gating* on top of multi-asset, not multi-asset itself.
- **"Mobile app."** Every competitor ships one. The iOS/Android requirement in the brief is a hygiene requirement, not a USP.
- **"AI / ML."** Say nothing about this in marketing unless it is paired with a specific auditable capability like USP3.

---

## 5. Buyer Objections (Red-Team The Pitch)

Honest answers. If an answer is weak, the gap is flagged.

### O1. "I already have a Vanguard account. Why would I switch to IBKR?"

**Answer**: You don't. Midas is for people **already on IBKR**. If you're on Vanguard and happy, Midas is not for you. Full stop.

**Strength**: Strong. It's a clean disqualification — but it also defines the ceiling of the addressable market. The TAM is IBKR users, not "everyone with a brokerage account." This is the TAM reality, not a dodge.

### O2. "Robos are cheaper. Wealthfront is 0.25%, Schwab is $0."

**Answer**: Schwab's "$0" includes a mandatory 6–10% cash drag that costs the typical account 40–80 bps/year in a bull market — more than Wealthfront's fee. Wealthfront's 0.25% on $500k is $1,250/year. Midas at $119/mo is $1,428/year — $178 more. For that, you get regime gating (VP1 — potentially 1,500+ bps of preserved capital in one drawdown), cost-honest turnover discipline (VP4 — 100–200 bps/year), and backtest transparency (VP2) that no robo offers. If Midas saves you from one 2022 and one 2008, the math is not close.

**Strength**: Strong on the narrative. **GAP**: requires Midas to actually deliver the regime-gating benefit in live trading. If the gate whipsaws or misses a crash in year one, this entire answer collapses. This is the single biggest execution risk and must be monitored relentlessly post-launch.

### O3. "I don't trust AI with my money."

**Answer**: Good. Neither do we. That's why Midas v1 never executes without your click. The AI explains; you decide. The allocator uses published academic methods (adaptive asset allocation, hierarchical risk parity, purged walk-forward) — not a neural net black box. The LLM in the debate layer reasons over the signal stack in plain language; it does not make allocation decisions.

**Strength**: Strong and honest. The separation of "LLM narrates, allocator decides" (per `rules/agent-reasoning.md`) is a real architectural distinction and the buyer will verify it.

### O4. "What's your track record?"

**Answer**: Midas has no live track record on day one. It has walk-forward, purged-CV, crisis-stress backtests from 2000 onward with point-in-time data, Deflated Sharpe Ratio, and Probability of Backtest Overfitting metrics reported alongside. You can audit every assumption in the backtest methodology document. Live paper-trading results will be public from beta.

**Strength**: **GAP — weak.** Backtests are not track records, and the target buyer knows this. Every TAA product shows the same pattern: beautiful backtests, disappointing live. The honest answer is that Midas will have no meaningful track record for 12–24 months, and the first crisis within that window will either make or break credibility. Mitigation: run paper-trading publicly from day 0 with full transparency; price v1 as a private beta; communicate explicit expectations that year 1 is trust-building, not outperformance.

### O5. "Regulatory risk — what if the SEC shuts you down?"

**Answer**: Midas v1 operates strictly as a publisher under Lowe v. SEC — impersonal model portfolios, regular cadence, no personalized per-user advice, no account-balance awareness on the server, user clicks every trade. This is the same posture newsletters and Allocate Smartly have operated under for decades. For v2's discretionary path, state-then-SEC RIA registration is on the roadmap (cost ~$15k–$50k, 3–9 months per regulatory §3.1). UK, SG, EU are geofenced in v1.

**Strength**: Moderate. **GAP**: the Lowe posture is defensible only if v1 rigorously avoids personalization creep. Any feature that tailors weights to user-specific tax or risk data pulls v1 into adviser territory and kills the exemption. This must become a bright-line engineering rule, not a best-effort policy. Also: the SEC's 2023 safeguarding rule proposal would expand "custody" to include discretionary trading authority; if that rule passes pre-v2, v2's timeline and cost shift materially.

### O6. "Why not just DIY with ChatGPT and a spreadsheet?"

**Answer**: You can. Many of your peers do. The question is whether your time is worth $119/month. Midas replaces: ~4 hours/week of signal gathering, regime assessment, rebalance math, and execution planning (≈ 150–200 hours/year). At any professional hourly rate, that's $15k–$30k of time saved per year. Plus, ChatGPT will cheerfully hallucinate a VIX3M value and you won't notice until your trade is wrong. Midas's signals are pinned to verified data (EODHD primary, Yahoo backup, Perplexity for news) and cited in every explanation.

**Strength**: **Moderate with a real gap.** A sophisticated DIY buyer with Python skills can build something like Midas in a weekend using open-source TAA libraries. The honest answer: they won't maintain it. They won't do the walk-forward retraining. They won't implement purged CV. They won't rebuild the cost model when IBKR changes the fee schedule. Midas is the maintenance layer, not the initial-build layer. **GAP**: This answer is only convincing to a buyer who has tried the DIY path and already burned out. For a buyer who hasn't tried it yet, DIY sounds cheaper and more fun than it actually is. Marketing must surface the maintenance-cost argument explicitly.

### O7. "Why not just use Interactive Advisors — it's already inside IBKR?"

**Answer**: Interactive Advisors runs static model portfolios rebalanced on drift or schedule. It has no regime gating, no backtest transparency, no conversational explainability, and no cost-attribution UI. It's a traditional robo wrapped in IBKR's custody. Midas is the opposite: same custody, but regime-aware, audit-transparent, and designed for the buyer who wants to see the math and approve the trade.

**Strength**: Moderate. **GAP**: this answer depends entirely on Midas actually delivering the four differentiators. If any of them ships half-baked, Interactive Advisors at 0.08% becomes the rational choice. The execution bar on USP1 and USP2 is not negotiable.

---

## 6. Commercialization Readiness Verdict

### The standard

To commercialize, Midas must clear two bars:

1. **10x better than Composer** at the thing Composer doesn't do — packaged regime-aware strategies with conversational explainability for non-quant users.
2. **Materially cheaper than an RIA** — $79–149/mo ($950–$1,800/year) vs a 1% AUM RIA at $5k–$10k/year on the same portfolio. That's 3–10x cheaper. Bar cleared on price.

### Where the value prop clears the bar

- **USP1 (regime freeze-and-ask)**: Nothing in the landscape ships this. Clears the bar by default.
- **USP2 (backtest at recommendation time)**: Composer shows backtests per-Symphony; Midas ships pre-built strategies with the same transparency. This is ~10x less work for the buyer. Clears the bar.
- **USP4 (IBKR-native + cost-honest)**: Removes the largest switching cost in the category. Clears the bar as a wedge, not as outright superiority.

### Where the value prop is conditional

- **USP3 (conversational debate)**: Defensible **only** if the implementation is rigorously pinned to live signal values and cites numbers. A generic chatbot version of this USP fails the scrutiny test — every fintech is shipping "AI chat" in 2026. The architectural discipline of `rules/agent-reasoning.md` (LLM narrates, allocator decides) is what makes this USP real. If implementation drifts into LLM-as-decider, the USP evaporates and the regulatory risk compounds.
- **Backtest-to-live credibility**: The value prop assumes regime gating and turnover discipline deliver in live trading. They might not in the first year. The verdict is conditional on a public paper-trading window before paid launch.
- **US-only reach at launch**: The Lowe posture works in the US. UK, SG, and EU are geofenced. The addressable market for v1 is materially smaller than the global IBKR user base — roughly 35–40% of IBKR accounts are US-domiciled, cutting the ~50k–250k TAM down to ~20k–100k for v1. Still viable for a premium SaaS, but plan accordingly.

### Verdict: **CONDITIONAL GO**

Midas has a real, defensible wedge with three unique selling points that survived brutal scrutiny (USP1, USP2, USP4) and a fourth that is unique **if and only if** engineered with the LLM-as-narrator discipline (USP3). The target buyer exists, is underserved, and can afford the price. The IBKR-native posture removes the largest competitive objection for that buyer. The economics support a premium SaaS at $79–149/mo against a ~20k–100k v1 TAM.

The conditions on the GO are non-negotiable:

1. **Regime gate must be validated in public paper trading** for at least one full regime cycle (3–6 months including at least one cautious-or-worse episode) before paid launch. Marketing based on backtest alone will not survive the first live drawdown.
2. **The explainability layer must be architected per `rules/agent-reasoning.md`**. The LLM explains; the allocator decides. Any drift into LLM-as-router kills both the USP and the regulatory posture.
3. **The publisher posture (Lowe) must be engineered as a bright line**, not a policy. No per-user tailoring on the server. No account-balance state outside the user's own session. Any personalization feature needs a regulatory sign-off gate.
4. **Paper trading and live track record must be published transparently from day zero.** Hide nothing. The target buyer will see through any opacity and walk.
5. **Interactive Advisors is the sharpest competitor** and must be addressed on the landing page, not in docs. If the buyer can't articulate in 30 seconds why Midas is different from Interactive Advisors, they will default to IA and Midas loses.

### If any condition fails

If regime gating cannot be validated, or the LLM architecture drifts, or the publisher posture breaks: the verdict flips to **NO-GO for consumer launch** and Midas pivots to one of two fallbacks — (a) B2B2C white-label signals to existing RIAs (cleaner regulatory posture, smaller but faster revenue), or (b) defer to v2 with RIA registration on day one and eat the 3–9 month delay. A consumer launch without the conditions met burns the brand on the first drawdown.

---

## 7. Gaps Flagged For Next Phase

These are items the value proposition depends on but that the current research doesn't fully resolve. They are not deferrable — they block the next gate.

1. **Live regime gate validation timeline.** How long does public paper trading need to run before the regime gate has earned trust? Recommendation in §6 is 3–6 months covering at least one cautious episode, but this needs an explicit plan with success criteria.
2. **Interactive Advisors head-to-head sheet.** A feature-by-feature comparison, verified against IA's current product docs (not training data), showing exactly where Midas wins and where it matches. Landing-page critical.
3. **Publisher-posture bright lines as engineering rules.** The list of "things Midas server-side must never do" needs to become a codified rule in `.claude/rules/` during phase 05, not a policy document. Regulatory risk is too high for soft guidance.
4. **Live vs backtest divergence monitoring.** The methodology doc has a calibration loop for transaction costs (§5.7), but not for regime gate accuracy or strategy Sharpe. What alert fires when live Sharpe drifts > 0.5 from backtest Sharpe? Who sees it?
5. **US-only v1 TAM refinement.** The ~20k–100k US TAM estimate needs a tighter bottom-up build from IBKR's US-domiciled account count, IBKR Pro penetration, and overlap with the "reads investment blogs, not a quant coder" segment.
6. **The "no live track record" objection (O4).** Currently the weakest answer in the red team. Needs a concrete credibility-building plan: paper-trading transparency, public validation period, beta pricing discount, explicit expectation-setting — a packaged answer, not a hand-wave.
