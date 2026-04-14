# 14 — IBKR Integration

Interactive Brokers is the only supported broker in v1. This chapter explains why, what the integration does, and how to set it up.

## Why IBKR only?

### 1. Best execution for ETFs
IBKR's smart order routing and tight spreads give the best fills for the liquid US ETFs Midas uses. Average spread on SPY is 0.01% at IBKR vs 0.05%+ at retail brokers like Schwab or Fidelity.

### 2. Lowest commissions
IBKR Pro tiered: $0.0035/share, minimum $0.35 per order, maximum 1% of trade value. For a typical $100k portfolio weekly rebalance, this is $2-$5 total. Retail brokers charge more.

### 3. Client Portal Web API
IBKR has a clean, documented API for third-party integrations. OAuth 2.0. Order preview. Order submission. Position sync. Not every retail broker has this.

### 4. International and margin support
Even though Midas v1 is US-only and long-only, IBKR's infrastructure lets us extend to international markets (Phase 2) and margin (Phase 3) without switching brokers.

### 5. Regulatory alignment
IBKR is an SEC-registered broker-dealer. Trades flow through regulated venues. Tax documents come from IBKR, not Midas.

## What we CAN'T use (and why)

- **Robinhood**: no official OAuth API for third parties
- **Schwab**: API is for institutional/RIA use, complex approval
- **Fidelity**: same as Schwab
- **E*Trade**: API was deprecated
- **Webull/SoFi**: no third-party API

