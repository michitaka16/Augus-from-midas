# Data Fabric — Midas Platform

Status: research draft, phase 01
Scope: storage, caching, sourcing, cost, quality for all market, fundamental, macro, and news data consumed by Midas
Note on figures: WebSearch was unavailable in this session. Pricing, rate limits, and plan tiers below reflect the agent's best knowledge as of early 2026 and are marked `[VERIFY]` where live confirmation is needed before the /todos gate. Architecture recommendations do not depend on exact numbers.

---

## 1. Data Sources Inventory

### 1.1 EODHD (primary)

EODHD (eodhd.com, formerly eodhistoricaldata.com) is the commercial aggregator the user already subscribes to. It is the cheapest production-grade source covering global equities, ETFs, funds, bonds, FX, crypto, and commodities in a single API surface.

**Coverage relevant to Midas sleeves:**

- **End-of-day OHLCV** — 70+ global exchanges, going back to 1990s for US listings, shallower for emerging markets. Dividend- and split-adjusted close available as separate field.
- **Fundamentals** — income statement, balance sheet, cash flow, ratios. Quarterly + annual, point-in-time indexed by report date (not just fiscal period) on higher tiers. Critical for survivorship-free backtests.
- **Splits & dividends** — full corporate action history per ticker. Needed to reconstruct total return series.
- **Intraday** — 1-minute and 5-minute bars, typically 120 days rolling history, some symbols longer. Not a full tick archive.
- **Options chains** — US equity options, strikes and greeks, delayed. Useful for vol-surface inputs to regime detection.
- **Bonds** — government yield curves (UST, Bund, JGB, Gilt), some corporate. Coverage thinner than equities.
- **ETF constituents & holdings** — periodic snapshots, ~monthly refresh. Needed for sleeve composition and look-through exposure.
- **Macro indicators** — some coverage via the "Economic Events" and "Macro Indicators" endpoints (CPI, PMI, GDP, rates). Thinner than FRED but in-band.
- **News** — a headline feed exists but is shallow and not a substitute for Perplexity.

**Rate limits and plans `[VERIFY]`:**

- All-in-One plan (~$100/mo): ~100k API calls/day, all endpoints incl. fundamentals, intraday, options.
- EOD-only plan (~$20/mo): EOD prices + splits/divs only, no fundamentals.
- Fundamentals plan (~$60/mo): EOD + fundamentals, no intraday.
- Institutional tiers above $300/mo unlock faster intraday, bulk downloads, commercial redistribution.

**Known gaps:**

- No real-time Level-1/2 quotes (delayed 15–20 min typical).
- Intraday history is rolling, not archival — cannot rebuild 2010 1-min bars.
- Bond coverage is narrow, especially corporate credit.
- No VIX term structure directly; VIX spot is on CBOE but VIX3M, VIX6M require supplemental feed.
- No credit spread series (HY OAS, IG OAS).

### 1.2 Yahoo Finance / yfinance (secondary, fallback)

- `yfinance` is a community-maintained Python wrapper scraping Yahoo's undocumented JSON endpoints. No official API, no SLA, no commercial license.
- **Strengths**: free, broad coverage, dividend-adjusted series, easy to reconcile against EODHD for data-quality checks.
- **Limitations**: silent schema changes, aggressive rate limiting (~2000 req/hr typical before soft-bans), occasional data gaps and bad ticks (especially on splits and late adjustments), legal gray area for commercial redistribution.
- **Role in Midas**: strictly a fallback/reconciliation source. Never the sole source for a production decision. Use as a cheap second opinion to flag EODHD anomalies and to fill short gaps while EODHD rate limit resets.

### 1.3 Perplexity API (news + research)

- **Models**: `sonar` (fast, grounded chat with web citations), `sonar-pro` (higher quality, more citations), `sonar-deep-research` (multi-step agentic research, minutes-long latency). `[VERIFY model names and tiers]`
- **Pricing `[VERIFY]`**: Sonar is billed per 1k input/output tokens plus a per-request search fee; rough envelope $1–$5 per 1M tokens for sonar, $5–$15 per 1M for sonar-pro, deep-research billed in "searches" at $5–$10 per deep call.
- **Freshness**: crawls public web near-realtime; citations include publication timestamps. Well suited for "what is the market talking about RIGHT NOW for ticker X" queries.
- **Citation quality**: citations are returned as structured links and we MUST persist them for audit — "why did Midas flag this as bearish news" is an auditable chain.
- **Rate limits**: low-hundreds req/min on standard plans. This is the binding constraint for news refresh at 1000-user scale.

