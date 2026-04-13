# Risk Register — Midas Platform

Ranked by severity × likelihood. Every item has an owner, a mitigation, and a tripwire signal.

## R1 — CRITICAL — Publisher exemption slide
Any line of code or product feature that personalizes signals per user (account-balance-aware, tax-aware, "your" portfolio) collapses Lowe v. SEC and turns v1 into an unregistered RIA.
- **Mitigation**: `signals` schema has no `user_id` FK, Postgres role separation enforced at DB level (ADR-009), legal copy review on every marketing change, CI lint on server-side code that imports both `signals` and `users` modules.
- **Tripwire**: Any PR diff that joins `signals` to `users.*` fails CI.

## R2 — CRITICAL — Backtest↔live drift
TAA strategies historically decay out-of-sample. Even worse if backtest and live run different code paths (different rounding, different cost model, different data source).
- **Mitigation**: ADR-005 single-workflow design with `TimeSourceNode` as the only variable. Tier-2 regression tests on real Postgres gate every merge. Every live signal is reproducible via backtest replay.
- **Tripwire**: Nightly replay job runs yesterday's live signal through the backtest engine; variance > tolerance pages ops.

## R3 — HIGH — IBKR OAuth production approval gating
IBKR approves OAuth production credentials selectively. An unregulated SaaS may be stuck in sandbox indefinitely.
- **Mitigation**: Begin IBKR application conversation during v1 development, not after. Fallback: per-user local CP Gateway for private beta.
- **Tripwire**: If OAuth approval is not in-hand 60 days before public launch, delay launch.

## R4 — HIGH — Hallucination in debate agent
If the debate agent ever invents a number, fabricates a backtest result, or cites a non-existent signal, the product's trust collapses.
- **Mitigation**: Hard grounding contract (ADR-008). Every response must cite IDs that resolve server-side; any response with non-empty `ungrounded_claims` is rejected before reaching the user. Tools return only facts; the LLM composes natural language around them.
- **Tripwire**: Grounding assertions in CI run against sample conversations. Any failure is a release blocker.

## R5 — HIGH — Approval fatigue in turbulent mode
A regime flip may produce 6–8 correlated trades. Sending 6–8 individual approval cards burns the user out and they either bulk-approve without reading or abandon.
- **Mitigation**: Grouped rebalance card with per-item opt-out + biometric "approve entire rebalance" escape hatch. Always preceded by a regime-change explainer.
- **Tripwire**: Approval abandonment rate > 15% in any 30-day window triggers UX review.

## R6 — HIGH — Survivorship bias inflates backtests
Without point-in-time ETF listings, backtest results are systematically inflated and the "go big" risk profile becomes dangerous in live.
- **Mitigation**: EODHD delisted-tickers ingestion from day 1. Nightly audit: every backtest must pass a PIT join test or it fails.
- **Tripwire**: CI test that rebuilds a fixed backtest and compares to golden hash.

## R7 — MEDIUM — Perplexity cost scaling
News ingestion cost grows linearly with users and can dominate the monthly bill.
- **Mitigation**: Aggressive dedup caching, time-decay TTLs, self-hosted RSS + FinBERT fallback path already scoped.
- **Tripwire**: Monthly Perplexity spend > 60% of total infra budget.

## R8 — MEDIUM — Stock-bond correlation regime break
2022-style regime where bonds fail as equity hedge. The ensemble's cross-sector PC1 signal will lag the first shock.
- **Mitigation**: PC1 signal in the ensemble catches the transition; drawdown hard override backstops.
- **Tripwire**: 21-day rolling correlation between SPY and TLT exceeds +0.3 → force cautious regime regardless of ensemble.

## R9 — MEDIUM — Yahoo Finance as fallback is legally/technically fragile
`yfinance` has no SLA and commercial use is gray-area.
- **Mitigation**: Use Yahoo only as reconciliation check, not as primary. Budget a paid secondary (Polygon or Tiingo) before commercial launch.
- **Tripwire**: Yahoo disagreement rate with EODHD > 1% for any ticker triggers investigation.

## R10 — MEDIUM — Overfitting via ensemble hyperparameter tuning
8 signals × thresholds × hysteresis × vol targets × K = enormous parameter surface.
- **Mitigation**: CPCV + embargo + Deflated Sharpe + PBO report on every ensemble change. No ensemble change ships without a PBO below a fixed threshold.
- **Tripwire**: PBO > 0.5 on any candidate ensemble blocks merge.

## R11 — LOW — Kaizen missing grounded-citation primitive
Hand-built in v1, potential upstream contribution.
- **Mitigation**: Ship Midas-local implementation; propose upstream PR post-launch.

## R12 — LOW — PACT envelope → Postgres role sync drift
Manual SQL migrations can drift from PACT envelope definitions.
- **Mitigation**: Single migration file is the source of truth; envelope definition documents it. Nightly audit compares the two.

## R13 — LOW — Competition from IBKR Interactive Advisors
IBKR's own robo is cheap and sits in the same account. Midas must differentiate visibly.
- **Mitigation**: Landing page leads with regime-aware freeze + debate + backtest transparency — things IA does not do.
