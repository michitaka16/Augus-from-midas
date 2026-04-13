# Red Team — Product & Strategy Review

Adversarial review of Midas v1 analysis, plans, user flows, and brief compliance.

---

## CRITICAL — Blocks Ship

### C1. Turbulent regime freeze has no timeout or auto-defensive trigger

**What's wrong**: Flow 3 freezes auto-trading and waits for the user to respond. The docs say "system checks again next market close" if the user chooses "Hold Current," but there is NO specification for what happens if the user simply does not respond at all — no tap on the push, no opening the app — for 1, 3, or 5 days. The system sits frozen in a turbulent regime with the user's existing positions fully exposed to drawdown.

**Why it matters**: The brief says "turbulent markets, high-risk situations: don't trade without my permission." The system interprets this as "freeze and wait." But the user also said "I don't want to monitor it." These two requirements are in direct tension. In March 2020, the S&P fell 34% in 23 trading days. A user who ignores a push notification for 3 business days in that scenario loses potentially 15%+ while the system sits frozen "waiting for permission." This is the worst possible outcome: the system knew danger was present, told the user, and then did nothing.

**Proposed fix**: Implement a tiered escalation protocol with a hard timeout:
1. T+0: Push notification (current).
2. T+4h: SMS/email escalation: "You haven't responded. Market is down X% since alert."
3. T+24h: Second escalation with explicit framing: "If you don't respond by [time], the system will execute the defensive rebalance automatically."
4. T+48h: Auto-execute the defensive rebalance. Log it. Notify user.

This must be configurable per user (the user sets their own timeout). The default should be 48 hours, not infinity. Document the legal implications under publisher exemption — auto-execution on timeout may push toward personalization. If so, the timeout action should be "pause signal publication for this user" rather than "execute trades."

### C2. AAA net-of-cost alpha is asserted, never stress-tested against the null hypothesis

**What's wrong**: ADR-004 specifies AAA with a walk-forward Sharpe > 0.5 gate. The backtest explorer mockup shows a full-history Sharpe of 0.72 for Growth. But there is zero discussion of the base rate for tactical allocation strategies in walk-forward tests. The academic literature (Marcos Lopez de Prado, Rob Arnott, AQR) consistently shows that most TAA strategies fail to beat a static 60/40 net of costs and taxes over 10+ year horizons. The plan requires PBO < 0.4, but this threshold is chosen without justification.

**Why it matters**: The entire product value proposition rests on the signal quality. If the AAA allocator underperforms a static benchmark in live walk-forward after the first 12 months, "Delegator Alex" will churn. The plan is honest about survivorship bias (R6) and backtest-live drift (R2) but never confronts the deeper question: even with perfect execution, does the strategy add value?

**Proposed fix**:
1. Add an explicit "null hypothesis benchmark" to the backtest gate: the AAA allocator must beat a static allocation (60/40, equal-weight across the 8 sleeves, and the user's chosen model portfolio weights) net of costs in at least 60% of walk-forward windows longer than 3 years.
2. The PBO threshold of 0.4 needs sourcing. Bailey et al. (2014) suggest PBO < 0.5 is "acceptable" but this is for single strategies; an ensemble with 8 signals and multiple hyperparameters should use a stricter threshold. Justify the number or tighten it.
3. The debate agent must be able to show the user "here's how the model performed vs. buy-and-hold over the last N months" at any time. This is missing from the debate tools list.

### C3. Publisher exemption + "go big or go home" is an unresolved legal contradiction

**What's wrong**: The synthesis (Section 1) correctly identifies that the publisher exemption requires impersonal delivery. But the brief's "go big or go home" risk appetite is inherently personal. The 3 model portfolios (Growth 14% / Balanced 10% / Conservative 6%) are the system's attempt to reconcile this, but the user choosing between them IS a form of personalization at the point of subscription. More critically: the approval flow computes "what this signal means for YOUR current IBKR holdings" client-side. If the client-side code is part of the SaaS product (which it is — it's the app), a regulator could argue this is personalized advice delivered through a technical workaround.

**Why it matters**: If a state regulator or the SEC views the client-side order preview as personalized investment advice, the publisher exemption collapses. The entire v1 legal posture depends on the server being impersonal, but the product experience — which is what a regulator evaluates — is deeply personal.

**Proposed fix**:
1. Get an actual securities attorney opinion on whether the client-side order preview constitutes personalized advice under Lowe v. SEC. This cannot be resolved by engineers.
2. Document the specific case law that supports "client-side computation from impersonal signals is not advice." If no case law exists, this is a genuine legal risk that should be in the risk register as CRITICAL, not implied as solved.
3. Consider shipping v1 WITHOUT the client-side order preview — just show the model portfolio target weights and let the user figure out their own trades. Less convenient, more legally clean.