### 1.4 Gaps and supplementary sources

- **Real-time quotes** — deferred. v1 is signal-only, user executes on IBKR's own terminal, so Midas does not need its own real-time feed. If live-trading v2 is funded, pull from IBKR market data subscription (packaged with the broker account).
- **VIX family (VIX, VIX3M, VIX6M, VVIX)** — CBOE publishes EOD free; intraday from EODHD index endpoint or FRED mirror. Sufficient for regime detection.
- **Credit spreads (HY OAS, IG OAS)** — FRED: `BAMLH0A0HYM2`, `BAMLC0A0CM`. Daily, free, reliable. Ingest via FRED API.
- **Yield curve** — FRED: full UST series (`DGS1MO` … `DGS30`). Free, daily.
- **Macro (CPI, unemployment, PMI)** — FRED primary; EODHD macro endpoint as secondary.
- **Sentiment** — derive from Perplexity news + optional FinBERT classifier on headlines. No dedicated paid sentiment feed in v1.

FRED becomes a third first-class source alongside EODHD and Perplexity. It is free, stable, and covers every macro series the regime detector needs.

---

## 2. Storage Architecture

### 2.1 Recommended stack (ONE pick)

**PostgreSQL 16 + TimescaleDB + pgvector, managed through Kailash DataFlow, with Redis hot cache and S3-compatible cold tier.**

One database engine. One framework. Everything else is a layer inside it.

Rationale:

1. **DataFlow is Postgres-native.** The Midas project is built on Kailash SDK — DataFlow gives us zero-config CRUD, pool management, migrations, and auto-generated nodes. Choosing a non-Postgres primary (ClickHouse, DuckDB) would force us off DataFlow for 80% of the platform.
2. **TimescaleDB gives us time-series superpowers inside Postgres.** Hypertables, continuous aggregates, compression (10–20x on OHLCV), and native time_bucket — at the price of one extension. We do not need the raw throughput of ClickHouse; we need correctness and joinability against fundamentals, users, portfolios, news. Keeping everything in one engine wins.
3. **pgvector handles news embeddings** for semantic retrieval ("find prior news similar to today's story on TSLA"). No separate vector DB.
4. **DuckDB is still useful — as a query engine, not a store.** For heavy backtests the analytics workers can materialize a Parquet extract from Postgres and query it with DuckDB in-process. Postgres remains the source of truth.

What we explicitly reject and why:

- **ClickHouse as primary**: faster for pure OLAP scans but a second operational surface, no DataFlow integration, and painful for the transactional parts of Midas (portfolios, orders, audit).
- **DuckDB as primary**: single-writer, file-based — not a multi-tenant database. Fine as an embedded analytics layer, wrong as the shared fabric.
- **MongoDB / document stores**: financial data is rigorously structured; schemaless storage loses type safety and makes point-in-time joins ugly.

### 2.2 Schema layout (logical)

All tables are multi-tenant via a `scope` column, not schema-per-user. Schema-per-user explodes to thousands of schemas and breaks shared caching (the whole point of the fabric is that `AAPL` EOD is pulled once for everyone).

- `instruments` — one row per tradable: ticker, exchange, asset_class, currency, first_trade_date, delisted_date, figi. **Global, no tenant.**
- `prices_eod` — Timescale hypertable partitioned on `(instrument_id, ts)`. Columns: open, high, low, close, adj_close, volume, source, ingested_at. **Global.** Compression after 90 days.
- `prices_intraday` — hypertable, 1-min bars, 180-day retention with automated drop_chunks policy; older bars archived to S3 Parquet. **Global.**
- `corporate_actions` — splits, dividends, symbol changes, delistings. Immutable append-only. **Global.** Drives survivorship-free backtests.
- `fundamentals_pit` — point-in-time fundamentals keyed on `(instrument_id, report_date, as_of_date)`. Two dates is the whole game: `report_date` = fiscal period end, `as_of_date` = when we learned it. Backtests query with `as_of_date <= bar_ts` to avoid lookahead bias. **Global.**
- `macro_series` — FRED-style `(series_id, ts, value, as_of_date)`. **Global.**
- `news_items` — headline, body, source, url, published_at, fetched_at, perplexity_query_id, citations JSONB, embedding VECTOR(1536). **Global.** pgvector HNSW index for semantic search.
- `news_ticker_link` — many-to-many `news_items ↔ instruments` with confidence score. **Global.**
- `users`, `portfolios`, `positions`, `orders`, `decisions`, `audit_log` — standard multi-tenant, `user_id` column, row-level security via Postgres RLS policies. **Per-tenant.**
- `dataset_versions` — every backtest run records the (min, max) `ingested_at` of each source it touched. Reproducibility gate.

