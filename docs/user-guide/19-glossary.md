# 19 — Glossary

Every financial and technical term used in Midas, defined.

## Financial terms

### AAA (Adaptive Asset Allocation)
The allocation strategy Midas uses: momentum-based sleeve selection followed by minimum-variance optimization, scaled to a vol target, with turnover penalty. Adapts to market conditions via regime detection.

### Adj_close (Adjusted Close)
A stock/ETF's closing price adjusted for splits, dividends, and other corporate actions. Use adj_close (not raw close) for return calculations.

### Almgren-Chriss Model
A market impact model used to estimate the cost of executing a trade. Impact grows with the square root of the trade's fraction of average daily volume. Midas uses this for cost estimation.

### Allocation
The target weight assigned to each asset sleeve in a portfolio. Sum of allocations + cash = 100%.

### Alpha
Returns above a benchmark. Midas's goal is to generate alpha vs 60/40 through regime-aware allocation.

### Annualized Sharpe
Sharpe ratio scaled to an annual basis (daily Sharpe × √252). Standard way to compare strategies.

### Asset Sleeve
A category of ETFs grouped by common characteristics. Midas uses 10: equity sectors, precious metals, short/intermediate/long gov bonds, IG corp bonds, REITs, commodities, dividend ETFs, EM equity.

### Backtest
Simulating a strategy on historical data to estimate performance. Midas uses walk-forward + CPCV backtests.

### Backwardation (VIX3M)
When near-term VIX is higher than 3-month VIX, indicating the market expects more volatility in the near future. A stress signal.

### Basis Points (bps)
1 bp = 0.01%. Used for spreads, yield differences. 300 bps = 3%.

### Benchmark
A reference portfolio to compare against. Midas uses 60/40 (SPY/TLT), equal-weight, and VTI as mandatory benchmarks.

### Cautious (Regime)
Middle regime level. Score 0.35-0.65. Reduced risk allocation (K=4 sleeves).

### CDN (Content Delivery Network)
Infrastructure that caches content near users for fast access. Signals are CDN-cacheable because they're impersonal (same for all subscribers).

### CPCV (Combinatorial Purged Cross-Validation)
López de Prado's improvement on walk-forward validation. Generates all combinatorial train/test splits with purge + embargo. Used to compute PBO.

### Covariance Matrix
The statistical relationships between sleeve returns. Used in minimum-variance optimization. Midas uses a 63-day rolling window.

### Credit Spread (HY OAS)
The yield premium high-yield corporate bonds pay over Treasuries. A leading indicator of equity stress.

### CUSIP
Unique identifier for a US security. Not used by Midas directly — we use tickers.

### Deflated Sharpe
Sharpe ratio adjusted for multiple testing and non-normal returns. Lower than raw Sharpe. PBO threshold: DSR > 0.5.

### Drawdown
Peak-to-trough decline in portfolio value. Max drawdown is the worst decline in a period.

### ETF (Exchange-Traded Fund)
A basket of securities that trades like a stock. Midas trades only ETFs.

### Ensemble Score
The weighted sum of 8 regime signals. 0.0 = calm, 1.0+ = crisis.

### Expense Ratio
Annual fee a fund charges as % of assets. Lower is better. Midas prefers ETFs with < 0.5% expense ratio.

### FOMC
Federal Open Market Committee. Sets US interest rate policy. FOMC announcements can trigger regime flips.

### Fundamental Data
Company financials (P/E, yield, AUM for ETFs). Midas uses these for filtering but not for allocation decisions.

### Gap Risk
The risk of large overnight price moves between market close and next open. Midas includes gap risk estimates in cost modeling.

### GFC
Global Financial Crisis (2008-2009). Max drawdown event in the backtest.

### HRP (Hierarchical Risk Parity)
A portfolio construction method that clusters assets hierarchically and allocates risk parity within clusters. Midas uses HRP as a fallback when momentum is degenerate.

### Hysteresis
The requirement that a regime stay above a threshold for 2 consecutive days before flipping. Prevents whipsaw.

### HY OAS (High-Yield Option-Adjusted Spread)
The yield spread between junk bonds and Treasuries. A regime signal with weight 0.25.

### Hypertable (TimescaleDB)
A Postgres table optimized for time-series data. Midas uses hypertables for `bars`, `regime_signals`, `audit_trail`.

### IBKR (Interactive Brokers)
The only brokerage Midas integrates with in v1.

