# Argus Product-Market Fit Analysis

## What is Argus? Investment Guideline Monitoring

Argus watches a portfolio and alerts when it drifts from the investor's stated guidelines.

**The core metaphor:** Argus Panoptes — the all-seeing giant who could watch 100 eyes across 100 bodies simultaneously. The system monitors everything simultaneously.

**The core job-to-be-done:** "I want to know IMMEDIATELY when my portfolio violates my own rules, without having to think about it every day."

---

## Value Proposition

### Before Argus:
- Institutional investors: have compliance teams who manually check portfolios against guidelines
- Retail investors: no tool exists — they either ignore monitoring or check manually (and forget)
- Financial advisors (RIAs): monitoring 50+ client portfolios is impossible without automation

### After Argus:
- Push notification: "ALERT: Your portfolio now has 34% in tech stocks. Your guideline says maximum 30%."
- Before-trade check: "This trade would push your emerging markets allocation from 8% to 13%, exceeding your 10% cap."
- Daily digest: "Your portfolio is within guidelines. No action needed." (reduces anxiety)

---

## Competitive Landscape

| Product | What They Do | Argus Difference |
|---------|-------------|-----------------|
| Bloomberg PORT function | Institutional portfolio analytics | Argus is simpler, retail-focused, alert-first |
| Riskalyze | Risk profiling + compliance | Riskalyze profiles risk tolerance; Argus monitors guideline rules |
| Personal Capital | Wealth management + tracking | Personal Capital is holistic; Argus is guideline-specific |
| SigFig | Portfolio monitoring + alerts | SigFig is generic; Argus lets users define custom rules |
| Institutional PMS (Advent, Orion) | Full compliance suite | Way too expensive for individuals; Argus is $X/mo |

**Blue ocean:** No current product lets retail investors define free-form investment guidelines AND monitors automatically. This is a genuine gap.

---

## AAA Framework Evaluation

### Automate: "Stop manually checking my portfolio"
- Current state: retail investor checks quarterly (if that)
- Argus: continuous monitoring, push alerts
- Operational cost reduction: HIGH (for high-net-worth with many positions)

### Augment: "Make better decisions with AI context"
- Current state: user has no automated way to know if a trade violates their own guidelines
- Argus: real-time guideline checking before trades
- Decision cost reduction: HIGH

### Amplify: "Scale expertise"
- Current state: financial advisor can manually monitor ~20 portfolios effectively
- Argus: advisor monitors 200 portfolios with automated alerts
- Expertise cost reduction: EXTREME (the core value for advisors)

---

## Network Effects

**Accessibility:** Easy to define a guideline (natural language: "no more than 30% in tech")
**Engagement:** Daily/weekly compliance score keeps users coming back
**Personalization:** User-defined rules are inherently personalized
**Connection:** Data sources (IBKR positions, price feeds) are integrations
**Collaboration:** Advisor-client shared view on guideline compliance

---

## Unique Selling Points (Critical Scrutiny)

### USP1: "Real-time guideline monitoring with push alerts"
**Strength:** Genuinely novel for retail. Existing tools are dashboard-first, not alert-first.
**Weakness:** Push alerts require mobile app. Web-only monitoring is insufficient.
**Verdict:** VALID but requires mobile app investment (Week 9?)

### USP2: "Define guidelines in plain English"
**Strength:** Natural language rule definition is intuitive and differentiated.
**Weakness:** Parsing natural language into enforceable rules is HARD. "No more than 30% in tech" requires AI to classify what "tech" means (QQQ, XLK, VGT, IYH all count).
**Risk:** Early version may need structured input (dropdown + number), not free-form NL.
**Verdict:** VALID as a direction, but Week 9 should ship structured input first.

### USP3: "ETF similarity for finding violations"
**Strength:** If ETF clustering can identify "you violated a guideline because your portfolio drifted into tech ETFs that are correlated with your existing tech exposure" — that's genuinely useful.
**Weakness:** Clustering quality is uncertain (see ML design challenges).
**Verdict:** VALID feature, HIGH RISK for Week 9 deadline.

---

## Phase 1 Scope (Week 9)

### Must Have (MVP)
1. IBKR account connection (OAuth)
2. Current portfolio positions display
3. Pre-defined guideline templates (sector max, beta range, drawdown limit)
4. Manual position check ("check if this trade complies")
5. Violation alerts (email/push)
6. Audit trail of all guideline checks

### Week 9 Should NOT Include
- Natural language guideline parsing (defer to Week 10)
- ETF similarity clustering (defer to Week 10-11)
- Advisor multi-portfolio view (defer to Week 12)
- Backtesting guideline rules (defer to Week 12)

### The Critical Path
IBKR OAuth → position fetch → guideline rule engine → violation check → alert delivery
This is achievable in 1 week if the rule engine is simple (threshold-based, not AI).

---

## Financial Model

- **Retail direct:** $X/month subscription
- **Advisor tier:** $Y/month per advisor (monitors unlimited portfolios per advisor)
- **Break-even analysis:** Requires understanding CAC, but the advisor market (RIA with 50-200 clients) is where the revenue is

The retail market is price-sensitive. The advisor market is not (they pass cost to end clients).
