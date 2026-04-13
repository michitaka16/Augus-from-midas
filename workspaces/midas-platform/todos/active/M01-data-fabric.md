# M01 — Data Fabric

Dependency: M00 (monorepo + schema)
Deliverable: D1
Package: `packages/midas-data`

## Todos

### M01-01: Build EODHD source adapter
`packages/midas-data/src/midas_data/sources/eodhd.py`
- EOD bars (all 8 sleeves: equity sector ETFs, precious metals, govt bonds all durations, IG corp, REITs, commodities, dividend ETFs, EM equity)
- Fundamentals (P/E, yield, AUM for ETFs)
- Corporate actions (splits, dividends, mergers)
- Delisted tickers (survivorship-free backtests) — **BLOCKER**: verify this endpoint actually exists via test query. If not, document gap and source from Polygon or SEC EDGAR.
- Rate limit handling per EODHD plan
- API key from `.env` (EODHD_API_KEY)

### M01-02: Wire EODHD adapter to DataFlow
- Bulk write ingested data to `bars`, `fundamentals`, `corp_actions`, `etf_universe` tables via DataFlow
- Deduplication: skip bars already present for (ticker, date, source)
- Write-through to Redis hot cache on ingestion

### M01-03: Build FRED source adapter
`packages/midas-data/src/midas_data/sources/fred.py`
- VIX (VIXCLS), VIX3M, VVIX
- HY OAS (BAMLH0A0HYM2), IG OAS (BAMLC0A4CBBB)
- Yield curve: 3-month (DGS3MO), 2-year (DGS2), 10-year (DGS10), 30-year (DGS30)
- Federal funds rate (FEDFUNDS)
- API via FRED's public JSON endpoint (no key required for limited use; key from `.env` if rate-limited)

### M01-04: Wire FRED adapter to DataFlow
- Write to `regime_signals` raw table (date, signal_name, value)
- Note FRED's 1-day publication lag on HY OAS — document for regime detector

### M01-05: Build Yahoo Finance reconciliation adapter
`packages/midas-data/src/midas_data/sources/yahoo.py`
- yfinance wrapper for EOD bars only
- Used ONLY for cross-check against EODHD, never as primary
- Reconciliation logic: flag any bar where |eodhd_close - yahoo_close| / eodhd_close > 0.5%
- Legal caveat comment: yfinance has no SLA; consider Polygon/Tiingo before commercial launch

### M01-06: Build Perplexity news adapter
`packages/midas-data/src/midas_data/sources/perplexity.py`
- Perplexity Sonar API for market news queries
- Structured response parsing: extract title, content, citations (two-hop — mark as "external, unverified")
- Embedding generation (OpenAI text-embedding-3-small or equivalent from `.env`)
- Store in `news_items` table with pgvector embedding
- Rate limit handling + aggressive dedup caching
- **Sanitize all responses** before storing (strip potential prompt injection payloads)
- Time-decay TTL: news older than 72h not re-fetched

### M01-07: Wire Perplexity adapter to DataFlow + pgvector
- Bulk write to `news_items` via DataFlow
- pgvector index for semantic search
- Write-through to Redis with time-decay TTL

### M01-08: Build IBKR real-time HY ETF spread proxy
`packages/midas-data/src/midas_data/sources/ibkr_spread.py`
- Compute HYG-IEF spread as intraday proxy for HY OAS (per TH3 resolution)
- Used when FRED's 1-day lag matters (crisis onset)
- Requires IBKR market data subscription
- Fallback: use FRED daily when IBKR data unavailable

### M01-09: Build data fabric cache layer
`packages/midas-data/src/midas_data/fabric/`
- Redis hot cache: write-through on ingestion
- TTL contract: EOD bars = never invalidate after market close confirmed; screen-active intraday = 60s; news = time-decay
- Stampede protection: probabilistic early expiry (jitter on TTL)
- Redis-down fallback: fall through to Postgres (logged, alerted)
- `get_bars(ticker, start, end)`, `get_regime_signals(date)`, `get_news(query, k=5)` — unified API

### M01-10: Build data quality layer
`packages/midas-data/src/midas_data/quality/`
- Gap detection: identify missing trading days per ticker
- Holiday calendar (NYSE, LSE for international ETFs)
- Bad-tick filter: flag bars with |return| > 20% for manual review
- EODHD/Yahoo reconciliation runner
- Corporate action adjustment verification

### M01-11: Build point-in-time ETF universe manager
`packages/midas-data/src/midas_data/fabric/pit_universe.py`
- For any date, return the set of ETFs that existed and were tradeable
- Uses `etf_universe` table (inception_date, delist_date)
- Critical for survivorship-free backtests
- Nightly audit: verify every backtest uses PIT universe, not current universe

### M01-12: Historical data load (2000-present)
- Script to backfill all 8 sleeves from 2000-01-01
- EODHD historical endpoint for bars
- FRED historical for all macro signals
- `corp_actions` backfill
- `etf_universe` backfill (including delisted)
- Validation: count bars per ticker, flag gaps
- **Gate**: Data for all 8 sleeves loads clean with < 0.1% gap rate

### M01-13: Test — data fabric Tier 1 (unit)
- Source adapter mocks (EODHD, FRED, Yahoo, Perplexity response parsing)
- Cache layer logic (TTL, stampede, fallback)
- Data quality filters
- PIT universe lookups

### M01-15: Verify EODHD delisted-tickers endpoint (BLOCKER)
- Make a test API call to EODHD's delisted/expired tickers endpoint
- Confirm it returns historical tickers with inception and delist dates
- If endpoint does NOT exist: immediately source from Polygon.io or SEC EDGAR XBRL
- **GATE**: This must pass before any backtest is considered valid (survivorship bias)
- Document the source chosen and its coverage

### M01-14: Test — data fabric Tier 2 (integration, real Postgres)
- Full ingestion pipeline: EODHD → DataFlow → Postgres → Redis
- Reconciliation runner against real Yahoo data
- pgvector semantic search on real news embeddings
- Deduplication correctness