---

## HIGH — Degrades Value Proposition

### H1. EM equity and commodity ETF liquidity in turbulent regimes is not addressed

**What's wrong**: The 8-sleeve universe includes EM equity and commodities. In turbulent regimes (when the user most needs to rotate), EM ETFs (VWO, IEMG, EEM) and commodity ETFs (DJP, GSG) experience significant spread widening and volume drops. The cost model mentions Almgren-Chriss impact, but the plan never discusses whether the allocator's 10-day min-hold + weekly cap is sufficient to avoid selling into illiquidity.

**Why it matters**: In March 2020, VWO bid-ask spreads tripled and intraday NAV premiums/discounts hit 3-5%. Selling $50k of VWO in that environment costs materially more than the cost model's normal-regime calibration suggests. The drawdown override triggers at -8% soft / -12% hard, which is exactly when EM/commodity liquidity is worst.

**Proposed fix**: Add a liquidity-aware execution layer to the cost model that uses regime-conditional spread estimates, not normal-regime calibration. The allocator's weight caps should be liquidity-adjusted: in cautious/turbulent regimes, EM and commodity sleeve max weights should shrink automatically based on trailing 5-day average spread and volume.

### H2. No trust-building path for weeks 1-4

**What's wrong**: Flow 2 assumes "push, card, swipe, done in 30 seconds." But a new user in week 1 has zero reason to trust a model they've never seen perform. The onboarding flow includes 2 weeks of paper trading (good), but there's no explicit trust-building sequence: no "here's what the model would have done last week" retrospective, no "here's how the model performed during COVID" walkthrough, no progressive disclosure of complexity.

**Why it matters**: Alex's anti-behavior is "accept 'just trust us.'" But the product asks for trust on day 1 by pushing an approval card. The debate agent exists but Flow 1 doesn't direct the user to it during onboarding. The backtest explorer exists but isn't part of the onboarding sequence.

**Proposed fix**: Add an explicit trust-building onboarding sequence:
- Week 1: Paper trading + daily "what the model did and why" email digest.
- Week 2: Backtest walkthrough ("here's how Growth performed during 2020 — watch the regime flip").
- Week 3: First real-money trade (small, low-cost).
- Week 4: Full weekly cadence begins.
Integrate the debate agent into onboarding: after the first paper trade, prompt "Want to understand why?"

### H3. No AI track record visibility for the user

**What's wrong**: Flow 4 (debate) shows the agent defending current positions, but there's no mechanism for the user to see the AI's historical accuracy. "The last 3 regime calls were: X, Y, Z. The model acted on them by... The result was..." This is conspicuously absent from both the debate tools and the backtest explorer.

**Why it matters**: When the AI is wrong (and it will be — R8 explicitly acknowledges stock-bond correlation breaks will lag), the user needs to see "the model was wrong about X, here's what happened, here's what it learned." Without this, the first significant wrong call destroys trust permanently. Priya (the validator persona) explicitly needs this to compare Midas against her own track record.

**Proposed fix**: Add a `fetch_regime_track_record` tool to the debate agent that returns: every regime transition, what the model recommended, what actually happened, the realized P&L delta vs. holding. Surface this as a "Model Track Record" tab in the backtest explorer.

### H4. Stock-bond correlation mitigation (R8) is hand-wavy

**What's wrong**: R8 says "PC1 signal in the ensemble catches the transition; drawdown hard override backstops." The tripwire (SPY-TLT 21-day rolling correlation > +0.3 forces cautious regime) is good, but the plan never specifies what "cautious" means when bonds AND equities are falling. The cautious regime (K=4, 8% vol target) still allocates to bonds. If bonds are the problem, going cautious with bond exposure is not a mitigation.

**Why it matters**: 2022 was a -18% year for both SPY and TLT. The cautious regime's 8% vol target with bond allocation would have been negative. The user who chose "Conservative" (6% vol, presumably heavy bonds) would have been especially hurt.

**Proposed fix**: Define a "correlation breakdown" sub-regime within cautious that reduces bond allocation to zero and substitutes T-bills or cash. The tripwire should trigger not just "cautious" but a specific "bonds-not-hedging" override. ADR-003 needs a 9th signal: trailing stock-bond correlation, with an explicit override path.

### H5. Pricing model is completely absent

**What's wrong**: The brief says "commercializable as a product" and the persona says Alex "will pay for value but bristles at percentage-of-AUM fees." But there is zero pricing model anywhere in the analysis, plans, or scope. No discussion of SaaS subscription tiers, AUM-based fees, freemium, or unit economics.

