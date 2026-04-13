# Red Team — Technical Architecture Review

**Date**: 2026-04-12
**Scope**: All analysis docs, ADRs, risk register, phase roadmap, monorepo layout
**Posture**: Adversarial. Assume everything will break.

---

## CRITICAL

### C1 — PACT envelope to Postgres GRANT is manual and unverifiable at runtime

ADR-009 admits PACT does not auto-generate GRANT/REVOKE SQL. The entire Lowe v. SEC legal posture depends on the publisher role never reading `users.*`. A single migration error — one forgotten REVOKE, one new table added without updating the role — collapses the publisher exemption. The "nightly audit" in R12 is listed as LOW priority, which is wrong given the consequence is CRITICAL (R1).

**Why it matters**: The legal architecture's structural guarantee is actually a process guarantee. Process guarantees fail on the first missed migration.

**Fix**: (a) Promote R12 to CRITICAL. (b) Write a startup assertion (not nightly — every process boot) that queries `information_schema.role_table_grants` and fails the application if the publisher role can see any table in the users/positions/orders namespace. (c) Add a CI check that parses the PACT envelope definition and the migration SQL and asserts they match. This is cheaper than the upstream PACT extension and ships in v1.

### C2 — Live data quality vs backtest adjusted data is unaddressed

The "single workflow, TimeSourceNode injected" design (ADR-005) claims parity, but the docs never address what happens when the live path encounters:

- **Corporate actions intra-week**: A stock splits Wednesday; the live allocator runs Friday with 3 days of split-adjusted and 2 days of raw data in the same window. The backtest sees a clean adjusted series.
- **Late EODHD bar corrections**: 04-data-fabric.md acknowledges EODHD restates bars within 24h but the live signal runs once and does not re-run after correction.
- **Partial bars / data gaps**: Live EODHD fetch may return a partial day (early close, exchange halt). The backtest fills these from the clean historical archive.
- **Dividend ex-date alignment**: Total return series in the backtest use perfectly aligned ex-dates; live sees the price drop on ex-date before EODHD publishes the adjusted close.

**Why it matters**: This is not a theoretical concern. Every quant fund that has gone live with a "same code" backtest has encountered this class of issue. The backtest will always look 20-50 bps better per annum than live due to data quality asymmetry alone.

**Fix**: (a) Add a `DataQualityGateNode` between `PriceHistoryNode` and `MomentumScoreNode` that flags corporate actions within the lookback window and forces the allocator to use raw (unadjusted) returns with explicit adjustment factors rather than relying on pre-adjusted close. (b) Document the expected live-vs-backtest decay budget (e.g., 30 bps/year) and alert when exceeded. (c) The nightly replay (R2 tripwire) must use the SAME data snapshot the live run used, not today's corrected data — otherwise the replay will always pass.

### C3 — IBKR OAuth token storage and rotation is never specified

03-broker-and-regulatory.md describes the OAuth 1.0a flow but the architecture docs never state:

- Where access tokens are stored (Postgres? Redis? Filesystem?)
- Whether they are encrypted at rest
- What the refresh/re-auth cadence is (IBKR OAuth tokens expire; the session keep-alive is documented as fragile)
- Whether token theft from the database grants order-submission capability

The monorepo layout has `midas-broker/ibkr/` but no mention of a secrets vault, HSM, or even envelope encryption.

**Why it matters**: An attacker who compromises the database gets every user's IBKR OAuth token and can submit trades on their behalf. This is a custody-adjacent risk that could trigger the exact regulatory scrutiny the Lowe posture is designed to avoid.

**Fix**: (a) Tokens encrypted at rest with a KMS-managed key (AWS KMS, GCP KMS, or Vault transit). (b) Tokens stored in a separate schema with its own Postgres role — not readable by the publisher or subscriber roles. (c) OAuth scope restricted to the minimum (read positions, preview order, place order — no withdrawal, no money movement). (d) Token rotation: re-auth every 24h or on any 401. (e) Add to risk register as HIGH.

### C4 — Audit trail truncation is unprotected

R1 mentions append-only audit, but there is no mechanism preventing:

- A Postgres superuser or the `midas` admin role from running `TRUNCATE audit_log` or `DELETE FROM audit_log`
- TimescaleDB `drop_chunks()` being misconfigured to drop audit chunks
- A compromised migration script wiping audit history

The EATP chain-store hash-linking is described as "optional" in 06-framework-architecture.md component 12.

**Why it matters**: When Midas becomes an RIA (v2), SEC examiners will request the audit trail. If it can be tampered with, the entire compliance posture is undermined. Even in v1, if a user disputes a recommendation, the audit trail is the only evidence.

