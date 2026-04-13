# Red Team Convergence — Resolutions

7 CRITICALs surfaced across product (05) and technical (06) red teams. Each is addressed below with a resolution that will feed into `/todos`.

---

## PC1 (Product C1): Turbulent freeze has no timeout

**Problem**: User says "don't trade without permission" AND "I don't want to monitor it." If user ignores a turbulent notification for 3 days during a crash, the system freezes while positions bleed.

**Resolution**: Configurable escalation protocol with 3 tiers:
1. **T+0h**: Regime flip notification (push + email + in-app)
2. **T+12h**: Reminder with updated loss estimate since freeze
3. **T+24h (default)**: Auto-execute the defensive rebalance (move to cash + short bonds) unless user explicitly chose "hold current"

The 24h timeout is configurable in settings (12h–72h range). User confirmed shorter default is preferred — in March 2020 the S&P lost 12% in 2 trading days, so 24h is already generous. This resolves the tension: the system asks permission first, but if you don't answer, it protects you. The auto-defensive action is always the CONSERVATIVE move (reduce risk), never the aggressive one.

**ADR impact**: New ADR-011 (turbulent escalation protocol). User flow 3 updated.

---

## PC2 (Product C2): AAA alpha asserted, not tested against null

**Problem**: Walk-forward Sharpe > 0.5 gate doesn't address whether AAA beats static 60/40 net of costs. PBO < 0.4 threshold unjustified.

**Resolution**:
1. **Mandatory benchmark comparison**: Every backtest report includes side-by-side vs static 60/40, vs equal-weight 8-sleeve, vs VTI-only. If AAA fails to beat 60/40 net-of-costs over the full horizon, we do not ship that model portfolio.
2. **PBO threshold justification**: Adopt López de Prado's recommendation of PBO < 0.40 for production strategies (consistent with published empirical work). Document the threshold source.
3. **Year-1 underperformance plan**: If any model portfolio underperforms its benchmark for 6 consecutive months, automatically publish a "strategy health" dashboard entry showing the divergence, regime attribution, and cost drag. Transparency is the churn mitigation — hiding underperformance is worse.
4. **Honest marketing**: Landing page includes "past performance does not guarantee future results" AND shows worst 12-month rolling period, not just cumulative returns.

**ADR impact**: ADR-010 amended (benchmark gates). Phase 2 gate condition updated.

---

## PC3 (Product C3): Client-side order preview may collapse publisher exemption

**Problem**: Showing "what this signal means for YOUR holdings" (computed client-side from position sync) may constitute personalized advice under SEC scrutiny.

**Resolution**:
1. **Legal opinion required**: This CANNOT be resolved by engineering. Before v1 ships commercially, a securities attorney must opine on whether client-side computation using impersonal signals + user's own IBKR position data constitutes "personalized investment advice."
2. **Architectural safeguard**: The order preview is computed ENTIRELY in the React Native / Next.js client. The server never sees the user's positions, holdings, or account balance. The server sends impersonal signals; the client overlays them on locally-fetched IBKR positions. The API never joins these.
3. **Fallback if legal says no**: Remove the order preview. Show only the model portfolio target allocation. User computes their own delta manually. Uglier but legally unambiguous.
4. **Phase gate**: Legal opinion is a Phase 6 gate. Code can be built in Phase 4 behind a feature flag.

**ADR impact**: New ADR-012 (legal opinion gate on order preview). Phase 6 gate updated.

---

## TC1 (Technical C1): PACT-to-Postgres GRANT sync is manual

**Problem**: The Lowe legal posture rests on the publisher Postgres role not having SELECT on `users.*`. This is enforced by manual migrations, not structural assertions.

**Resolution**:
1. **Boot-time assertion**: On API startup, query `information_schema.role_table_grants` and assert the publisher role has zero grants on any table in the `users` schema. Fail to start if violated.
2. **CI check**: GitHub Actions job runs the same assertion against a fresh migration. Any PR that adds a grant from publisher to users fails CI.
3. **PACT envelope audit**: Nightly job compares PACT envelope definitions to actual Postgres grants. Drift = PagerDuty alert.

This converts a process guarantee into a structural one. The legal posture is now enforced by code, not policy.

**ADR impact**: ADR-009 amended (boot-time + CI assertion).

---

## TC2 (Technical C2): Live data quality vs backtest adjusted data

**Problem**: Backtests use clean, adjusted, post-correction data. Live runs use raw data with partial bars, late corrections, and intra-week corporate actions. The nightly replay job uses corrected data, not the snapshot live actually consumed.

