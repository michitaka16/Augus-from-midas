# 03 — Your First Week

Your first week with Midas is a trust-building exercise. The system will publish signals but you're not executing trades yet. Here's the recommended sequence.

## Day 1: Sign up and pick a portfolio

1. **Go to http://localhost:3000/signup**
2. **Create an account** with email + password (8+ characters)
3. **Log in** — you'll land on the Dashboard
4. **Go to Settings** (left sidebar)
5. **Pick a model portfolio**. If you're unsure, start with **Growth** — it's the default and has the broadest mandate. You can switch anytime.
6. **Review the timeout setting** — this is how long the system waits during a turbulent regime before auto-executing a defensive move. Default is 24 hours. If you travel frequently or don't check notifications, set it to 48h or 72h.
7. **Enable paper trading** (it's on by default). This means for your first 2 weeks, no real money moves even if you link IBKR.

## Day 2-3: Understand the dashboard

Open the Dashboard. You'll see:

### Top banner: Current regime
A colored stripe at the top:
- **Green "Normal"**: Risk-on. The system is allocating across momentum leaders.
- **Yellow "Cautious"**: Elevated stress. The system is reducing risk.
- **Red "Turbulent"**: Crisis. The system has frozen pending your input (or will execute defensive after timeout).

Click into the regime number to see the 8 underlying signals.

### Stat cards
Three cards:
1. **Regime** — current level + date last updated
2. **Latest Signal Cost** — what the most recent rebalance cost you in fees/slippage/impact
3. **Pending Approvals** — how many signals are waiting for you to decide

### Current Allocation
A bar chart of your model portfolio's current target weights across 10 asset sleeves:
- Equity Sectors (SPY)
- Precious Metals (GLD)
- Government Bonds Short/Intermediate/Long (SHY/IEF/TLT)
- IG Corporate Bonds (LQD)
- REITs (VNQ)
- Commodities (DJP)
- Dividend ETFs (VYM)
- Emerging Markets Equity (VWO)

The allocation updates weekly when new signals publish.

## Day 4: Read the current signal

Click **Signals** in the sidebar.

You'll see:
- The latest published signal for your portfolio
- Which sleeves are in the allocation and their target weights
- The regime detected when this signal was generated
- The cost estimate for rebalancing into this allocation
- The reasoning object (what drove each decision)

Take 5 minutes to understand why the allocation is what it is. Example reasoning:
> "HY OAS at 420bps (below 500bps threshold). VIX3M in contango. Cross-sector PC1 stable. Regime: normal. Top-6 momentum selection: equity_sector (+12% 6m), precious_metals (+8%), em_equity (+6%)..."

## Day 5: Debate the signal (Phase 2)

*If you have an LLM API key configured.*

Click **Debate** in the sidebar.

Try these queries:
- "Why is precious_metals ranked so high this week?"
- "What would happen if I skip this rebalance?"
- "Show me the backtest for Growth over 5 years"
- "What signals are closest to flipping the regime?"

The AI will respond with citations like `[cite: signal_123]` or `[cite: backtest_45]` — these are clickable and take you to the underlying data.

**Push back on the AI.** Try:
- "I think we should go all-in on gold" (it will ask for evidence)
- "Commodities are a bad idea" (it will show you the momentum data)
- "Sell everything, I'm nervous" (it will explain the cost of market-timing)

The AI is designed to defend positions with data, not to agree with you.

## Day 6: Review the backtest (Phase 2)

Click **Backtests** in the sidebar.

The Backtest Explorer shows your portfolio's historical performance:
- **1-year, 3-year, 5-year, 10-year, full** horizons
- Sharpe, Max Drawdown, Turnover, Cost Drag, Total Return per horizon
- Deflated Sharpe + PBO (overfitting checks)
- Worst 12-month rolling return (the stress test)
- Side-by-side vs 60/40, Equal Weight, VTI benchmarks

**Key numbers to check:**
- **Sharpe > 0.5** — the strategy generates risk-adjusted returns
- **PBO < 40%** — not likely overfit
- **Beats 60/40** — outperforms the simplest benchmark net-of-costs
- **Max DD** — can you stomach this loss? If the portfolio drew down 25% during 2008, ask yourself if you'd have stayed invested

If any of these fail the gate, the portfolio isn't shippable. Pick a different one.

## Day 7: Decide whether to connect IBKR

Two paths:

### Path A: Continue in paper trading
Keep paper trading enabled. The system will continue to publish signals. You can manually track how well you'd have done by mirroring the allocation in your existing brokerage account. No real money at risk.

### Path B: Link Interactive Brokers
1. Go to Settings → Broker Connection
2. Click "Link Account"
3. You'll be redirected to IBKR's OAuth page
4. Authorize Midas with these scopes:
   - Read positions
   - Preview orders
   - Place orders
5. Midas will NOT have withdrawal or funding permissions — just trading.

Once linked, the app can compute order deltas when a signal publishes (client-side) and submit trades when you approve them.

## What happens in week 2

### Sunday 7 PM ET: First signal publishes

You'll get a notification:
> "Growth signal published for 2026-04-19. 3 trades recommended. Regime: normal."

Open the app. Go to Approvals.

### The approval card

You'll see a grouped rebalance card with:
- The regime banner at the top
- Portfolio name ("Growth")
- Number of trades and estimated cost
- Each trade (buy GLD 15 shares, sell TLT 8 shares, etc.)
- A checkbox next to each — you can uncheck any individual trade
- Two buttons: **Skip** and **Approve All**

### Reviewing trades

Before approving, ask yourself:
- **Does the regime make sense?** If the UI says "Normal" but your gut says markets are panicking, check the Debate agent — maybe it's seeing something you missed, or maybe the signals are lagging.
- **Are the trades reasonable?** If the system says "sell 80% of your portfolio", that's a huge red flag. Check Debate.
- **Is the cost estimate reasonable?** For a $100k portfolio, weekly rebalance costs should be $3-$10. If it's $50+, something's off.

### Approving

Click "Approve All". If IBKR is linked and you're in real trading mode, you'll get a biometric prompt (Face ID / Touch ID on mobile, WebAuthn on desktop). Confirm.

The system will:
1. Submit market orders to IBKR (ETFs only — limit orders add complexity without benefit for ETF rebalancing)
2. Poll for fill confirmation
3. Write every step to the audit trail
4. Update the dashboard with new positions

If any order fails, the app stops and asks you what to do. It doesn't auto-retry.

## What to expect in a normal week

- **99% of signal days**: Green banner, small rebalance, total cost $3-$10, you click Approve and go back to your day. Takes 2 minutes.
- **1 in 10 weeks**: Yellow banner. System is reducing risk. Check the regime signals, understand why. Maybe debate the change if you disagree. Approve or skip.
- **Once or twice a year**: Red banner. Turbulent regime. The system froze. You have 24h (or your timeout) to decide. Options:
  - Approve the defensive move (cash + short bonds)
  - Reject it (stay in current allocation — your call)
  - Hold (acknowledge but delay — resets timer)
  - Do nothing → auto-defensive executes at timeout

## What you should NOT do in your first month

- **Don't panic-sell during the first turbulent regime**. The system has been tested across 26 years including 2008, 2020, 2022. Trust the data, not your gut. If you disagree, use the Debate agent to surface what you think the system is missing.
- **Don't switch portfolios weekly**. Each switch creates turnover costs. Pick one and stick with it for at least a quarter.
- **Don't disable notifications for turbulent regimes**. These are the ONLY notifications you'll get — the system is designed not to spam you. Turning them off defeats the point.
- **Don't over-optimize**. The 5 model portfolios already represent the full risk spectrum. Don't try to build a "custom" allocation by combining them — they're not designed to compose.

---

**Next**: [04 — The Dashboard](04-dashboard.md)