**Fix**: (a) Make EATP chain-store hash-linking mandatory, not optional. (b) The admin Postgres role must NOT have TRUNCATE or DELETE on `audit_log` — use a write-only role. (c) Ship audit records to an immutable external sink (S3 with Object Lock, or a separate append-only database) as defense-in-depth. (d) Add a CI assertion that no migration contains DELETE/TRUNCATE on `audit_log`.

---

## HIGH

### H1 — Regime ensemble hysteresis deadlock is not addressed

Strategy doc section 2.9 specifies 2-day hysteresis. The risk register (R8) addresses stock-bond correlation but not the core ensemble failure: what happens when signals oscillate around the threshold for >2 days?

Scenario: Day 1 score = +0.31 (Turbulent), Day 2 = +0.28 (Cautious), Day 3 = +0.32 (Turbulent), Day 4 = +0.27 (Cautious). The 2-day persistence requirement is never met. The system is stuck in whatever regime it was in before the oscillation started. If it was "Normal", it stays Normal while multiple signals are screaming caution.

**Why it matters**: This is exactly the scenario that precedes a crash — VIX rising but choppy, credit widening then tightening, trend crossing back and forth. The system stays in Normal while the user expects it to protect them.

**Fix**: (a) Add a "sustained ambiguity" rule: if the ensemble score is within 0.1 of a boundary for >3 days, escalate to the more conservative regime regardless of hysteresis. (b) Add an explicit "oscillation count" metric — if regime flips >3 times in 10 days, force Cautious. (c) Test this scenario in the backtest stress suite against 2018 Q4 and 2015-16 China/oil, which exhibited exactly this pattern.

### H2 — Perplexity two-hop citation problem

04-data-fabric.md says Perplexity citations "MUST be persisted for audit." But Perplexity's citations are URLs to news articles that Perplexity summarized. The debate agent then cites Perplexity's summary, not the original article. This creates a two-hop citation chain:

User sees: "According to Midas analysis, gold is rising due to central bank buying [1]"
[1] points to: Perplexity's synthesis, which itself cited Reuters and FT articles

If Perplexity's summary is wrong or hallucinated, Midas inherits the error and the user has no way to verify without clicking through two layers.

**Why it matters**: The grounding contract (ADR-008) verifies that `cited_signal_ids` resolve. It does NOT verify that Perplexity's original citations are still live, accurate, or correctly summarized. The "zero ungrounded claims" guarantee is only as strong as Perplexity's accuracy.

**Fix**: (a) Persist Perplexity's source URLs alongside the summary in `news_items.citations`. (b) The debate agent's citation cards must show both the Perplexity synthesis AND the original source URLs. (c) Add a periodic link-rot checker on persisted citations. (d) The grounding contract should flag any news item older than 48 hours as "unverified freshness" and the LLM should disclose this.

### H3 — FRED data latency vs regime detection expectations

FRED series used for regime detection:
- HY OAS (`BAMLH0A0HYM2`): published with 1-day lag, updated daily
- Credit spreads: same lag
- Yield curve (`DGS*`): published next business day
- VIX: available from CBOE EOD, also in FRED with 1-day lag

The regime ensemble weights HY OAS at 0.25 (highest single weight). On a Friday close, the HY OAS value available is Thursday's. The ensemble is making Friday's regime decision on Thursday's credit data.

**Why it matters**: In March 2020, HY OAS moved 100+ bps in a single day. A 1-day lag on a 0.25-weighted signal means the regime detector is systematically late by 1 day in exactly the scenarios where speed matters most (crisis onset).

**Fix**: (a) Document the lag explicitly in the regime detector's configuration and the backtest (ensure the backtest also uses T-1 publication dates, not T-0 values). (b) Use CBOE's direct VIX feed (available intraday from EODHD index endpoint) as the fast signal, and weight it higher during the first 48 hours of a potential regime change. (c) Consider a "proxy HY OAS" derived from HYG ETF price changes (available real-time from EODHD) as a leading indicator for the actual OAS publication.

### H4 — EODHD delisted-tickers endpoint is unverified

ADR-010 and 04-data-fabric.md both state "EODHD delisted-tickers ingestion from day 1." The data fabric doc says "EODHD provides a delisted-tickers endpoint." But the research caveat says "WebSearch was not available in this session."

EODHD's actual API surface should be verified. If the delisted-tickers endpoint does not exist, does not cover US ETFs, or does not go back to 2000, the entire survivorship-bias mitigation (R6) collapses and every backtest result is inflated.