### Impersonal Publisher
A legal category under the publisher exemption. Publishes same content to all subscribers. Not regulated as an investment adviser.

### IG (Investment Grade)
Bond credit quality rated BBB- or higher. IG corporate bonds = LQD, VCIT.

### IPO Lockup
Period after IPO when insiders can't sell. Can affect ETFs holding recent IPOs.

### K (Top-K Selection)
Number of top-momentum sleeves to include. K=6 in normal, K=4 in cautious, K=0 in turbulent.

### Limit Order
An order to buy/sell at a specific price or better. Midas uses market orders for ETFs (sufficient liquidity).

### Liquidity Tier
Classification of ETFs by average daily volume: high, medium, low. Used by cost model.

### Long-Only
No short positions. All weights ≥ 0. Midas v1 is long-only.

### Market Impact
The price movement caused by your own order. Midas estimates this via Almgren-Chriss.

### Market Order
An order to buy/sell at the current best price. Used by Midas for ETF rebalancing.

### MFA (Multi-Factor Authentication)
Extra authentication factor beyond password. Midas uses TOTP.

### Min-Variance Optimization
Portfolio construction that minimizes variance. Formula: w = (Σ⁻¹ × 1) / (1' × Σ⁻¹ × 1). Used by AAA.

### Momentum (6-Month)
Total return over the last 126 trading days. Used to rank sleeves.

### Normal (Regime)
Lowest regime level. Score < 0.35. Full allocation across 6 sleeves.

### NYSE (New York Stock Exchange)
Primary US exchange. Midas's trading calendar.

### OAuth 2.0
Authorization protocol used by IBKR for third-party access. Midas uses OAuth for IBKR integration.

### OHLCV
Open, High, Low, Close, Volume. Standard bar data format.

### PBO (Probability of Backtest Overfitting)
Fraction of CPCV splits with negative OOS Sharpe. PBO > 40% = don't ship.

### PC1 Variance
Variance of the first principal component of sector ETF returns. Proxy for correlation breakdown. A regime signal with weight 0.20.

### Paper Trading
Simulated trading with fake money on a separate IBKR paper account. Default for new Midas users.

### PIT Universe (Point-in-Time)
The set of ETFs that existed and were tradeable on a given historical date. Used for survivorship-free backtests.

### Portfolio
A model allocation strategy. Midas has 5: Aggressive Growth, Growth, Balanced, Conservative, Income.

### Preview Order
IBKR endpoint that simulates an order's impact without submitting. Used by Midas for client-side cost estimation.

### Publisher Exemption (Lowe v. SEC)
Legal framework under which publishers of financial information are exempt from investment adviser registration. Requires impersonal, disinterested, bona fide publication.

### Purge Window
In CPCV, the number of samples removed around train/test boundaries to prevent leakage. Midas uses 5 days.

### Realized Volatility
Actual volatility observed in recent returns (vs implied vol from options). Midas uses 21-day annualized.

### REIT (Real Estate Investment Trust)
A security holding real estate. REIT ETFs include VNQ, IYR.

### Refresh Token
JWT used to obtain a new access token. Single-use in Midas (rotates on each use).

### Regime
Market state classification: normal, cautious, turbulent. Core concept of Midas.

### Rebalance
Adjusting portfolio weights back to target. Midas rebalances weekly (Sunday).

### ROC (Rate of Change)
Momentum-related metric, sometimes confused with momentum. Midas uses cumulative return, not ROC.

### Sharpe Ratio
(Return - Risk-free rate) / Volatility. Risk-adjusted return metric. Key evaluation metric.

### Signal
A published allocation recommendation for a model portfolio. Generated weekly.

### Sleeve
See "Asset Sleeve".

### Slippage
Price difference between decision and execution. Midas estimates half-spread slippage.

### SMA 200 (200-Day Simple Moving Average)
Price's average over 200 trading days. Trend filter. Midas tracks persistence above/below.

### Survivorship Bias
Error from using only currently-existing entities in historical analysis. Midas uses PIT universe to avoid this.

### TimescaleDB
Postgres extension for time-series data. Used for `bars`, `regime_signals`.

### TOTP (Time-Based One-Time Password)
MFA standard (RFC 6238). 6-digit code that changes every 30 seconds.

### Turbulent (Regime)
Highest regime level. Score > 0.65. All-cash allocation. Triggers escalation protocol.

### Turnover
Amount of portfolio rotated per period. Midas caps at 10% per sleeve per week.

### TWAP (Time-Weighted Average Price)
Execution algorithm that spreads orders over time. Midas doesn't use TWAP — market orders for ETFs.

### VIX
CBOE Volatility Index. Expected 30-day volatility implied by S&P 500 options. A regime signal.

### VIX3M
CBOE 3-Month Volatility Index. 90-day version of VIX. Ratio with VIX indicates contango/backwardation.

### Vol Target
Target annualized volatility for a portfolio. Midas portfolios: 6%, 10%, 14%, 18%.

### Walk-Forward Validation
Backtest method that trains on initial data, tests on subsequent, advances. Simulates real-time deployment.

### Whipsaw
Rapid back-and-forth price movement causing stop-loss or rebalance errors. Hysteresis prevents this.

### Yield Curve
Spread between long and short Treasury yields. Inversion = recession signal. Midas uses 3m10y spread.

## Technical terms

### AES-256-GCM
Symmetric encryption used for IBKR token storage. Authenticated encryption.

### API Gateway
Midas's main entry point. aiohttp-based in v1.

### Chain Hashing
SHA-256 linkage between audit records. Tamper-evident.

### Docker Compose
Tool for defining multi-container apps. Used for local Postgres + Redis.

### Editable Install
Python package installed with `-e` flag, so changes to source are immediately reflected.

### Grounding Contract
Midas's rule that every AI claim must cite a real database record. Post-generation verification.

### JWT (JSON Web Token)
Signed token for authentication. Midas uses HS256 (HMAC-SHA256).

### Kaizen Framework
The Kailash AI agent framework. Debate agent is built on Kaizen.

### LLM (Large Language Model)
The AI model powering the debate agent. MiniMax, OpenAI, Anthropic, etc.

### Nexus
The Kailash multi-channel deployment framework. Midas v1 uses aiohttp instead, migrating to Nexus in Phase 2.

### PACT (Policy, Access, Compliance, Trust)
Governance framework. Midas uses PACT envelopes for Postgres role separation.

### pgvector
Postgres extension for vector similarity search. Used for news embeddings.

### Provider Fallback Chain
MiniMax → ZAI → OpenAI → Anthropic. Tried in order until one succeeds.

### Pytest Asyncio
Plugin for testing async Python code.

### Row-Level Security (RLS)
Postgres feature that restricts which rows a role can see. Planned for `users.approvals`.

### Sanitization
Stripping dangerous content from external input (HTML, control chars, prompt injection).

### System Prompt
Instructions given to the LLM that shape its behavior. Not visible to the user.

### Tool Use (LLM)
AI pattern where the LLM can call functions (tools) to fetch data or take actions.

### UV (Python Package Manager)
Fast Python package manager by Astral. Used by Midas for venv management.

### Write-Ahead Log (WAL)
Postgres's transaction log. Redis has AOF as its equivalent.

---

## Appendix: Acronyms

| Acronym | Full |
|---|---|
| AAA | Adaptive Asset Allocation |
| ADV | Average Daily Volume |
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| AUM | Assets Under Management |
| BD | Broker-Dealer |
| CDN | Content Delivery Network |
| CPCV | Combinatorial Purged Cross-Validation |
| DSR | Deflated Sharpe Ratio |
| EOD | End of Day |
| ETF | Exchange-Traded Fund |
| ET | Eastern Time |
| FRED | Federal Reserve Economic Data |
| GFC | Global Financial Crisis |
| HRP | Hierarchical Risk Parity |
| HY | High-Yield |
| IBKR | Interactive Brokers |
| IG | Investment Grade |
| IPO | Initial Public Offering |
| JWT | JSON Web Token |
| KYC | Know Your Customer |
| LLM | Large Language Model |
| MFA | Multi-Factor Authentication |
| NYSE | New York Stock Exchange |
| OAS | Option-Adjusted Spread |
| OAuth | Open Authorization |
| OHLCV | Open, High, Low, Close, Volume |
| PBO | Probability of Backtest Overfitting |
| PIT | Point-in-Time |
| REIT | Real Estate Investment Trust |
| RIA | Registered Investment Adviser |
| SEC | Securities and Exchange Commission |
| SMA | Simple Moving Average |
| TLH | Tax-Loss Harvesting |
| TOTP | Time-Based One-Time Password |
| VIX | CBOE Volatility Index |
| WAL | Write-Ahead Log |

---

**End of User Guide**

Return to [README](README.md) for the table of contents.
