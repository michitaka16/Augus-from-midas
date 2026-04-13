# Midas Compliance — Quick Reference

## Publisher Exemption (Lowe v. SEC)

**The rule**: Midas v1 is an impersonal publisher. The server produces signals that go to ALL subscribers at the same time. No per-user personalization on the server.

### DO
- Publish model portfolios keyed by (model_portfolio_id, timestamp)
- Let users pick which portfolio to subscribe to (client-side)
- Compute order deltas entirely in the client (React/RN)
- Use "the Growth portfolio recommends" language

### DO NOT
- Add user_id to the signals table
- Join signals with users.* on the server
- Show "your portfolio" in server-generated responses
- Compute tax-aware or balance-aware recommendations server-side
- Personalize signal content based on user data

### Structural Enforcement
1. **Schema**: signals table has no user_id column
2. **Postgres roles**: midas_publisher cannot SELECT from users or tokens schemas
3. **Boot-time assertion**: API refuses to start if publisher role has user grants
4. **CI check**: PRs modifying migrations trigger grant assertion

## Turbulent Escalation Protocol
T+0h: notify → T+12h: reminder → T+24h: auto-defensive (configurable 12-72h)

## Geofencing
v1: US only. UK/SG/EU blocked (regulatory).

## Token Security (ADR-013)
- AES-256-GCM encrypted, BYTEA column (not TEXT)
- Single-use refresh tokens
- Scopes: read_positions + preview_order + place_order only
- Separate Postgres role (midas_broker)