### 2.3 Cache tiers

- **Hot — Redis** (or Postgres unlogged tables if we want to stay single-engine). TTL 60s for "latest bar" queries during active screens, TTL 5 min for rendered fundamental summary blocks, TTL 1 hour for news relevance rankings. Key namespace: `midas:hot:<kind>:<id>`.
- **Warm — Postgres/Timescale** — the authoritative store above. Queries hit this when hot misses.
- **Cold — S3 (or R2/MinIO)** — Parquet exports of prices_intraday chunks older than 180 days, full EODHD raw-response snapshots, compressed news bodies. Read-through from the analytics worker only; never on the user-facing path.

### 2.4 Multi-tenancy model

Single shared database with `user_id` columns on per-tenant tables and Postgres **row-level security** policies enforced at the role level. Market, fundamental, macro, and news data are global (no `user_id`) — this is the entire point of "common database for all users, never re-pull." Schema-per-user is rejected.

---

## 3. Cache Invalidation

A coherent invalidation story is more important than a fast cache. Wrong cached data costs the user money; a slow cache miss does not.

- **EOD bars**: once the official market close is confirmed for a given exchange-day AND the EODHD EOD endpoint returns that day's bar, the row is **immutable**. Never invalidated. Exception: late adjustment windows (EODHD sometimes restates a bar within 24h for splits or error corrections) — we schedule a re-fetch of `ts > today - 3 days` nightly and diff against stored values. Any diff triggers a `corporate_actions` or `adjustment` record and an audit event.
- **Intraday bars**: TTL tied to the last-known bar close of the exchange. For US 1-min bars during RTH, cache entry for the "latest bar" key is valid until the next minute boundary. Off-hours: no TTL — bars are frozen.
- **Fundamentals**: invalidated only when a new filing arrives (new `report_date` for that issuer). Polling cadence: daily for actively-held tickers, weekly for watchlist, monthly for universe.
- **News**: time-decay. Relevance score halves every 6 hours after `published_at`. Entries with relevance < 0.05 fall out of the hot cache but stay in the warm store for backtests and audit.
- **Perplexity queries**: cache the full query+response by `(query_hash, model, as_of_hour)`. Same user screen re-open within the hour returns cached. New hour → re-query. Material price move (|ret| > 2σ of trailing 20-day realized vol) → force re-query regardless.
- **Screen-active pull policy**: when a user opens a screen, Midas (a) serves from warm cache instantly, (b) fires an async refresh job. Per-user throttle: **max 1 refresh request per 10 seconds per symbol**, global throttle per user: **max 60 req/min** across all symbols. These protect EODHD quota under many concurrent users.

---

## 4. Backtest Data Requirements

The brief demands "comprehensive backtest across all market conditions, multiple sub-horizons." This is meaningless if the data has lookahead or survivorship bias. Requirements:

- **Point-in-time instrument universe.** Join trades against `instruments.first_trade_date` and `delisted_date` so the 2005 backtest universe includes tickers that died by 2015. EODHD provides a delisted-tickers endpoint — we ingest it into `instruments` with `delisted_date` populated.
- **Point-in-time fundamentals.** The `(report_date, as_of_date)` pair in `fundamentals_pit` is non-negotiable. A 2008 backtest filter on "P/E < 15" MUST use the P/E we could have computed on that date, not the restated P/E published in 2010.
- **Dividend-adjusted close.** Store raw close AND adjusted close separately. Total return series is `adj_close`; tax/commission models hit raw close. Never conflate.
- **Split adjustment.** Apply from `corporate_actions` table, not from pre-adjusted feeds, so we can reconstruct either view.
- **Coverage target — 2000-01-01 to present.**
  - US equities and major ETFs: EODHD direct.
  - ETFs that didn't exist pre-2005 (most sector ETFs): use the tracked index as a proxy, flagged as `proxy=true` so backtest results from the proxy window are tagged.
  - Bonds: TLT/IEF/SHY etc. cover post-2002; for earlier, use FRED constant-maturity yields and synthesize total return.
  - Commodities: GLD from 2004; pre-2004 use LBMA gold fix from FRED. Oil: USO from 2006; pre-2006 use WTI spot from FRED with a roll-cost adjustment.
  - Emerging markets: EEM from 2003.
- **Holiday calendar** from `pandas_market_calendars` or EODHD exchange hours endpoint. Gap-fill policy: never forward-fill across a holiday; mark as NaN and exclude from returns.

---

## 5. Data Quality and Fallback

- **Primary/secondary reconciliation.** Nightly batch: pull the last 5 trading days of EOD from Yahoo for the active universe, compare close values. Divergence > 50 bps on the same ticker-day triggers a quality alert and a row in `data_quality_events`. Threshold is tuned per-asset (tighter for majors, looser for micro-caps).
- **Gap detection.** For each instrument on each trading day from the exchange calendar, assert a row exists in `prices_eod`. Missing rows re-fetched first from EODHD, then Yahoo. After both fail, gap is logged and the instrument is excluded from that day's backtest slice.
- **Bad tick filtering.** Reject bars where `high < low`, `close > high`, `close < low`, or `|ret| > 50%` without a corresponding corporate action. Rejected ticks go to `quarantine_bars` for manual review, not silently dropped.
- **Audit trail.** Every backtest run persists (a) code git SHA, (b) min/max `ingested_at` for each source touched, (c) dataset_version id, (d) random seeds. Rerunning the same (SHA, dataset_version, seed) MUST yield bit-identical results. This is how we answer "why does this backtest result exist."

---

## 6. Cost Estimates `[VERIFY all figures]`

Assumptions: universe of ~3000 global instruments tracked in EOD, ~500 actively traded, ~200 with frequent fundamentals refresh.

**Fixed platform cost (independent of user count, because data is shared):**

| Line                             | Monthly |
| -------------------------------- | ------- |
| EODHD All-in-One                 | ~$100   |
| FRED                             | $0      |
| Yahoo fallback                   | $0      |
| Postgres+Timescale (managed, small) | ~$100   |
| Redis (managed, small)           | ~$25    |
| S3 cold tier                     | ~$10    |
| **Fixed subtotal**               | **~$235** |

**Variable — Perplexity** (only variable line that scales with users, because market data is shared):

- Assumed per-user news query budget: ~50 sonar calls/day average, ~1 sonar-pro call/day, ~0.1 deep-research call/day. Screen-open driven, heavily cached, throttled.
- Per-user Perplexity cost estimate: ~$3–$6/month at 100 users, dropping toward ~$2–$4/user/month at 1000 users because cache-hit rate rises with concurrency (more users → more shared queries already in warm cache).

**At 100 users:** 235 + (100 × ~$5) ≈ **$735/month**, dominated by Perplexity.
**At 1000 users:** 235 + (1000 × ~$3) ≈ **$3,235/month**, still dominated by Perplexity. EODHD does NOT scale with users because the fabric is shared — this is the whole architectural bet paying off.

Institutional Perplexity or a self-hosted news pipeline (RSS + FinBERT) would compress the 1000-user line significantly if per-user Perplexity exceeds $3.

---

## 7. Open Questions for the Gate

1. Commercial redistribution: EODHD All-in-One covers "internal use." If Midas ships as a commercial SaaS, we need the commercial tier — `[VERIFY]` the delta.
2. Perplexity throughput: are the default rate limits sufficient for 1000 concurrent screen opens, or do we need an enterprise agreement?
3. IBKR market data: deferred to v2, but decide now whether v1 signal-only mode displays 15-min delayed quotes (EODHD) or live quotes (IBKR subscription, ~$10/user/month added).
4. Do we want a real sentiment feed (RavenPack, Bloomberg) in v2, or is Perplexity + FinBERT adequate?