**Why it matters**: At $50k AUM, a 0.25% AUM fee is $125/year — barely worth billing for. At $1M, it's $2,500/year — competitive. A flat SaaS subscription of $50/month works for $1M accounts but is expensive relative to value for $50k accounts. The pricing model affects product decisions: if it's flat-rate, you optimize for high-AUM users; if AUM-based, you need to know the account balance (which may break publisher exemption). This is not a v2 problem — it affects v1 positioning and landing page copy.

**Proposed fix**: Add a pricing analysis to the synthesis or scope doc. At minimum: flat-rate subscription (likely $29-99/month), with justification for why this works at the target AUM range. Explicitly confirm that flat-rate pricing avoids the need to know account balances (preserving publisher exemption).

### H6. Three model portfolios may be too few for the target market

**What's wrong**: Growth (14% vol), Balanced (10%), Conservative (6%). This maps neatly to risk tolerance tiers but ignores the user's actual financial context: time horizon, income needs, existing holdings outside IBKR. Alex with $200k at IBKR might also have $500k in a 401k that is 100% equities — making "Growth" at IBKR dangerously correlated. Priya's clients have diverse needs that don't map to 3 portfolios.

**Why it matters**: The publisher exemption prevents per-user customization, but the 3-portfolio menu is so narrow that users will self-select incorrectly. A user who picks "Growth" without understanding their total portfolio risk is getting advice that is inappropriate for their situation — and Midas has no mechanism to know or warn about this.

**Proposed fix**: Add a disclaimer in the selection flow: "This model portfolio does not account for your other investments, tax situation, or financial goals. Consider consulting a financial advisor." Also consider adding 1-2 more portfolios: "Income" (dividend + bond heavy) and "All-Weather" (risk-parity inspired) would cover more use cases without personalization.

---

## MEDIUM — Should Address

### M1. Perplexity API as sole news source creates a single point of failure for debate quality

The debate agent's news grounding depends entirely on Perplexity. R7 mentions a fallback (RSS + FinBERT) but this is scoped as a Phase 6 item — meaning the entire beta period has no news fallback. If Perplexity changes their API, rate-limits aggressively, or halts service, the debate agent loses news context with no warning.

**Proposed fix**: Move the RSS + FinBERT fallback to Phase 3 or 4. It doesn't need to be perfect — it needs to exist.

### M2. Mobile app scope is ambitious for 1 session in Phase 4

Phase 4 allocates 1 session for the entire mobile app: push notifications, approval cards, biometric auth, IBKR order submission, deep links. React Native Expo reduces boilerplate but IBKR OAuth in a mobile context, biometric confirmation flows, and push notification infrastructure are each non-trivial.

**Proposed fix**: Either increase mobile allocation to 2 sessions or cut mobile to "approval-only PWA" for v1 beta and ship native in v1.1.

### M3. No monitoring for regime detection false positives

The risk register covers regime detection for known historical events but doesn't address false positive rate. How often does the ensemble trigger "turbulent" when markets subsequently recover within days? Every false alarm costs user trust and potentially forces unnecessary defensive trades.

**Proposed fix**: Add a backtest metric: regime detection false positive rate (transitions to turbulent that revert within 10 trading days without reaching -12% drawdown). Target: < 2 false positives per year over the backtest period.

### M4. FRED data is missing from the EODHD ingestion plan

The data fabric (D1) mentions EODHD for prices and FRED for macro indicators (VIX, credit spreads, yield curve). But the phase roadmap (Phase 1) only mentions "EODHD + FRED ingestion" as a single line item. The regime ensemble depends on 7+ FRED series. There is no specification of which FRED series, their update frequency, or how gaps/revisions are handled.

**Proposed fix**: Enumerate the exact FRED series needed (BAMLH0A0HYM2 for HY OAS, VIXCLS, DGS10, DGS3MO, etc.), their update schedule, and the backfill strategy.

### M5. The "debate" framing may set wrong expectations

"Debate with the AI" implies the AI has opinions and can be argued with. In practice, the DebateAgent is a data-retrieval and explanation tool with a conversational interface. Users expecting a genuine intellectual sparring partner (like arguing with a human advisor) may be disappointed when the agent always defers to the quantitative model.

**Proposed fix**: Consider reframing as "Ask the AI" or "Challenge the Model" — setting expectations that the system explains and defends with data, rather than having independent opinions.

### M6. Paper trading mode behavior during regime transitions is unspecified

Flow 1 defaults new users to 2 weeks of paper trading. What happens if a regime flip occurs during those 2 weeks? Does the user see the turbulent-regime flow with paper trades? Does the freeze apply? Paper accounts at IBKR behave differently from real accounts in volatile markets (fills are guaranteed, no spread widening). The onboarding experience during turbulence could be misleadingly smooth.

**Proposed fix**: Specify paper-trading behavior during regime transitions. Add a disclaimer: "Paper trading fills are guaranteed — real-market fills during turbulent periods may differ."