**Why it matters**: Survivorship bias is typically 1-2% annualized on US equities. On a concentrated momentum strategy, it can be 3%+. An inflated backtest misleads the user about risk.

**Fix**: (a) Before any implementation session, verify the EODHD API docs for `exchange-symbol-list` and `delisted` endpoints. (b) If the endpoint does not exist, identify an alternative (SEC EDGAR full-text search for ETF delistings, Nasdaq's delisted companies list, or a manual scrape from ETF.com). (c) Add a backtest integrity test: run the 2000-2010 window with and without delisted tickers and assert the Sharpe difference is <0.15. If it is larger, the survivorship bias is material and must be disclosed.

### H5 — Prompt injection via debate agent tools

The DebateAgent has 7 tools including `fetch_news_by_similarity` which returns news headlines and bodies from Perplexity. An attacker who can influence news content (e.g., by publishing a crafted article that Perplexity indexes) could inject instructions into the LLM context via the news body.

Additionally, the `fetch_counterfactual_backtest` tool accepts an `override: dict` parameter. The LLM decides the override content based on user input. A user could craft a message that causes the LLM to pass malicious overrides (e.g., extreme weights, negative weights, weights summing to >1) that crash the backtest or produce misleading results.

**Why it matters**: The debate surface is the product's differentiator. If it can be manipulated to produce false confidence in a bad trade, the user loses money and the product loses credibility.

**Fix**: (a) Input validation on `fetch_counterfactual_backtest`: override weights must be in [0, 1], sum to <=1, only contain valid ticker symbols from the universe. This is structural validation (permitted by agent-reasoning.md exception 1), not LLM routing. (b) News bodies passed to the LLM should be sanitized — strip any content that looks like instruction injection (sequences containing "ignore previous", "system:", "you are", etc.). (c) Rate-limit counterfactual backtests per user per hour to prevent resource exhaustion. (d) Add adversarial prompt injection tests to the debate agent test suite.

### H6 — Redis cache invalidation contract is underspecified

04-data-fabric.md describes TTLs (60s for latest bar, 5 min for fundamentals, 1 hour for news) but does not specify:

- Who writes to Redis? The ingestion workflow? The API handler? Both?
- What happens on a cache stampede (1000 users open screen simultaneously, all miss cache)?
- Is there a write-through or write-behind pattern?
- What if Redis goes down — does the API fall through to Postgres or return an error?

**Why it matters**: An underspecified cache is worse than no cache. Stale reads on financial data cause users to see outdated prices and make decisions on wrong information.

**Fix**: (a) Specify the write pattern: ingestion workflows write-through to Redis on every successful Postgres insert. API handlers read-only from Redis, fall through to Postgres on miss. (b) Use Redis `SETNX`-based locking for cache population to prevent stampede. (c) If Redis is down, the API serves from Postgres with a latency warning in the response header. (d) Add a health check that pages ops if Redis is unreachable for >60 seconds.

### H7 — No churn mitigation for sustained underperformance

The risk register has no entry for: "strategy underperforms buy-and-hold SPY for 12 months straight." This is not hypothetical — momentum strategies had a terrible 2009-2012 stretch (reversal regime) and 2017-2019 (low-dispersion regime).

**Why it matters**: Users paying for Midas who see SPY outperform for a year will cancel. The product has no answer for this beyond "trust the process."

**Fix**: (a) Add R14 to the risk register at MEDIUM. (b) The debate agent should be able to explain why the strategy underperformed (regime analysis, dispersion analysis) proactively, not just when asked. (c) Build a "performance attribution vs benchmark" view that shows whether underperformance is from regime detection (conservative → missed rally) or allocation (wrong sleeves). (d) Consider a "benchmark-aware" model portfolio option that never deviates more than X% from a 60/40, for users who want the regime protection without the full active bet.

### H8 — IBKR Client Portal API instability risk

IBKR has changed the Client Portal API multiple times (2019 session model change, 2023 headless mode addition, 2024 endpoint deprecations). The risk register has no entry for API breakage.

**Why it matters**: If IBKR deprecates an endpoint, every user's order flow breaks simultaneously. The local Gateway fallback (ADR-002) helps for auth but does not help if the underlying REST API changes.

**Fix**: (a) Add R15 to the risk register at HIGH. (b) Build an IBKR API integration test suite that runs daily against the paper account and pages on any 4xx/5xx or schema change. (c) Abstract the IBKR client behind a broker interface so that (i) a mock can be swapped in for testing and (ii) a second broker can be added without rewriting the strategy layer. (d) Pin the CP Gateway version and test upgrades before deploying.

---

## MEDIUM

### M1 — Monorepo package boundaries create a diamond dependency

The dependency graph shows `midas-debate` depends on `midas-strategy` (for signal/backtest data) and `midas-data` (for models). `midas-strategy` also depends on `midas-data`. This is a diamond: `midas-debate -> midas-strategy -> midas-data` AND `midas-debate -> midas-data`. If `midas-data` model definitions change, both paths must be updated atomically or type mismatches occur.

**Fix**: Accept the diamond but enforce it: `midas-debate` should depend only on `midas-strategy` (which re-exports the data types it needs), not directly on `midas-data`. Or: extract shared types into a `midas-types` package that all others depend on.

### M2 — DuckDB backtest acceleration is mentioned but unplanned

06-framework-architecture.md says "DuckDB as a query engine, not a store" for heavy backtests. The monorepo has no `midas-analytics` package and no plan item for DuckDB integration. Walk-forward CPCV with 756-day embargo on 25 years of data across 20+ instruments will be slow on pure Postgres.

**Fix**: Add a Phase 1 spike to benchmark the CPCV driver on Postgres. If a single CPCV run exceeds 10 minutes, add DuckDB Parquet materialization to the Phase 1 deliverables.

### M3 — No rate-limit strategy for EODHD at scale

04-data-fabric.md mentions "max 1 refresh per 10s per symbol, max 60 req/min per user" but the EODHD plan is ~100k calls/day. At 1000 users with aggressive screen-open patterns and a 3000-instrument universe, the nightly backfill alone could consume 10-20k calls. The per-user throttle protects against burst, but there is no global EODHD budget allocation between ingestion, backfill, reconciliation, and user-triggered refresh.

**Fix**: Implement a global EODHD request budget with priority queues: (1) scheduled ingestion, (2) gap backfill, (3) reconciliation, (4) user-triggered refresh (lowest). Monitor daily usage and alert at 80% of quota.

### M4 — The 10-day minimum hold period is not cost-optimal

Strategy doc 4.3 specifies a 10-trading-day minimum hold. But the cost model shows round-trip costs of 6-15 bps. For a sleeve with a 1%+ momentum shift in 3 days, the min-hold forces the allocator to ignore a signal that would more than cover transaction costs. This is an anti-whipsaw rule that may cost more than it saves in trending regimes.

**Fix**: Make the min-hold period regime-conditional: 10 days in Cautious, 5 days in Normal, 0 in Turbulent (since Turbulent already freezes trading). Backtest the sensitivity.

### M5 — No monitoring for PACT envelope violations in production

The architecture describes PACT fail-closed behavior, but there is no operational monitoring for how often violations occur, what triggers them, or whether legitimate operations are being blocked. In production, a false-positive PACT block on the signal publication workflow would silently prevent new signals from being published.

**Fix**: Every PACT fail-closed event must emit a structured log and increment a Prometheus counter. Alert if the publisher envelope blocks >0 operations in any 24-hour window (it should never block in normal operation — any block indicates either a bug or a real security event).

---

## LOW

### L1 — Shared TypeScript types package has no generation pipeline

`shared/types/` is listed but there is no mechanism to keep TypeScript types in sync with Python DataFlow models or Pydantic schemas. Manual sync will drift.

**Fix**: Use a code-generation step (e.g., `datamodel-code-generator` or a custom script) that reads the Python models and emits TypeScript interfaces. Run in CI.

### L2 — No load testing plan

The phase roadmap has no load testing phase. At 1000 users, the signals endpoint (CDN-cacheable) is fine, but the debate agent (per-user, LLM-backed) could be a bottleneck.

**Fix**: Add a load test spike to Phase 6 targeting 50 concurrent debate sessions.

### L3 — Gap risk in cost model is attribution, not cost

Strategy doc 5.5 acknowledges gap risk is "not a cost in the commission sense" but it appears in the `total_bps` sum of `TransactionCostNode`. This inflates the turnover penalty and makes the allocator more conservative than intended.

**Fix**: Separate gap risk from the cost function. Use it for attribution reporting but not for the L1 turnover penalty lambda calibration.

### L4 — No circuit breaker on the counterfactual backtest tool

`fetch_counterfactual_backtest` runs an actual backtest. A user who asks "what if I had 100% in TLT" triggers a full walk-forward run. At scale, this is a denial-of-service vector against the compute tier.

**Fix**: (a) Cap counterfactual backtests to a 1-year lookback. (b) Queue them with a per-user concurrency limit of 1. (c) Cache results by (override_hash, lookback_window) with a 1-hour TTL.
