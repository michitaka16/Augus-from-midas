# Midas Platform — Analysis Synthesis

Ties together the six research streams in `01-research/` into a single decision surface for planning.

## 1. What Midas Is (after research)

A **publisher of impersonal, regime-aware, multi-asset ETF model portfolios**, delivered via web + mobile, with an interactive debate-with-AI layer and IBKR-native execution by the user (who clicks every trade in v1).

Critical framing change from the original brief: v1 CANNOT be "personalized autonomous portfolio manager." US regulatory research (03-broker-and-regulatory.md) shows the only legally-clean path without an RIA license is the **publisher's exemption** (Lowe v. SEC), which requires the server to be strictly impersonal: one set of model portfolios broadcast to all subscribers on a regular cadence. Personalization collapses the exemption and forces state RIA registration. The user's "go big" risk appetite, rebalance cadence, and debate preferences live client-side; the server never sees account balances or tax lots.

## 2. Value Propositions (locked)

1. **Regime-aware freeze-and-ask** — Unique. No competitor freezes auto-recommendations when an ensemble regime model flips turbulent and asks the user to override.
2. **Multi-horizon backtest transparency** — Every published signal is linked to a walk-forward + CPCV backtest over 2000–present, surfaced in the UI alongside the recommendation.
3. **Debate-with-AI with hard grounding** — Interactive conversational layer where every claim must cite a signal ID, backtest run ID, or cost model output. No hallucination escape hatch.
4. **IBKR-native, zero custody** — User keeps custody, tax lots, and reporting at IBKR. Midas never touches funds.
5. **Realistic cost modeling in-UI** — Commissions + SEC §31 + FINRA TAF + half-spread slippage + Almgren-Chriss impact + gap risk, shown per recommendation.

## 3. Unique Selling Points (what no competitor has combined)

- Publisher-style delivery + regime-aware freeze + debate-AI + multi-horizon backtests + IBKR-native, all in one product. Wealthfront/Betterment lack regime awareness and debate. Composer has regime logic but is BYO-portfolio with no debate. Interactive Advisors is cheap but doesn't explain itself. Titan is opaque.

## 4. Anti-USPs (things users might expect, we do NOT ship)

- Personalized risk scoring (v1 legal blocker)
- Tax-loss harvesting (v1 legal blocker, v2+ with RIA)
- Direct execution ("one-click" becomes "one-click approval → user executes at IBKR")
- Real-time quotes (screen-active pull only; not a day-trading tool)
- Options / leverage / single stocks (ETF universe only)

## 5. Target User (v1)

**Delegator who wants control**: self-directed HNW ($50k–$1M at IBKR), understands markets, doesn't want to monitor daily, wants to understand and argue with the system's reasoning. Not the Wealthfront "set and forget" persona. Not the QuantConnect DIY persona. A narrow but real segment.

## 6. Platform Thinking (AAA + network)

- **Automate**: Regime detection + allocator runs weekly without user involvement → reduces operational cost.
- **Augment**: Debate agent + transparent backtests → reduces decision cost.
- **Amplify**: Impersonal publisher model lets one research pipeline serve every subscriber → reduces expertise cost per user.
- **Network effects (weak in v1)**: Impersonal delivery means every subscriber gets the same signal simultaneously. No producer-consumer network. Possible future: community debate transcripts, subscriber overlay portfolios (v3+ with proper licensing).

## 7. The 80/15/5 Split

- **80% reusable core** (framework): data fabric, backtest engine, regime detection, allocator, cost model, debate agent, audit trail, IBKR connector.
- **15% client-configurable** (self-service): which model portfolio to subscribe to, notification cadence, approval preferences, debate depth.
- **5% customization** (per jurisdiction when we expand): compliance wrappers, disclosure text, geofencing, currency handling.

## 8. Failure Modes (each must fail-closed)

| Failure | Fail-closed behavior |
|---|---|
| EODHD down | Reject new signal publication; serve cached signal until market close |
| Perplexity rate-limited | Debate agent degrades gracefully — "news context unavailable", still cites signals |
| IBKR OAuth fails | Approval flow shows "broker link down, re-authenticate"; no auto-retry with stale token |
| Regime ensemble disagrees | Cautious regime by default; no aggressive rotation |
| Backtest regression in CI | Block signal publication until investigated |
| Cost model predicts fills > 2x historical for 4+ weeks | Auto-page ops, pause publication |

## 9. Open Questions Remaining

Tracked in `03-gaps.md`. Key: IBKR OAuth production approval gating for multi-tenant SaaS; Perplexity cost scaling at 1000+ users; whether v2 RIA path is worth the 6–12 month compliance build.
