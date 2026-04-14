# 11 — The Audit Trail

Every action Midas takes is recorded. The Trade Log page is your window into this permanent record.

## What the audit trail records

Every state-changing event:
- `signal_published` — a new signal was generated
- `regime_changed` — regime flipped
- `approval_requested` — an approval card was shown to you
- `approval_decided` — you approved, rejected, or held
- `order_submitted` — an order went to IBKR
- `order_filled` — a trade executed
- `escalation_step` — turbulent timer fired (notify, remind, auto-defensive)
- `user_action` — you changed portfolio, updated settings, linked/unlinked IBKR

Each record has:
- `id`: sequential integer
- `prev_hash`: SHA-256 of the previous record's hash + payload (chain linkage)
- `timestamp`: UTC timestamp
- `event_type`: one of the above
- `payload_json`: structured event data
- `actor`: `system`, `user:<id>`, or `api:<client_id>`
- `hash`: SHA-256 of this record's contents + prev_hash

## The chain-hashing property

Every audit record is cryptographically linked to the previous one:

```
record[i].hash = SHA256(record[i].payload + record[i-1].hash)
```

If anyone tampers with record N:
- Record N's hash changes
- Record N+1's prev_hash now mismatches record N's new hash
- The chain breaks at N+1
- Every record from N onwards is detectably invalid

This makes the audit trail **tamper-evident**. You can't silently alter the past — any modification produces a visible inconsistency.

## Viewing the trade log

Click **Trade Log** in the sidebar.

### Filters
Top of the page:
- **All**: every event
- **Signals**: only `signal_published`
- **Approvals**: only `approval_decided`
- **Executions**: only `order_filled`
- **Regime**: only `regime_changed`

### Timeline
Each row shows:
- Timestamp (local timezone)
- Event type (color-coded)
- Description (human-readable summary)

Example:
```
2026-04-13 19:00  signal_published   Growth signal: 6 sleeves, regime normal, cost $4.52
2026-04-13 19:05  approval_requested Approval requested: 2 trades (GLD buy, TLT sell)
2026-04-13 19:12  approval_decided   Approved by user (manual). Biometric confirmed.
2026-04-13 19:13  order_submitted    Market order: BUY 15 GLD
2026-04-13 19:13  order_submitted    Market order: SELL 8 TLT
2026-04-13 19:14  order_filled       GLD: 15 shares @ $213.40
2026-04-13 19:14  order_filled       TLT: 8 shares @ $104.00
```

### Export

Click "Export CSV" to download the full audit trail. Use this for:
- Tax preparation (cross-reference with your IBKR 1099)
- Personal record-keeping
- Analysis (which signals did you approve vs reject? what's your hit rate?)

## The chain verification

The API has an endpoint to verify the chain:

```bash
curl http://localhost:8000/audit/verify | python3 -m json.tool
# {
#   "is_valid": true,
#   "records_checked": 100,
#   "broken_records": []
# }
```

If `is_valid` is false, ops is alerted and the system investigates. You should never see this in production — if you do, something is very wrong.

## S3 external sink

Daily at 3 AM UTC, the previous day's audit records are exported to an S3 versioned bucket. S3 versioning means:
- Files can't be deleted without deleting the entire bucket
- Every version is preserved
- You can re-read any historical day

This is **external tamper evidence**. If someone hacked the Midas database and altered audit records, the S3 copy would show a different hash chain. Cross-verification detects the attack.

The S3 upload is verified: SHA-256 of the exported batch must match the chain hash of the final record in that batch. If it doesn't, the upload is retried.

## What the audit trail is NOT

- **Not your tax records**. IBKR provides 1099-B for tax filing. The audit trail is operational, not tax-grade.
- **Not a full execution log**. Partial fills, order rejections, and ultra-fine execution details stay in IBKR's systems. Midas records the user-facing events only.
- **Not personal identifying information**. The audit trail has user IDs but no PII. Email, name, address are in the `users.accounts` table, separate.

## Why this matters

Three reasons:

### 1. Regulatory compliance
If Midas is ever audited (SEC, state regulators), we need to show:
- What signals were published
- Whether they were uniform across subscribers (publisher model)
- Whether any personalization leaked in
- Whether users had legitimate choice at every approval

The chain-hashed audit trail is the immutable record of all this.

### 2. User trust
You can look at the trade log and see exactly what happened and when. No black boxes. If a trade looks weird, you have a permanent record to reference.

### 3. Debugging
If something went wrong (a trade executed at the wrong price, a regime flipped when it shouldn't), the audit trail shows the exact sequence of events with their inputs. Engineers can replay any failure.

## Public audit records vs private

### Public (no user_id, anyone can query)
- `signal_published`: the signal itself is public. No user_id.
- `regime_changed`: regime is global, public.

### Private (per-user, auth required)
- `approval_requested`, `approval_decided`: tied to a user
- `order_submitted`, `order_filled`: tied to a user
- `user_action`: tied to a user

When you view the Trade Log, you see the global events (signals, regimes) plus your own private events.

## The publisher exemption audit

Every day, an automated check verifies:
- Every signal published to every subscriber of a portfolio is identical (same allocations, same reasoning, same cost estimate)
- No user_id ever appears in the `signals` or `signal_inputs` tables
- The `midas_publisher` Postgres role has zero grants on any user schema

If any check fails, the system locks new publications until ops investigates. This is the structural enforcement of the publisher exemption (see chapter 17).

## Investigating an event

Click any event in the Trade Log to expand the full payload:

```
Event: order_filled
Timestamp: 2026-04-13 19:14:02 UTC
Actor: system
Payload:
  ticker: GLD
  direction: buy
  shares: 15
  fill_price: 213.40
  order_id: "ibkr_order_88xYz"
  status: "filled"
  fill_time: "2026-04-13T19:14:02Z"

Hash: a3f2b890c5e1d7f4...
Prev hash: 9e4f2d1a8b6c3e5f...
```

Hashes are shown so you can independently verify the chain by running:
```python
import hashlib, json
payload_str = json.dumps(payload, sort_keys=True)
expected_hash = hashlib.sha256((prev_hash + payload_str).encode()).hexdigest()
assert expected_hash == record_hash
```

## Retention

Audit records are retained **forever**. The table is never truncated. As volume grows, old records are partitioned but never deleted.

S3 sink retains for 7 years minimum (SEC requirement for investment adviser records, which Midas doesn't technically need but follows as best practice).

## Privacy

Your audit trail is visible only to you and Midas ops (for support and regulatory response). It's never shared with:
- Other users
- Third-party analytics
- Ad networks (Midas has none)

If you request account deletion, your private audit records are anonymized (user_id replaced with a hash). The event timestamps and types remain for regulatory purposes but are no longer linked to you personally.

## The tamper-evidence demo

If you want to verify the chain property yourself:

```bash
# Export audit trail
curl http://localhost:8000/audit/export --header "Authorization: Bearer $TOKEN" > audit.json

# Verify chain
python3 << 'EOF'
import json, hashlib
with open('audit.json') as f:
    records = json.load(f)

prev_hash = "0" * 64
for r in records:
    payload_str = json.dumps(r['payload'], sort_keys=True)
    expected = hashlib.sha256((r['prev_hash'] + payload_str).encode()).hexdigest()
    assert expected == r['hash'], f"BROKEN at record {r['id']}"
    assert r['prev_hash'] == prev_hash, f"LINK BROKEN at record {r['id']}"
    prev_hash = r['hash']
print(f"Verified {len(records)} records, chain is intact")
EOF
```

---

**Next**: [12 — Settings & Preferences](12-settings.md)
