# User Brief — Midas Platform

Source: verbatim from user, session 2026-04-09.

## 1. Objective
- I don't want to monitor it
- It should make the best investment decisions
- Make me money

## 2. Risks
- Turbulent markets, high-risk situations: don't trade without my permission
- In normal markets, go ahead

## 3. Markets and Instruments
- Broker access: IBKR (Interactive Brokers)

## 4. Strategies

### Portfolios
- ETFs for diversification and sector rotation
- Precious metals
- Bonds: government bonds (all durations)
- Corporate high-quality bonds
- REITs
- Commodities
- Dividend funds
- Emerging markets

### Principles
- There is no free lunch
- No single instrument is always best
- Agile rotation is important

### Risk Profile
- "Go big or go home"
- Risk-loving, NOT reckless/stupid

### Rebalancing
- Cadence depends on market regime
- Never more than once per week

## 5. Constraints
- Concerned about transaction fees (over-trading risk)

## 6. Risk Management
- Backtest comprehensively across all market conditions
- Multiple sub-horizons, not a single horizon

## 7. Metrics (cost modeling)
- Accurate transaction cost algorithms
- Fees, price impact, slippage
- Gap up / gap down
- Commissions, exchange, regulatory fees

## 8. UI/UX
- Web, iOS, Android
- Modern UX for rapid decision-to-execution
- "Debate with the AI" capability on demand
- Commercializable as a product

## 9. Data Sources
- EODHD API (primary) — user has key
- Yahoo Finance (backup)
- Perplexity API for news (user has key)
- Data fabric: store-once, reuse — never re-pull
- Common multi-user database
- Latency critical → aggressive caching
- Real-time not required; pull when screen is active