If you don't have an IBKR account and can't open one (e.g., you're outside the supported regions), Midas won't work for you in v1. Future phases may add Tiger Brokers (for Asia) or Alpaca (for developer-focused US users).

## Opening an IBKR account

If you don't have one:

1. Go to https://www.interactivebrokers.com
2. Click "Open Account"
3. Select "Individual" or "Joint" (not "Cash" — need margin-eligible for ETF rebalancing)
4. Complete the application (takes 30-60 minutes, similar to any brokerage)
5. Fund the account ($0 minimum, but $25k+ recommended for Midas)
6. Account approval: 1-5 business days

## Linking IBKR to Midas

### Option A: OAuth (production, not available yet)

When IBKR approves Midas's OAuth production application (in progress — see journal entry 0004-GAP-ibkr-oauth-production-approval):

1. In Midas, go to Settings → Broker Connection
2. Click "Link Account"
3. You're redirected to IBKR's authorization page
4. Log into IBKR
5. Review scopes: read_positions, preview_order, place_order
6. Authorize
7. Redirected back to Midas with a secure auth code
8. Midas exchanges the code for access + refresh tokens
9. Tokens encrypted (AES-256-GCM) and stored
10. Done. Midas can now fetch positions and submit orders.

### Option B: Client Portal Gateway (beta workaround)

Until OAuth production is approved, beta users run IBKR's Client Portal Gateway locally:

1. Download CP Gateway from IBKR's website
2. Run the gateway on your machine (port 5000 by default)
3. In your browser, go to `https://localhost:5000` and log into IBKR
4. Keep the gateway running
5. In Midas, go to Settings → Broker Connection
6. Click "Use Local Gateway"
7. Midas connects to `https://localhost:5000` instead of IBKR's cloud
8. Same interface for trading, but the gateway must be running

This is a workaround for beta. Not production-ready — you'd need to run the gateway 24/7 for signals to auto-execute.

## Token security

Once OAuth is complete, tokens are stored with these protections:

### Encryption at rest
- Access token: encrypted with AES-256-GCM using `IBKR_TOKEN_ENCRYPTION_KEY` (32-byte hex in `.env`)
- Refresh token: same encryption
- Stored in `tokens.user_tokens` table, column type `BYTEA` (not TEXT — prevents accidental logging)

### Key management
- Encryption key is in `.env`, never in database
- If the `.env` key is lost, all tokens are unrecoverable (users must re-link)
- Key rotation: create new key, re-encrypt tokens, update `.env`

### Access control
- Only the `midas_broker` Postgres role can read `tokens.user_tokens`
- Publisher role (`midas_publisher`) has zero grants on the `tokens` schema
- Boot-time assertion verifies this on every API startup

### Refresh token rotation
- Every refresh invalidates the old refresh token
- Single-use refresh tokens prevent replay attacks

### Revocation
- When you unlink, tokens are deleted from the database
- Midas calls IBKR's revoke endpoint to invalidate server-side too
- Takes effect immediately

## Scope minimization

Midas requests ONLY:
- `read_positions`: see what ETFs/cash you have
- `preview_order`: calculate order impact without submitting
- `place_order`: submit orders

Midas explicitly does NOT request:
- Withdrawal permission
- Funding permission
- Account settings changes
- Statement / tax document access
- Options / margin / crypto permissions

The scopes are hardcoded in `midas_broker/ibkr/oauth.py`. If an attacker gained access to Midas's codebase, they still couldn't increase the scopes without IBKR re-approving.

## Position sync

When you open the Midas app, it fetches your current IBKR positions:

```python
positions = await ibkr.get_positions(account_id)
# Returns: ticker, quantity, market_value, avg_cost, unrealized_pnl
```

These positions are displayed in the client-side order preview (see next section). They are NEVER sent to the Midas server — the impersonal publisher constraint.

Cache: positions are cached in browser localStorage for 60 seconds. After that, a new fetch happens.

## Order preview (client-side)

When a signal publishes and you open the approval card:

1. Client fetches your IBKR positions (`read_positions`)
2. Client computes the delta: target allocation − current positions
3. Client calls IBKR's `preview_order` for each trade
4. Preview returns: estimated commission, impact, post-trade buying power
5. UI displays the full rebalance card

This computation happens **in the browser / mobile app**, not the Midas server. The server only knows the impersonal target allocation; it never sees your current positions or balance.

This is the PC3 resolution and the legal tell that Midas operates as a publisher, not an advisor.

## Order submission

When you tap "Approve All":

1. Biometric prompt (Face ID / Touch ID / WebAuthn)
2. On confirm, each trade is sent to IBKR one-by-one
3. Order type: market order (ETFs are liquid enough that limit orders just add complexity)
4. Time in force: DAY (cancel at end of day if unfilled)
5. IBKR returns an order ID
6. Midas polls IBKR every 2 seconds for fill status
7. On fill, audit trail entry written
8. On timeout (60 seconds max poll), partial state recorded

If any order fails (insufficient funds, IBKR halts the stock, etc.):
- Midas stops submitting further orders
- User is alerted with the specific error
- Completed trades stay; failed trades aren't retried automatically

## Paper trading

IBKR offers a "paper trading" account linked to every real account:
- Same login
- Same API
- Same interface
- Simulated money
- Simulated fills

For Midas, paper trading just means connecting to the paper account URL instead of the live URL. Everything else is identical.

Default for new Midas users: paper trading for 2 weeks, then prompt to flip to real.

## Rate limits

IBKR doesn't publicly document rate limits but they exist. Midas implements:
- Max 3 position fetches per 10 seconds per user
- Max 10 order submissions per minute per user
- Exponential backoff on 429 responses
- Session keepalive via `/tickle` endpoint

If you hit a rate limit, the UI shows "Too many requests, retrying in 5s".

## Session management

IBKR sessions expire after ~6 hours of inactivity. Midas handles this:
- On 401 response, Midas tries to refresh the token (if < 5 minutes to expiry)
- If refresh fails, user is prompted to re-login to IBKR
- Session state is NOT stored in Midas — always queried live

## International ETFs

IBKR supports LSE (London) and other international ETFs. Midas v1 uses only US-listed ETFs. If you have UK/EU/Asian holdings in your IBKR account, Midas won't rebalance them — it'll show a warning and require you to handle them manually.

Phase 2 may add international ETF sleeves.

## Market hours

- Signals generate Sunday 7 PM ET (markets closed)
- Approvals can happen anytime
- Execution requires market hours (9:30 AM - 4:00 PM ET, Monday-Friday, excluding holidays)
- If you approve at 2 AM Monday, orders are queued and submitted at 9:30 AM

During market hours: orders execute immediately. Ofter hours: queued.

## Holiday calendar

NYSE holidays (no trading):
- New Year's Day
- MLK Day (3rd Monday of January)
- Presidents Day (3rd Monday of February)
- Good Friday (movable)
- Memorial Day (last Monday of May)
- Independence Day (July 4)
- Labor Day (1st Monday of September)
- Thanksgiving (4th Thursday of November)
- Christmas (December 25)

Midas's trading calendar matches NYSE. Signals don't generate on holidays.

## Tax reporting

Tax documents (1099-B, 1099-DIV, etc.) come from IBKR, not Midas. At year-end:
- IBKR generates tax forms based on actual executed trades
- You (or your CPA) use these for tax filing
- Midas's audit trail is a cross-reference for reconciliation, not a tax document

## Account holds

If IBKR puts a hold on your account (margin call, compliance review, etc.), Midas detects this on the next API call and:
- Pauses automatic execution
- Displays a warning on the dashboard
- Continues publishing signals (so you can see what the system recommends)
- Requires manual approval via IBKR web before trading resumes

## Multi-account support

v1 supports one IBKR account per Midas user. If you have multiple IBKR accounts (personal + trust + joint), you'd need multiple Midas accounts.

Phase 2 may add multi-account support.

## What happens if IBKR is down

- Position fetch fails: UI shows cached positions (60s cache) or "positions unavailable"
- Order submission fails: error displayed, user asked to retry
- Mid-trade failure: partial state recorded, user alerted

Midas doesn't try to route to a different broker. IBKR is the only broker. If it's down for an extended period (> 1 hour), the signal will still publish, but approvals may need to wait.

## Disconnecting and reconnecting

If you unlink IBKR, your Midas account continues to work but can't execute trades. Signals still publish. You can still approve — but the approval just records your intent without actually trading.

To re-link: Settings → Broker Connection → Link Account. Go through OAuth again. Your previous audit history is unaffected.

---

**Next**: [15 — Troubleshooting](15-troubleshooting.md)