### M7. No discussion of tax efficiency even at the publishing level

The plan correctly defers tax-loss harvesting to v2. But the signal publication itself (weekly rebalancing, sector rotation) generates short-term capital gains by design. The plan never discusses or warns users about tax drag. A Growth portfolio with 142% annual turnover generates substantial short-term gains taxed at ordinary income rates.

**Proposed fix**: Add a "Tax Impact" section to the signal detail screen (not personalized — just a generic note: "This model portfolio's estimated annual turnover of X% may generate short-term capital gains. Consult a tax advisor."). Consider adding a "tax-aware turnover penalty" to the allocator that penalizes trades held < 1 year more heavily.

---

## LOW — Nice to Have

### L1. "Delegator Alex" persona may be too narrow for early growth

The persona is well-drawn but the segment ($50k-$1M, IBKR, self-directed, wants regime awareness + debate) is niche. Early growth will depend on word-of-mouth from exactly this segment. The Learner (Marco) and Validator (Priya) personas are acknowledged but not served by the UX (no educational content, no multi-portfolio comparison view).

### L2. No offline/degraded-state mobile UX

What does the mobile app show when the user has no connectivity? The approval card flow depends on real-time IBKR connectivity. An airplane-mode user who taps a push notification should see a cached version with a "submit when online" option.

### L3. Backtest explorer mockup shows unrealistically clean numbers

The mockup shows Sharpe ratios that decline smoothly from 1.12 (1y) to 0.72 (full). Real backtest results are messy, with some 3y windows showing negative Sharpe. The UI should be designed for ugly numbers, not idealized ones.

### L4. No A/B testing or signal variant framework

If the team wants to iterate on the allocator (new signals, different weights, different K), there's no framework for publishing "variant A vs variant B" signals and measuring which performs better out-of-sample.

---

## Brief Compliance Audit

| Brief Item | Covered? | Notes |
|---|---|---|
| 1. Don't want to monitor | Partial | Weekly push + approve is low-touch, but turbulent freeze has no timeout (C1) |
| 1. Best investment decisions | Partial | AAA specified, but alpha vs. null hypothesis untested (C2) |
| 1. Make me money | Partial | Depends on C2 resolution |
| 2. Turbulent: don't trade without permission | Yes | Flow 3 covers this well, modulo C1 timeout |
| 2. Normal: go ahead | Yes | Flow 2 covers this |
| 3. IBKR | Yes | ADR-002, D5 |
| 4. ETFs, precious metals, bonds, REITs, commodities, dividends, EM | Yes | 8 sleeves cover all |
| 4. No free lunch, no single best, agile rotation | Yes | Core design principle |
| 4. Go big or go home, risk-loving not reckless | Partial | Tension with publisher exemption (C3); Growth at 14% vol is moderate, not "go big" |
| 5. Transaction fee concern | Yes | Cost model is comprehensive |
| 6. Backtest comprehensively | Yes | CPCV + PBO + multi-horizon |
| 6. Multiple sub-horizons | Yes | 1y/3y/5y/10y/full |
| 7. Accurate cost algorithms | Yes | Almgren-Chriss + all fee components |
| 7. Fees, impact, slippage, gap | Yes | All modeled |
| 8. Web, iOS, Android | Yes | Next.js + React Native Expo |
| 8. Modern UX, rapid decision-to-execution | Yes | Flow 2 targets 30 seconds |
| 8. Debate with AI | Yes | Flow 4 + ADR-008 |
| 8. Commercializable | Partial | No pricing model (H5) |
| 9. EODHD primary | Yes | D1 |
| 9. Yahoo backup | Yes | Reconciliation layer, R9 notes fragility |
| 9. Perplexity for news | Yes | D1, R7 |
| 9. Data fabric / store-once | Yes | Core architecture |
| 9. Common multi-user DB | Yes | ADR-006 |
| 9. Latency critical / aggressive caching | Yes | Redis hot cache, screen-active pull |
| 9. Real-time not required | Yes | Pull on screen-active, not streaming |

**Items NOT in brief but added by the system**: PACT envelope separation, CPCV/PBO statistical rigor, Deflated Sharpe, publisher exemption legal analysis, HRP fallback allocator, multi-persona analysis (Priya, Marco). All are reasonable additions that serve the brief's intent — none are scope creep.

**Items in brief but underserved**: "Go big or go home" — Growth at 14% vol target is a moderate risk level, not aggressive. A truly "go big" portfolio would target 18-20% vol with leveraged ETFs or concentrated sector bets. The publisher exemption makes this even harder because you can't offer a "go big" portfolio without also offering moderate ones (impersonal = one-size-fits-all). The brief's risk appetite is structurally incompatible with the chosen legal posture, and this tension is acknowledged but not resolved.