**Resolution**:
1. **Snapshot-on-consume**: When the live signal workflow runs, it snapshots the EXACT input data (bar values, signal values) into an immutable `signal_inputs` table BEFORE computing. This is the audit trail.
2. **Replay uses snapshot**: The nightly replay job runs against the snapshot, not current corrected data. This catches bugs in the live code path, not just the data.
3. **Backtest degraded-data mode**: Quarterly, run the backtest with simulated data-quality issues (1-day lag on credit spreads, 0.1% noise on bars, missing Friday bars) to measure sensitivity. If degraded performance drops Sharpe by > 0.15, the strategy is too fragile for live.
4. **Corporate action handler**: Intra-week splits/dividends detected by comparing EODHD corp_actions table against last-seen values. If a corp action happened mid-week, the signal workflow re-fetches and re-computes before publishing.

**ADR impact**: ADR-005 amended (snapshot-on-consume + degraded-data mode).

---

## TC3 (Technical C3): IBKR OAuth token storage unspecified

**Problem**: Compromise of the token store gives trade-submission capability for every user.

**Resolution**:
1. **Encryption at rest**: OAuth tokens (access + refresh) stored in a dedicated `user_tokens` table, AES-256-GCM encrypted with a key from environment variable (never in DB).
2. **Token column is BYTEA, not TEXT**: Prevents accidental logging or SELECT * exposure.
3. **Refresh token rotation**: On every token refresh, the old refresh token is invalidated. Single-use refresh tokens.
4. **Scope minimization**: Request only `read positions` + `preview order` + `place order` scopes. No withdrawal, no ACH, no funding.
5. **Separate Postgres role**: The `user_tokens` table is in its own schema, accessible only by the broker service role. Not the publisher role, not the debate agent role.

**ADR impact**: New ADR-013 (token storage security).

---

## TC4 (Technical C4): Audit trail has no truncation protection

**Problem**: Chain-store hashing is marked "optional" when it should be mandatory. No external immutable sink. Admin could truncate.

**Resolution**:
1. **Mandatory chain hashing**: Every audit record includes `prev_hash` (SHA-256 of previous record). This is not optional.
2. **Tamper detection on read**: Any read of the audit trail verifies the hash chain from the most recent record back N records (configurable, default 100). Break = alert.
3. **External sink**: Daily export of audit records to S3 with versioning enabled (versioned S3 = immutable without deleting the entire bucket). This is the external tamper evidence.
4. **No DELETE grant**: The audit role has INSERT + SELECT only. No UPDATE, no DELETE, no TRUNCATE.

**ADR impact**: New ADR-014 (immutable audit trail).

---

## HIGH findings — disposition

| ID | Finding | Resolution |
|---|---|---|
| PH1 | EM/commodity liquidity in turbulent | Add liquidity check to cost model; widen spread + impact for low-ADV ETFs; block rotation into illiquid sleeves when regime = turbulent |
| PH2 | No trust-building path weeks 1–4 | Paper trading default + progressive onboarding: week 1 paper, week 2 small allocation, week 3 full. Debate agent guides. |
| PH3 | No AI track record visibility | Add "regime call history" screen showing every regime transition + outcome. Shipped in Phase 4. |
| PH4 | Stock-bond correlation mitigation | Add explicit "bonds-as-hedge failure" signal: if 21d rolling SPY/TLT correlation > +0.3, force cautious regime. New ensemble hard-override. |
| PH5 | Zero pricing model | Propose: $29/mo Growth, $19/mo Balanced, $9/mo Conservative. Flat rate preserves publisher exemption (no AUM %). |
| PH6 | Three portfolios too narrow | Add 2 more: "Aggressive Growth" (18% vol target), "Income" (6% vol, dividend-heavy). Total 5. **User approved.** |
| TH1 | Regime hysteresis deadlock | Add max-hysteresis counter: if ensemble has been in the hysteresis band for > 5 days, force the transition. |
| TH2 | Perplexity two-hop citations | Grounding contract verifies Midas signal/backtest IDs. News citations are marked "external, unverified" in the UI. |
| TH3 | FRED HY OAS 1-day lag | Use IBKR real-time HY ETF spread (HYG-IEF) as intraday proxy; FRED for daily confirmation. Dual-source. |
| TH4 | EODHD delisted-tickers unverified | **BLOCKER for Phase 1**: verify EODHD endpoint exists with a test query. If not, source from Polygon or SEC EDGAR. |
| TH5 | Prompt injection via news | Sanitize all Perplexity responses before storing in pgvector. Debate agent tools return structured data, not raw text. |
| TH6 | Redis cache underspecified | Write-through from DataFlow on ingestion, TTL = market-close for EOD, 60s for screen-active. Stampede: probabilistic early expiry. Redis-down: fall through to Postgres. |
| TH7 | Strategy underperformance churn | See PC2 resolution: transparent "strategy health" dashboard. |
| TH8 | IBKR CP API instability | Add IBKR API version pinning, integration test suite against sandbox, alerting on breaking changes. |
