# M05 — IBKR Integration

Dependency: M00 (schema for user_tokens)
Deliverable: D5
Package: `packages/midas-broker`

## Todos

### M05-01: Build IBKR Client Portal API client
`packages/midas-broker/src/midas_broker/ibkr/client.py`
- HTTP client for IBKR Client Portal Web API
- Endpoints: accounts, positions, orders (preview + place + status), market data
- Rate limit handling (IBKR's undocumented limits — exponential backoff)
- Error handling: session timeout, re-authentication, gateway errors
- API version pinning (per TH8 — pin to known working version)

### M05-02: Build IBKR OAuth flow
`packages/midas-broker/src/midas_broker/ibkr/oauth.py`
- OAuth 2.0 authorization code flow per IBKR spec
- Scope minimization: `read positions` + `preview order` + `place order` only. NO withdrawal/ACH/funding.
- Token storage: AES-256-GCM encrypted in `user_tokens` table (key from .env IBKR_TOKEN_ENCRYPTION_KEY)
- Token column is BYTEA, not TEXT (prevents accidental logging)
- Refresh token rotation: single-use refresh tokens, old token invalidated on refresh
- Token expiry handling: auto-refresh before expiry, graceful degradation on failure

### M05-03: Build local CP Gateway fallback
`packages/midas-broker/src/midas_broker/ibkr/gateway.py`
- For private beta: user runs IBKR Client Portal Gateway locally
- Same client interface as OAuth path (adapter pattern)
- Instructions for user to download + configure Gateway
- Auto-detect: if OAuth token available, use OAuth; otherwise fall back to Gateway

### M05-04: Build position sync
`packages/midas-broker/src/midas_broker/orders/positions.py`
- Read-only: fetch current positions from IBKR
- Returns: ticker, quantity, market_value, avg_cost, unrealized_pnl
- Cache positions in Redis (TTL: 60s when screen active)
- This data NEVER leaves the client in v1 (publisher exemption — server never sees user positions)

### M05-05: Build order preview
`packages/midas-broker/src/midas_broker/orders/preview.py`
- Given a signal's target allocations and current positions (from M05-04):
  - Compute the delta (what to buy/sell to reach target)
  - Call IBKR order preview endpoint for each trade
  - Return: per-trade (ticker, direction, shares, estimated_commission, estimated_impact)
- This computation happens CLIENT-SIDE (web/mobile) — server provides the signal, client fetches positions and computes delta
- Feature-flagged pending legal opinion (per PC3 resolution)

### M05-06: Build order submission
`packages/midas-broker/src/midas_broker/orders/submit.py`
- User-initiated: takes a list of previewed orders, submits to IBKR
- Biometric confirmation required before submission (handled by frontend)
- Order type: market order (ETFs, liquid — limit orders add complexity without benefit for ETF rebalancing)
- Confirm fill: poll order status until filled/cancelled
- Write execution result to audit trail

### M05-07: Build paper trading adapter
`packages/midas-broker/src/midas_broker/paper/`
- Adapter that talks to IBKR paper trading account
- Same interface as real account
- Default for first 2 weeks of onboarding (trust-building, per PH2)
- Paper account auto-provisioned on IBKR link (if paper account exists)

### M05-08: Test — IBKR integration Tier 1 (unit)
- OAuth token encryption/decryption round-trip
- Refresh token rotation logic
- Position sync caching
- Order preview delta computation against known portfolio

### M05-09: Test — IBKR integration Tier 2 (integration, IBKR sandbox)
- OAuth flow against IBKR sandbox
- Position read from paper account
- Order preview + submit on paper account
- Fill confirmation
- Token refresh cycle
