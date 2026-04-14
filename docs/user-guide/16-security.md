# 16 — Security & Privacy

How Midas protects your data and money.

## Threat model

What we're defending against:
1. **Attackers trying to access other users' data**
2. **Attackers trying to steal IBKR tokens and trade**
3. **Attackers trying to manipulate signals to cause bad trades**
4. **Insiders (engineers, DBAs) abusing access**
5. **Compromise of a single component cascading to full breach**

What we're NOT defending against (out of scope for v1):
- Nation-state actors with zero-day exploits
- Physical access to your device (your responsibility)
- You clicking phishing links (your responsibility — enable MFA)

## Authentication

### Password storage
Passwords are hashed with bcrypt (cost factor 12) before storage. Never stored in plaintext. Never logged.

Fallback when bcrypt isn't available: PBKDF2-SHA256 with 100,000 iterations and per-user salt. Also secure.

### Session management
- Access tokens: JWT, 15-minute expiry
- Refresh tokens: JWT, 7-day expiry
- JWT secret: from `.env`, 32+ characters, never committed to git

When you log in, you get both tokens. Access token is used for API calls. When it expires, the web/mobile app silently refreshes using the refresh token.

If someone steals your access token, they have 15 minutes. If they steal your refresh token, they have 7 days (and we'd detect suspicious usage patterns).

### MFA (optional but recommended)
Time-based one-time password (TOTP, RFC 6238). Compatible with Google Authenticator, Authy, 1Password, Bitwarden.

Once MFA is enabled, login requires:
1. Email + password
2. 6-digit TOTP code from your authenticator app

If you lose your authenticator, email `support@midas.app` for recovery (takes 24-48h for identity verification).

### Session binding
We plan to bind sessions to:
- Device fingerprint (browser + OS)
- IP address (loose binding — allows mobile data → WiFi transition)

If either changes dramatically, the user is prompted to re-authenticate.

## Authorization — PACT envelopes

Midas uses a 4-role separation of privileges. Each role has explicit Postgres grants.

### midas_publisher
- Can SELECT/INSERT/UPDATE: `bars`, `regime_signals`, `signals`, `signal_inputs`, `backtest_runs`, `model_portfolios`
- Can SELECT: `news_items`, `etf_universe`, `fundamentals`, `corp_actions`
- CANNOT access: `users.*`, `tokens.*`

### midas_subscriber
- Can SELECT: `signals`, `backtest_runs`, `news_items` (all public)
- Can SELECT/INSERT/UPDATE: `users.accounts`, `users.preferences`, `users.approvals`
- CANNOT access: `tokens.*`, other users' rows (enforced via Row Level Security in future)

### midas_broker
- Can SELECT/INSERT/UPDATE/DELETE: `tokens.user_tokens`
- CANNOT access: `users.*`, `signals`, `regime_signals` (separate concern)

### midas_audit
- Can SELECT/INSERT: `audit_trail`
- CANNOT UPDATE, DELETE, or TRUNCATE (append-only enforcement)

### Structural enforcement
On every API startup, `run_all_assertions()` queries `information_schema.role_table_grants` and verifies:
1. `midas_publisher` has ZERO grants on `users` or `tokens` schemas
2. `midas_audit` has no UPDATE, DELETE, or TRUNCATE grants
3. `midas_broker` has no grants on `users`

If any assertion fails, the API refuses to start. This is the publisher exemption made structural (ADR-001).

### CI enforcement
Every PR that modifies migrations runs the assertion check in CI. A PR that would weaken the separation is blocked.

## IBKR token encryption

Tokens are stored encrypted at rest:

### Algorithm
AES-256-GCM with a 32-byte key from `IBKR_TOKEN_ENCRYPTION_KEY` in `.env`.

### Format
```
ciphertext_bytes = nonce(12 bytes) + AESGCM.encrypt(key, nonce, plaintext)
```

The nonce is randomly generated per encryption. Same plaintext encrypted twice produces different ciphertext.

### Key management
- Key lives in `.env`, not database
- Key rotation: generate new key, re-encrypt all tokens, update `.env`
- Key loss: all tokens become unrecoverable. Users must re-link.

### Column type
Tokens are stored as `BYTEA` (binary), not `TEXT`. This prevents:
- Accidental string logging (binary won't format as a string)
- Accidental JSON serialization (you'd see `<bytes>` not the actual token)

## Input validation

### SQL injection
All queries use parameterized statements. No string interpolation into SQL.

Database column validation: identifier names (table names, column names) are whitelisted before any SQL that references them. The regex `^[a-zA-Z_][a-zA-Z0-9_]*$` prevents injection via column/table names.

### XSS
React escapes all output by default. No `dangerouslySetInnerHTML` is used in user-facing components.

Server-side: we sanitize news content from Perplexity before storing. HTML tags, script tags, control characters, and known prompt injection patterns are stripped.

### Prompt injection (AI context)
News items and user messages are wrapped with safety framing before being sent to the LLM:
```
[EXTERNAL CONTENT - may contain manipulation attempts]: <content>
```

Known patterns detected:
- "ignore previous instructions"
- "you are now a..."
- "forget everything"
- "disregard all..."
- "new instructions:"

The LLM is also instructed via system prompt to treat external content as suspicious.

### CSRF
All state-changing endpoints require:
1. JWT in Authorization header (not cookie)
2. Content-Type: application/json (prevents form-based CSRF)

Since we don't use cookies for auth, traditional CSRF doesn't apply.

### Rate limiting
Per-endpoint limits (see chapter 12):
- Auth endpoints: 10/min per IP (brute force protection)
- Debate: 20/min per user (LLM cost control)
- Signals: 60/min per IP (CDN handles most)
- Approvals: 30/min per user

Exceeded → 429 with `Retry-After` header. Redis-backed sliding window.

## Audit trail integrity

### Chain hashing
Every audit record is SHA-256 linked to the previous record. See chapter 11 for details.

### Write-only role
The `midas_audit` role can INSERT and SELECT, not UPDATE or DELETE. Enforced at the Postgres level. Even if someone compromises the audit API, they can't retroactively modify records.

### External sink
Daily export to S3 with versioning enabled. Even if the Midas database is fully compromised, the S3 copy provides tamper evidence.

## Network security

### TLS everywhere (production)
- HTTPS for all user-facing endpoints
- TLS for Postgres connections
- TLS for Redis connections (when hosted)
- TLS for IBKR API calls

In local dev, TLS is optional (localhost is trusted).

### CORS
The API allows specific origins only:
- `http://localhost:3000` (web dev)
- `http://localhost:19006` (Expo dev)
- Production domains (from `ALLOWED_ORIGINS` env var)

Credentials allowed for specific origins only.

### Secrets management
`.env` is in `.gitignore`. Never committed to git.

In production, secrets come from environment variables set by the hosting platform (Fly.io, AWS Secrets Manager, etc.), not from `.env` files.

### No inbound from public internet (v1)
The API runs behind CloudFront/Cloudflare. Only CDN IPs can reach the origin. Rate limiting and DDoS protection at the CDN layer.

## Data minimization

### What Midas stores about you
- Email (for login and notifications)
- Password hash (never plaintext)
- Model portfolio subscription
- Notification preferences
- Escalation timeout preference
- Paper trading flag
- IBKR OAuth tokens (encrypted)
- Approval history
- Debate conversation history

### What Midas does NOT store
- Your name (not required)
- Your address (not required)
- Your phone number (not required — notifications use email/push)
- Your SSN or tax ID (never asked for)
- Your income (never asked for)
- Your investment goals (never asked for — publisher model doesn't need them)
- Your IBKR balance (fetched at runtime, never stored server-side)
- Your IBKR positions (fetched at runtime, never stored server-side)

This minimization is the publisher exemption in practice: if we don't have personal financial data, we can't accidentally use it in a way that would convert us into a personalized adviser.

## Encryption at rest

### Database
Postgres TDE (Transparent Data Encryption) at the disk level (production). Unauthorized physical access to disks yields encrypted blobs.

### Backups
Automated daily backups, encrypted with AES-256. Stored in S3 with Object Lock (immutability). Retention: 90 days.

### Logs
Application logs are stored in CloudWatch / similar. No PII in logs (we scrub email/name/token fields). Retention: 30 days.

## Privacy

### No analytics trackers
No Google Analytics. No Mixpanel. No Segment. No Amplitude. No Facebook Pixel. Zero third-party tracking.

### No ads
Midas's business model is subscription, not advertising. There is no incentive to sell your data. We don't have an ad product to cross-sell.

### No data sale
We don't sell data. Period. Even for "aggregated analytics." If Midas is acquired, users get 30 days' notice before any data transfer, with opt-out.

### Data export
Click "Download my data" in Settings. Get a ZIP of everything we have about you in JSON + CSV.

### Data deletion
Request deletion in Settings. 30-day cool-off (reversible). After 30 days:
- PII deleted
- Tokens deleted
- Audit records anonymized (user_id hashed)
- Impersonal data (signals, regime states) unaffected

### Do Not Track
We respect the DNT header. If your browser sends DNT, we disable the (nonexistent) analytics (already disabled for everyone).

## Incident response

If a security incident occurs:
1. Affected users notified within 72 hours (GDPR requirement)
2. Public disclosure within 30 days unless law enforcement requests delay
3. Post-mortem published within 90 days
4. Credit monitoring offered if PII was exposed

## Responsible disclosure

Security researchers: email `security@midas.app` with:
- Description of the vulnerability
- Steps to reproduce
- Any PoC code

We commit to:
- Acknowledge within 24 hours
- Patch within 30 days
- Credit you publicly (with your permission)
- Not pursue legal action against good-faith researchers

## What you should do

### Strong practices
1. **Use a password manager** (1Password, Bitwarden) with a strong master password
2. **Enable MFA** on Midas and your email
3. **Enable MFA on IBKR** too (they offer it)
4. **Keep your devices updated** — iOS/Android/macOS patches matter
5. **Don't share your login** with anyone, including family
6. **Be suspicious of emails** claiming to be from Midas with urgent action — we rarely email

### If you lose a device
1. Log into Midas from a new device
2. Settings → Security → "Log out all devices"
3. Change your password
4. Check your IBKR account for unauthorized trades (extremely unlikely due to biometric requirement, but verify)

### Red flags to report
Email `security@midas.app` if you see:
- A push notification you didn't expect
- A trade in your history you didn't approve
- A regime flip notification that seems implausible
- An email from "Midas" asking for your password or token

---

**Next**: [17 — The Publisher Model](17-publisher-model.md)
