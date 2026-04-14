# 05 — Model Portfolios

Midas publishes 5 model portfolios. You subscribe to one. The same signal goes to every subscriber of that portfolio at the same time.

## The portfolio spectrum

| Portfolio | Vol Target | Style | Monthly | Ideal for |
|---|---|---|---|---|
| **Aggressive Growth** | 18% | Max momentum, concentrated | $29 | Long horizon, high risk tolerance |
| **Growth** | 14% | Diversified tactical | $29 | Mainstream, 10+ year horizon |
| **Balanced** | 10% | Stocks + bonds blend | $19 | Mid-career, 5-10 year horizon |
| **Conservative** | 6% | Bond-heavy with some equity | $9 | Near retirement, low risk |
| **Income** | 6% | Dividend + REIT biased | $19 | Retirement income focus |

All portfolios use the same 10 asset sleeves. What differs is the **volatility target** (how much risk the allocator scales to) and, for Income, a **bias toward dividend-paying assets**.

## How each portfolio works

### Aggressive Growth (18% vol)

**Pipeline:**
1. Rank 10 sleeves by 6-month momentum
2. Select top 6 (K=6 in normal regime)
3. Minimum-variance optimize within the 6
4. Scale weights to target 18% annualized volatility
5. Apply turnover penalty (max 10% weight change per week per sleeve)

**In normal regimes:** Concentrated in the 6 strongest-momentum sleeves. Can be 100% invested. Typical allocation: 60-70% equity (sectors + EM + dividend), 15-20% alternatives (commodities + precious metals), 15% bonds.

**In cautious regimes:** K drops to 4 sleeves. Vol target becomes a ceiling — if 4 sleeves' minimum-variance portfolio is already below 18% vol, stays fully invested. If above 18%, scales down toward cash.

**In turbulent regimes:** 100% cash. Escalation protocol fires.

**Expected returns:** 9-13% annualized over a full cycle, with ~22-28% annualized volatility during bull phases, ~30% max drawdowns.

**Who should pick this:** You have 15+ years until you need the money. You can stomach a 35% drawdown without panic-selling. You believe in trend-following.

### Growth (14% vol) — RECOMMENDED DEFAULT

**Pipeline:** Same as Aggressive Growth but with 14% vol target.

**In normal regimes:** Similar composition to Aggressive Growth, but scaled to lower vol. Typical: 50% equity, 20% alternatives, 20% bonds, 10% cash.

**In cautious regimes:** K=4 sleeves. More bonds, less equity.

**In turbulent regimes:** 100% cash.

**Expected returns:** 7-10% annualized, ~14% annualized volatility, ~20% max drawdowns.

**Who should pick this:** Most users. Broad mandate, reasonable risk. Outperforms 60/40 over long horizons with similar drawdown profile.

### Balanced (10% vol)

**Pipeline:** Same allocator, 10% vol target.

**In normal regimes:** Moderate equity exposure. Typical: 35% equity, 15% alternatives, 30% bonds, 20% cash.

**In turbulent regimes:** 100% cash.

**Expected returns:** 5-7% annualized, 10% vol, 15% max drawdowns.

**Who should pick this:** You're 5-10 years from needing the money. You want equity upside but can't tolerate a 25% drawdown.

### Conservative (6% vol)

**Pipeline:** Same allocator, 6% vol target. Heavily weighted toward bond sleeves when momentum supports it.

**In normal regimes:** 20% equity, 5% alternatives, 50% bonds, 25% cash.

**In turbulent regimes:** 100% cash.

**Expected returns:** 3-5% annualized, 6% vol, 8% max drawdowns.

**Who should pick this:** Retirement is within 3 years or you're already retired. Preservation is the goal.

### Income (6% vol, dividend-biased)

**Pipeline:** Same as Conservative, but with a floor on:
- Dividend ETFs: ≥30% weight (when available in the PIT universe)
- IG Corporate Bonds: ≥20% weight
- REITs: ≥15% weight

These floors ensure yield-generating assets stay in the portfolio even when their momentum is weak.

**In normal regimes:** 30% dividend ETFs, 20% IG corp bonds, 15% REITs, 15% other equity, 20% cash.

**In turbulent regimes:** Still holds dividend ETFs (they pay during crisis too). Reduces equity portion to cash.

**Expected returns:** 3-5% annualized total return. Expected yield: 3-4.5% (varies with rates).

**Who should pick this:** You want monthly dividend income. You're in or near retirement. You prioritize cash flow over total return.

