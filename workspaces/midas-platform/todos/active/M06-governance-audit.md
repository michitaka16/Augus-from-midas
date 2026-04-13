# M06 — Governance & Audit

Dependency: M00 (schema + roles)
Deliverable: D9
Package: `packages/midas-governance`

## Todos

### M06-01: Build PACT publisher envelope
`packages/midas-governance/src/midas_governance/envelopes/publisher.py`
- Define: can read `bars`, `regime_signals`, `fundamentals`, `corp_actions`, `etf_universe`
- Define: can write `signals`, `signal_inputs`, `regime_signals`
- Define: CANNOT read `users`, `user_preferences`, `user_tokens`, `approvals`
- Generate corresponding Postgres GRANT SQL in `migrations/`

### M06-02: Build PACT subscriber envelope
`packages/midas-governance/src/midas_governance/envelopes/subscriber.py`
- Define: can read `signals`, `backtest_runs`, `news_items`
- Define: can read `users`, `user_preferences` (own row only — RLS)
- Define: can write `approvals`, `user_preferences`
- Define: CANNOT write `signals`, `regime_signals`
- Generate corresponding Postgres GRANT SQL + RLS policies

### M06-03: Build PACT broker envelope
`packages/midas-governance/src/midas_governance/envelopes/broker.py`
- Define: can read/write `user_tokens` (own row only — RLS)
- Define: CANNOT read `signals`, `regime_signals`, `users` (separate schema)
- Separate Postgres role: `midas_broker`

### M06-04: Build PACT audit envelope
`packages/midas-governance/src/midas_governance/envelopes/audit.py`
- Define: INSERT + SELECT only on `audit_trail`
- NO UPDATE, NO DELETE, NO TRUNCATE
- Separate Postgres role: `midas_audit`

### M06-05: Build boot-time GRANT assertion
`packages/midas-governance/src/midas_governance/assertions.py`
- On API startup: query `information_schema.role_table_grants`
- Assert: `midas_publisher` has ZERO grants on any table in `users` schema
- Assert: `midas_audit` has no DELETE/UPDATE/TRUNCATE grants
- Fail to start if any assertion fails
- This is the structural enforcement of the publisher exemption (per TC1)

### M06-06: Wire boot-time assertion to CI
- GitHub Actions job: spin up fresh Postgres, run migrations, run assertions
- Any PR that modifies migrations triggers this job
- Failure = PR blocked

### M06-07: Build append-only audit trail
`packages/midas-governance/src/midas_governance/audit/trail.py`
- Mandatory chain hashing: every record includes `prev_hash` (SHA-256 of previous record JSON)
- Tamper detection on read: verify hash chain back N records (configurable, default 100)
- Event types: signal_published, regime_changed, approval_requested, approval_decided, order_submitted, order_filled, escalation_step, user_action
- Write via `midas_audit` Postgres role (INSERT + SELECT only)

### M06-08: Build S3 audit sink
`packages/midas-governance/src/midas_governance/audit/s3_sink.py`
- Daily export: batch audit records from previous day → S3 versioned bucket
- S3 versioning = immutable without deleting entire bucket
- Verify upload: SHA-256 of exported records matches chain hash
- External tamper evidence (per TC4)

### M06-09: Build nightly PACT drift detector
- Compare PACT envelope definitions to actual Postgres grants
- Alert on any drift (grant added that envelope doesn't specify, or grant missing)
- Run as scheduled job

### M06-10: Test — governance Tier 1 (unit)
- Chain hash computation and verification
- Tamper detection (inject bad hash, verify detection)
- Envelope definition → SQL generation correctness

### M06-11: Test — governance Tier 2 (integration, real Postgres)
- Boot-time assertion against real migrated Postgres
- Audit trail: write 100 records, verify chain, attempt tamper, confirm detection
- Role separation: connect as `midas_publisher`, attempt SELECT on `users.*`, confirm denied
- S3 sink: mock S3 (localstack), verify upload
