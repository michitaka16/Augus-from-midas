# 18 — FAQ

Quick answers to common questions.

## The product

### What is Midas in one sentence?

A regime-aware multi-asset ETF portfolio manager that publishes impersonal model portfolios and lets you debate every decision with a grounded AI.

### How is it different from a robo-advisor?

Robo-advisors use fixed target allocations that rebalance to the same target regardless of market conditions. Midas's allocation adapts to market regime (normal/cautious/turbulent) based on 8 signals. Robos also don't let you debate the AI — Midas does.

### How much does it cost?

Flat monthly subscription:
- $9/mo for Conservative
- $19/mo for Balanced, Income
- $29/mo for Growth, Aggressive Growth

No AUM fees. No transaction fees (IBKR charges those directly, ~$3-$10/week for a $100k portfolio).

### How much money do I need?

Minimum meaningful: $25,000. Below that, the flat fee is a large % of returns and the minimum trade sizes don't work well.

Recommended: $100,000+. At this level, the subscription is < 0.4% annual drag, much better than a 1% advisor.

### Can I try it free?

Yes. Paper trading is free for the first 2 weeks of every account. You see the same signals, approve the same trades, but no real money moves.

### Where's the money held?

At Interactive Brokers. Midas never holds your money. We're a publisher + thin client, not a custodian.

## The strategy

### What's a "regime"?

A characterization of the market environment:
- **Normal**: risk-on, growth-friendly
- **Cautious**: elevated stress, reduced risk
- **Turbulent**: crisis, all cash

Determined by 8 signals: credit spreads, VIX, yield curve, sector correlations, realized volatility, trend persistence, drawdowns, bond-hedge correlation.

### Will it avoid all drawdowns?

No. The hysteresis requires 2 consecutive days above threshold before flipping, so flash crashes happen faster than the detector. The portfolio rides part of the drop before the defensive move.

What the regime detector does: **reduces** drawdowns. Compare 2008: SPY -38%, Midas Growth (backtested) -19%.

### Does the strategy work in all markets?

The 26-year backtest covers 2000-2024, which includes multiple regimes (dot-com crash, 2008 GFC, 2020 COVID, 2022 stagflation). The strategy performs well across all of these.

Novel regimes not in training data (e.g., a 1929-style depression or 1970s stagflation in the US) may behave differently. The drawdown override provides some protection but can't guarantee performance in unprecedented regimes.

### What's the maximum drawdown I should expect?

Depends on portfolio:
- Aggressive Growth: ~30-35%
- Growth: ~20-25%
- Balanced: ~12-18%
- Conservative: ~6-10%
- Income: ~8-12%

These are from the 26-year backtest. Future drawdowns could be worse.

### Why ETFs only?

1. **Liquidity**: ETFs have tight spreads, easy to rotate in/out
2. **Cost**: Low expense ratios (0.04-0.70%)
3. **Diversification**: One ETF = many stocks
4. **Allocation-level**: Midas optimizes at the sleeve level, not stock level
5. **Tax efficiency**: ETF structure is tax-efficient vs mutual funds

Single stocks are riskier, options add leverage we don't want, mutual funds trade once per day. ETFs are the right tool.

### Can I add my own ETF to the universe?

No. The 10 sleeves and their primary tickers are fixed. Changing them would invalidate the backtest. If you want a sleeve we don't have (e.g., crypto, single-country EM), use your own allocation outside Midas.

## The AI

### Does the AI make the decisions?

No. The **allocator** (deterministic code) generates the signal. The AI's job is to **explain** and **debate** the signal. Every trade recommendation is from the algorithmic allocator, not the AI.

### Why does the AI cite everything?

Because if it didn't, it'd just be a chatbot making things up. Midas's "grounding contract" requires every factual claim to cite a real database record. This is what makes the AI useful — its responses are verifiable.

### What if the AI is wrong?

The AI can only cite what's in the database. If the cited data is correct (the signal, backtest, cost breakdown), the AI's explanation is accurate. If the underlying data is wrong (a bug in the strategy), the AI will faithfully explain the wrong data.

The protection: the data is verified by backtests, assertions, and the replay job. The AI doesn't need to second-guess the data — it just describes it.

### Will the AI agree with me?

Not if your argument is weak. The AI is designed to defend positions with data and push back on gut-feeling arguments. It yields only to evidence.

### Can the AI execute trades?

No. The AI can propose, explain, and compare, but only you (with biometric confirmation) can approve a trade. The system has no auto-execution path that bypasses the user, except the turbulent auto-defensive after timeout — and that's explicitly documented and configurable.

### What LLM does the AI use?

The debate agent uses whichever provider has a working API key in `.env`. Fallback chain: MiniMax → ZAI → OpenAI → Anthropic. If you have GPT-4o or Claude Opus, the AI will use those.