## Switching portfolios

You can switch anytime via Settings. Consequences:

### Cost of switching

When you switch, your next signal will be the new portfolio's allocation. The system does NOT automatically rebalance you into it — it waits for the next weekly signal, and then the rebalance card includes whatever changes are needed.

This means switching on a Tuesday means:
- Sunday's signal publishes for the new portfolio
- You approve that signal
- Your positions move from the old allocation to the new

Typical switching cost: $5-$20 for a $100k portfolio, depending on how different the two portfolios are.

### When to switch

**Good reasons:**
- Major life event (job change, retirement, inheritance, college expense)
- Your risk tolerance changed after living through a drawdown
- Financial goals shifted

**Bad reasons:**
- "Aggressive Growth had a bad week, let me de-risk to Balanced"
- "The regime just flipped to cautious, let me switch to Conservative"
- "I saw a news article"

The system already handles tactical adjustments within each portfolio — switching mid-cycle to respond to regime changes is strictly worse because you pay turnover costs on both sides of the switch.

## Why only 5 portfolios?

Midas deliberately offers a **small, curated** set. Competitors offer dozens of funds or "custom" robos where you answer 20 questions. That's complexity theater — the differences between 8/20 stocks and 12/20 stocks are invisible after costs.

The 5 portfolios span the full risk spectrum (6% to 18% vol). Every retail investor should map to one of these. If you want something between Growth and Balanced, just pick Growth and keep some cash outside Midas — that's functionally the same thing without the complexity.

## The impersonal model — why all subscribers get the same signal

Midas is a **publisher**. This is a specific legal concept in US securities law (Lowe v. SEC, 1985). A publisher:
- Sends the same content to all subscribers simultaneously
- Does NOT personalize based on individual circumstances
- Is exempt from registration as an investment adviser

This is the same framework as:
- The Wall Street Journal
- Morningstar
- Stock-pick newsletters

What this means for you:
- **All Growth subscribers get the exact same signal** at the same time
- Midas doesn't know your balance, tax bracket, age, or goals
- The system can't (and won't) say "sell 50% of your portfolio" — it publishes "Growth target allocation is X"; you decide how to apply it
- No fiduciary duty, no KYC questionnaire, no SEC registration required

If you want personalized advice, hire a registered investment adviser (RIA). Midas is designed to be the affordable middle ground.

## Comparison to alternatives

### vs. Vanguard Target Date funds
- Vanguard: glide path based on retirement year, fixed rebalance, no regime awareness, 0.08% fee
- Midas: tactical allocation, regime-aware, $19-29/mo flat fee
- **Midas wins if:** your portfolio is >$50k (flat fee beats AUM)
- **Vanguard wins if:** your portfolio is <$20k or you want zero engagement

### vs. Robo-advisors (Wealthfront, Betterment)
- Robos: couch potato portfolios with minor tax-loss harvesting, 0.25% AUM
- Midas: regime-aware tactical allocation with full transparency, flat fee
- **Midas wins if:** you want to understand what's happening and don't need TLH
- **Robos win if:** you want tax-loss harvesting and don't care about regime awareness

### vs. Advisors (1% AUM)
- Advisor: human relationship, tax planning, estate planning, 1% AUM
- Midas: just the tactical allocation piece, no human, flat fee
- **Midas wins if:** you only need allocation help
- **Advisor wins if:** you need holistic planning

### vs. DIY
- DIY: full control, zero fees (besides trading costs)
- Midas: delegate the allocation decision + get the regime detector, $19-29/mo
- **Midas wins if:** you don't want to research 8 macro signals every week
- **DIY wins if:** you enjoy the research and have time for it

## Performance expectations

Don't expect miracles. Regime-aware allocation doesn't let you avoid all drawdowns — it reduces them. Examples from backtest:

| Period | 60/40 Return | Growth Portfolio Return | Growth Max DD |
|---|---|---|---|
| 2008 crisis | -22% | -14% | -19% |
| 2020 COVID | +8% | +11% | -13% |
| 2022 stagflation | -16% | -5% | -11% |
| Full 2000-2024 | +6.5%/yr | +8.2%/yr | -24% |

The regime detector's goal is to **reduce** drawdowns, not eliminate them. In a flash crash that happens faster than the 2-day hysteresis, the portfolio rides it down to some degree before the defensive move. Over long horizons, the compounding benefit of smaller drawdowns adds up — that's where the outperformance comes from.

---

**Next**: [06 — Signals Explained](06-signals.md)
