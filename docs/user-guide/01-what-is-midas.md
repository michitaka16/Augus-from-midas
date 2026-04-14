# 01 — What is Midas?

## In one sentence

Midas watches global markets continuously and tells you exactly what to buy and sell in your ETF portfolio, using an 8-signal regime detector that hides inside a calm, non-intrusive interface that only interrupts when something actually matters.

## The problem it solves

Most retail investors have a choice between two bad options:

1. **Pick their own portfolio and check it every day.** This is what robo-advisors replaced for mass market, but the robos gave up any tactical layer and became glorified couch-potato portfolios. If you want regime-aware allocation, you're supposed to pay 1% to a human advisor who mostly mimics Vanguard anyway.

2. **Use an active manager and pay 1-2%.** The manager does the work, but you have no idea why they did what they did, and the fee eats 30%+ of your long-run returns.

Midas gives you the best of both: a tactical, regime-aware portfolio that adjusts through market cycles, with full transparency into every signal and every decision, at a flat monthly subscription instead of AUM fees.

## What makes it different

### 1. Regime awareness

Midas doesn't just rebalance to fixed targets. It watches 8 market signals (credit spreads, VIX, cross-sector correlation, realized volatility, yield curve, 200-day SMA persistence, drawdowns) and classifies the current market as one of three regimes:

- **Normal**: Risk-on. Full allocation across top-momentum sleeves.
- **Cautious**: Elevated stress. Reduced risk, more bonds/gold.
- **Turbulent**: Crisis mode. All cash unless you override.

The system flips between regimes based on hard data, with hysteresis to prevent whipsaw, and hard overrides for drawdowns or bond-hedge failure.

### 2. The impersonal publisher model

Midas is a **publisher** of model portfolios, not a personalized financial advisor. It generates the same signal for every Growth subscriber at the same time. Your personal situation (balance, tax lots, goals) never enters the signal generation.

This is the same legal framework as The Wall Street Journal or Morningstar — no fiduciary duty, no personalized advice, no SEC adviser registration required. You subscribe to a model portfolio; you decide whether to follow it.

Why this matters to you: lower fees (no advisor margin), full transparency (you see the model, not a black box), no KYC theater beyond what your broker requires.

### 3. The debate layer

This is the feature that separates Midas from every other robo. Every signal the system publishes can be challenged. You open the Debate tab, ask "Why are we heavy in commodities this week?" and the AI responds with citations to specific signal IDs, backtest run IDs, and cost model outputs — all verifiable in the database.

The AI is designed to defend its recommendations with data and push back on weak arguments. If you say "gold is definitely going up", it will ask you to show evidence. If you show evidence it hasn't considered, it will incorporate that into its reasoning.

This makes Midas **debateable** in a way no other automated system is. Every number it shows you has a source.

### 4. Transparent backtests

You can see exactly how the strategy performed over the last 1, 3, 5, 10, and 26 years. You can see:

- Sharpe ratio and Deflated Sharpe (adjusted for multiple testing)
- Probability of Backtest Overfitting (PBO) — is this strategy likely overfit?
- Max drawdown and duration
- Worst 12-month rolling period
- Side-by-side vs 60/40, equal-weight, and VTI-only benchmarks
- Cost drag (how much transaction costs eat returns)
- Regime-conditional performance (how it did in each regime)

If a portfolio doesn't beat 60/40 net-of-costs, it doesn't ship. That's a hard gate.

## What it is NOT

- **Not personalized advice.** Midas publishes the same signal to all Growth subscribers simultaneously. It doesn't know your age, tax bracket, or retirement date.
- **Not real-time.** Signals publish weekly (Sunday 7 PM ET). Intraday regime checks run in live mode but positions are only rebalanced weekly.
- **Not for single stocks or options.** ETF universe only. 10 asset sleeves.
- **Not leveraged.** Long-only, never more than 100% invested. Remainder is cash.
- **Not international (v1).** US residents only during beta. UK/SG/EU blocked until regulatory review.
- **Not a bank.** Midas doesn't hold your money. You connect Interactive Brokers; money stays with your broker.
- **Not a black box.** Every allocation change comes with a reasoning object that cites the signals that drove it.

## Who should use Midas

**Good fit:**
- You have $25k-$2M in investable assets
- You want tactical allocation but don't want to pay 1% to an advisor
- You want to understand what's happening, not just trust a fund manager
- You're comfortable reviewing a weekly signal (takes ~2 minutes)
- You use Interactive Brokers or are willing to open an IBKR account

**Not a good fit:**
- You want a "set and forget" couch potato portfolio → use Vanguard or Fidelity
- You want alpha from individual stock picks → Midas is allocation-level only
- You trade daily → Midas is weekly max turnover
- You need personalized tax-loss harvesting → requires a CPA + advisor, not Midas
- You're outside the US in v1 → wait for Phase 2 international rollout

## The 5 model portfolios

| Name | Vol Target | Style | Monthly |
|---|---|---|---|
| Aggressive Growth | 18% | Maximum momentum concentration | $29 |
| Growth | 14% | Broad diversification with tactical tilt | $29 |
| Balanced | 10% | Stocks + bonds, moderate rotation | $19 |
| Conservative | 6% | Heavy fixed income, some equity | $9 |
| Income | 6% | Dividend + REIT bias, bond heavy | $19 |

You pick one. You can switch anytime. The same signal publishes to everyone subscribed to that portfolio.

---

**Next**: [02 — Quick Start](02-quick-start.md)