## Technical

### Why Python 3.14?

Latest stable Python at time of writing. Most stable for new installs. Some quirks (editable installs, asyncio) are documented in troubleshooting.

### Why Next.js for web?

Server-side rendering, file-based routing, built-in TypeScript, Vercel deployment. Mature, battle-tested for SaaS apps.

### Why React Native for mobile?

Code reuse with web (~60% of UI logic shared via shared types). Cross-platform (iOS + Android from one codebase). Expo simplifies distribution.

### Why Interactive Brokers only?

See chapter 14. Short version: IBKR has the best execution for ETFs, lowest commissions, and a clean third-party API. Other brokers don't meet one or more of these criteria.

### Why PostgreSQL?

Standard choice for financial data. TimescaleDB extension adds hypertables for time-series (bars, regime signals). pgvector for semantic news search. All open-source.

### Why Docker for infrastructure?

Reproducible local dev environment. Same commands work on any developer's machine.

### Is there a Docker image for production?

Not yet. Production deployment uses Kubernetes with separate container images built by GitHub Actions. The `deploy/docker/Dockerfile` is for local dev.

## Legal

### Is Midas regulated?

Midas operates under the publisher exemption (Lowe v. SEC). This means we're NOT registered as an investment adviser — we're a publisher, like a financial newsletter.

### What if the SEC changes its interpretation?

If our publisher status were challenged, we'd either:
1. Register as an RIA (expensive, but preserves the business)
2. Restrict features to stay within publisher bounds
3. Shut down (worst case)

We've designed Midas to be comfortably within the publisher zone. This risk is low, but nonzero.

### Can I trust the backtest?

The backtest uses:
- Real historical market data (EODHD for bars, FRED for macro)
- Walk-forward validation (no look-ahead bias)
- CPCV for overfitting detection
- Point-in-time ETF universe (no survivorship bias)
- Full cost model (commissions, slippage, impact)

Trust the process. Don't trust the specific number — future performance varies.

### Is there a money-back guarantee?

First 14 days: full refund, no questions.
After 14 days: prorated refund for unused time.
After 12 months: no refund.

Refund requests: email `billing@midas.app`.

### Can I transfer my account?

No. Midas accounts are non-transferable. The linked IBKR account is yours and transfers with you if you close Midas.

## Edge cases

### I'm outside the US, can I use Midas?

v1 is US-only. Signups from other IPs are blocked at the CDN. We're evaluating UK, Singapore, and EU for Phase 2.

### I'm a minor

Midas requires account holders to be 18+ (or the age of majority in their state). We can't legally publish to minors without parental involvement.

### I'm a high-net-worth individual (> $10M)

Midas works, but consider hiring a full-service advisor. At your asset level, personalized tax optimization, estate planning, and trust structuring are worth the 0.5-1% fee. Midas fills a niche below advisors, not a replacement for them.

### I have multiple brokerages

Midas supports one IBKR account per user in v1. If you have Vanguard + Fidelity + IBKR, Midas can only trade your IBKR account. You'd need to manually mirror the allocation in your other accounts.

### My portfolio is < $25k

Midas technically works, but:
- $29/mo fee = $348/yr
- 1.4% annual drag on $25k
- Minimum trade sizes may fail for small positions

At this size, use Vanguard or Fidelity's free robo (couch potato portfolio) until you grow the account. Come back to Midas when you have $50k+.

### I'm in or near retirement

Conservative or Income portfolios are right for you. Bond-heavy, low vol target, designed for capital preservation.

Consider pairing with an annuity or SPIA for guaranteed income — Midas handles the market-exposed portion of your portfolio only.

### I have specific tax constraints

Midas doesn't do tax-loss harvesting. If you need that, use an RIA or a robo that offers TLH (Wealthfront, Betterment).

You can manually replicate tax-aware behavior by skipping specific trades on the approval card. But this breaks portfolio balance and isn't recommended as a regular practice.

### I'm a financial advisor — can I use Midas for my clients?

Not yet. v1 is direct-to-consumer. RIA licensing for Midas as a white-label tool is Phase 2.

### What about a SPAC or IPO ETF that just launched?

If it's in our 10 sleeves' primary ticker list, we'd include it when the PIT universe picks it up. Usually 6+ months after IPO. If it's not in our universe, we don't trade it.

### What about inverse or leveraged ETFs?

Not used. These products have decay properties that make them unsuitable for weekly allocation. We stay with plain long-only ETFs.

## Still have questions?

- **Product questions**: email `support@midas.app`
- **Technical issues**: GitHub issues on the repo
- **Billing**: `billing@midas.app`
- **Security**: `security@midas.app`
- **Legal**: `legal@midas.app`

---

**Next**: [19 — Glossary](19-glossary.md)
