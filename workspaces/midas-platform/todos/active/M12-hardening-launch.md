# M12 — Hardening & Launch Prep

Dependency: M00–M11 all complete
Deliverable: D10 (infrastructure) + launch readiness

## Todos

### M12-01: Security review — full stack
- Run security-reviewer agent across all packages
- OWASP top 10 check on API endpoints
- Token storage audit (encryption, rotation, scope minimization)
- SQL injection scan (all DataFlow queries parameterized)
- XSS scan (all user content encoded in frontend)
- Prompt injection audit on debate agent (news content sanitized, tool inputs validated)
- IBKR OAuth scope verification (no over-privileged scopes)
- Gate: zero CRITICAL, zero HIGH findings

### M12-02: Legal copy review
- Scrub ALL server-side copy for "your portfolio" language (publisher exemption)
- Marketing/landing page copy reviewed for compliance
- Disclaimer: "past performance does not guarantee future results"
- Terms of service: explicitly state Midas is a publisher, not an advisor
- Privacy policy: what data is collected, stored, how long

### M12-03: Build monitoring + alerting dashboard
- Cost model drift: alert when realized fill costs > 2x modeled for 4+ weeks
- Perplexity spend: alert when monthly spend > 60% of infra budget
- Data gaps: alert when any ticker missing > 1 trading day of bars
- EODHD/Yahoo reconciliation: alert when disagreement > 1%
- Regime ensemble disagreement: alert when ensemble stuck in hysteresis > 5 days
- PACT drift: alert when Postgres grants drift from envelope definitions
- Audit chain: alert when hash chain verification fails

### M12-04: Build Perplexity fallback (RSS + FinBERT)
- Self-hosted RSS feed aggregator (financial news sources)
- FinBERT sentiment analysis (local model, no API cost)
- Activated when: Perplexity API down, rate-limited, or cost > threshold
- Debate agent degrades gracefully: "news context limited, citing market data only"

### M12-05: IBKR OAuth production application
- Prepare application materials for IBKR
- Demo video of the product
- Documentation of data access patterns (read positions, preview/place orders)
- If denied: document fallback (manual order entry, per GAP-0004)
- This is an external dependency — track status weekly

### M12-06: Build Docker deployment
- Dockerfile for API service
- docker-compose.yml: API + Postgres/Timescale + Redis
- Environment variable injection via .env
- Health check endpoints
- Migration runner as init container

### M12-07: Build production CI/CD
- `.github/workflows/deploy.yml`: build → test → deploy on merge to main
- Backtest regression gate (M03-09)
- Grounding assertion gate (M10-10)
- PACT assertion gate (M06-06)
- Secret scanning (no .env, no API keys in code)

### M12-08: Build landing page + onboarding copy
- Landing page: lead with regime-aware freeze + debate + backtest transparency
- Differentiators vs Interactive Advisors / Wealthfront / Betterment (per competitive landscape)
- Pricing page: 5 portfolios, flat monthly rate, free tier
- "How it works" explainer: 3 steps (subscribe → review signals → approve trades)
- Trust signals: backtest results (with caveats), audit trail, IBKR custody

### M12-09: Geofencing
- IP-based + account-address geofencing: US-only for v1
- Non-US users: "coming soon" waitlist
- UK/SG/EU explicitly blocked with explanation (regulatory)

### M12-10: Strategy health auto-publish
- If any portfolio underperforms benchmark for 6 consecutive months:
  - Auto-publish "strategy health" entry on Strategy Health dashboard
  - Show: divergence, regime attribution, cost drag
  - Notify subscribers: "Growth portfolio is underperforming 60/40 this quarter. Here's why."
- Transparency > silence (per PC2)

### M12-11: Worst-case documentation
- Each portfolio: worst 12-month rolling return, worst drawdown, longest underwater period
- Published on Backtest Explorer AND landing page
- "You could lose X% in a bad year" — honest marketing

### M12-12: Test — E2E full flow (Playwright + IBKR paper)
### M12-13: Build strategy underperformance detection job
- Scheduled job: monthly, checks each model portfolio against its benchmark
- Detection: 6 consecutive months of underperformance → trigger strategy health auto-publish (M12-10)
- Uses backtest data + live signal performance
- Alert ops team when triggered
- This is the monitoring JOB; M12-10 is the auto-publish action; M08-20 is the UI

### M12-14: Test — hardening components Tier 1
- Monitoring alert rules: each tripwire fires on synthetic threshold breach
- Perplexity fallback: RSS + FinBERT produces valid output when Perplexity is mocked-down
- Geofencing: US IPs pass, non-US IPs blocked, edge cases (VPN, unknown GeoIP)
- Underperformance detection: 6-month consecutive check logic against known data

### M12-15: Build log aggregation
- Structured JSON logging across all Python packages (stdlib logging + JSON formatter)
- Log levels: DEBUG (dev), INFO (prod default), WARN, ERROR
- Log shipping: stdout → Docker log driver → CloudWatch/Datadog/equivalent
- Sensitive data redaction: never log tokens, passwords, API keys, user PII

### M12-16: Build backup/restore strategy
- Postgres WAL archiving to S3 (continuous)
- Point-in-time recovery (PITR) capability
- Automated daily logical backup (pg_dump) as safety net
- Restore runbook: documented steps to restore from backup to a new instance
- Test restore quarterly (add to ops checklist)

### M12-17: Build analytics/telemetry
- Product telemetry: page views, feature adoption, funnel metrics (signup → portfolio → IBKR link → first approval)
- Privacy-first: no PII in telemetry, user consent, anonymous IDs
- Tool: PostHog (self-hosted) or Mixpanel
- Key metrics: weekly active users, approval rate, debate usage, churn rate, time-to-approve

- New user: signup → MFA → choose Growth → link IBKR paper → see dashboard
- Weekly signal: signal published → push notification → approve → order placed at IBKR paper → fill confirmed
- Turbulent: regime flip → freeze → escalation → timeout → auto-defensive → audit logged
- Debate: open chat → ask "why commodities?" → receive grounded response → click citation → see backtest
- Settings: change portfolio → verify dashboard updates → change timeout → verify escalation uses new value
