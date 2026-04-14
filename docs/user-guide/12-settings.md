# 12 — Settings & Preferences

Settings is where you configure how Midas behaves for you. It's split into 4 sections.

## Model Portfolio

Click on a portfolio card to subscribe to it. The active portfolio is highlighted with an "Active" tag.

Five portfolios available (see chapter 5 for details):
- Aggressive Growth (18% vol) — $29/mo
- Growth (14%) — $29/mo
- Balanced (10%) — $19/mo
- Conservative (6%) — $9/mo
- Income (6%, dividend-biased) — $19/mo

Switching takes effect on the next signal (Sunday). Your current week's signal is already published and unchanged.

## Turbulent Regime Timeout

A slider between 12h and 72h.

### What it controls

When the regime flips to turbulent and you don't respond, this is how long the system waits before auto-executing a defensive move.

### Recommended values by user type

| User type | Recommended timeout |
|---|---|
| Always on phone, checks notifications hourly | 12h |
| Normal work schedule, checks daily | 24h (default) |
| Travels often, checks every 2-3 days | 48h |
| On sabbatical or rarely checks | 72h |

### Trade-off

- **Shorter timeout**: more automatic protection, less time to think
- **Longer timeout**: more control, more risk if you miss notifications

The default of 24h is calibrated to the typical retail user who can check their phone once per day.

### The reminder fires at 50%

If your timeout is 24h, a reminder push fires at T+12h. You get one reminder, not constant nagging.

## Notifications

Four notification types. Each can be set to: push, email, both, or none.

### Types

1. **Regime changes**: fires when regime flips (normal ↔ cautious ↔ turbulent). High importance — this is your primary signal that something needs attention.
2. **Signal published**: fires every Sunday when the new signal publishes. Lower importance. Enable if you want to review promptly; disable if you'll check on Monday morning.
3. **Approval pending**: fires if you have pending approvals that haven't been decided. Fires at signal publish, then again at 50% of timeout if turbulent.
4. **Execution confirmed**: fires when your trades fill. Useful for confirmation, but not time-critical.

### Gating

Midas has a strict engagement philosophy: **notifications are only allowed for these four types**. There are no engagement-driving notifications like "You haven't checked in 3 days!" or "New insight available". If you ever see one, it's a bug.

### Recommended settings

For most users:
- Regime changes: **push** (important, time-sensitive)
- Signal published: **push** (weekly, informational)
- Approval pending: **push** (requires your action)
- Execution confirmed: **email** (confirmation only, not urgent)

### Mobile vs web

Notifications sync across devices. If you approve on mobile, the notification is dismissed on web too. No double-notification spam.

## Broker Connection (IBKR)

### Link account

Click "Link Account" under Broker Connection. This initiates the OAuth flow:

1. Midas generates a secure state token
2. You're redirected to IBKR's authorization page
3. IBKR asks you to log in (to IBKR, not Midas)
4. IBKR shows the scopes Midas is requesting:
   - `read_positions` — see what you own
   - `preview_order` — calculate order impact
   - `place_order` — submit orders (requires biometric per order)
5. You approve. IBKR redirects back to Midas with an auth code.
6. Midas exchanges the code for access + refresh tokens
7. Tokens are encrypted (AES-256-GCM) and stored in the `tokens.user_tokens` table (BYTEA column, never logged)

### What Midas CAN'T do

Scopes Midas explicitly doesn't request:
- **Withdraw funds**: Midas never has withdrawal permission
- **Transfer funds**: Can't ACH, wire, or transfer to other accounts
- **Change account settings**: Can't update your IBKR profile
- **Access statements**: Can't see your tax docs or history beyond current positions

### Unlink account

Click "Unlink Account" to revoke tokens. Midas deletes the encrypted tokens from the database and can no longer access your IBKR account.

Note: this doesn't undo past trades. It just prevents future ones.

## Paper Trading

A toggle switch. Default: **ON** (paper trading enabled).

### What paper trading means

When paper trading is on:
- All trades go to your IBKR **paper account** instead of real money
- Same interface, same approval flow, same signals
- Fills are simulated by IBKR
- Gains/losses are fake

### Why it's on by default

For the first 2 weeks of using Midas, paper trading builds trust:
- You see the signals
- You approve trades
- You watch the portfolio move (in paper land)
- You learn the system without risk

After 2 weeks of paper trading, you can confidently flip to real trading.

### Switching to real trading

Toggle paper trading off. A confirmation dialog fires:
> "You are about to enable live trading with real money. All future approvals will execute against your real IBKR account. Confirm?"

Type your password to confirm. The switch is recorded in the audit trail.

### Switching back to paper

You can flip back to paper anytime. Your real positions stay where they are — the switch only affects future approvals.

## Privacy Settings (read-only)

Midas doesn't have toggleable privacy settings because the privacy model is structural, not preference-based:

- **No user_id in signals**: enforced at database level (boot-time assertion)
- **No cross-user data sharing**: API endpoints are user-scoped
- **No third-party analytics**: no Google Analytics, no Mixpanel, no Segment
- **No ads**: no ad SDK, no tracking pixels
- **No data sale**: we don't have a "sell your data" toggle because we don't sell data

These aren't configurable; they're the product.

## Account Management

Click your email at the bottom of the sidebar. Options:

### Change password
Standard flow: current password + new password + confirm. You're logged out on all devices after.

### Enable MFA (multi-factor auth)
1. Click "Enable MFA"
2. Midas generates a TOTP secret
3. Scan the QR code with Google Authenticator, Authy, 1Password, etc.
4. Enter the 6-digit code to verify
5. MFA is now required on every login

Strongly recommended for anyone with IBKR linked.

### Download my data
Downloads a ZIP containing:
- Your profile
- Your preferences
- Your approval history
- Your audit trail (private events only)
- Your debate history

GDPR-compliant export. The file is JSON + CSV for easy parsing.

### Delete account
Two-step process:
1. Click "Delete Account" → confirmation dialog
2. Type your email and password to confirm
3. Account is scheduled for deletion in 30 days (cooling-off period)
4. Log out

During the 30-day cool-off, you can cancel deletion by logging back in. After 30 days:
- `users.accounts` row is deleted
- `tokens.user_tokens` row is deleted (IBKR connection severed)
- Audit trail records are anonymized (user_id replaced with hash)
- Signal subscriptions (no user_id) are unaffected — the publisher data stays

## Advanced Settings (dev/ops only)

### API base URL
Default: `http://localhost:8000` (dev) or your production URL. Changes require app restart.

### Debug mode
Shows verbose logs in the browser console. Not recommended for production.

### LLM provider override
If you want to override the default LLM provider chain (MiniMax → ZAI → OpenAI → Anthropic), you can specify a single provider. Useful for testing.

## Keyboard shortcuts

On any page:
- `g h` — go to Dashboard
- `g s` — go to Signals
- `g a` — go to Approvals
- `g d` — go to Debate
- `g b` — go to Backtests
- `g t` — go to Trade Log
- `g ,` — go to Settings
- `Esc` — close modal / go back

On Debate chat:
- `Enter` — send message
- `Shift+Enter` — new line
- `↑` — edit last message
- `Esc` — cancel edit

---

**Next**: [13 — Mobile App](13-mobile.md)
