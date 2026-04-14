# 17 — The Publisher Model

This chapter explains why Midas works the way it does from a legal and regulatory perspective. If you're a typical user, this helps you understand the product's quirks. If you're a lawyer evaluating Midas, this is the headline.

## The legal framework: Lowe v. SEC (1985)

In *Lowe v. SEC*, 472 U.S. 181 (1985), the Supreme Court distinguished between:

1. **Investment advisers**: Regulated under the Investment Advisers Act of 1940. Required to register with the SEC, maintain fiduciary duties, file Form ADV, conduct KYC, and accept liability for personalized advice.

2. **Publishers of financial information**: Exempt from the Advisers Act if they meet specific criteria. Examples: newspapers (WSJ), newsletters (Motley Fool), financial magazines (Morningstar).

The test for publisher status:
- **Impersonal**: content is the same for all subscribers
- **Disinterested**: not tied to specific transactions
- **Bona fide**: genuine publication, not a shell for advisory services

Midas is designed to meet all three.

## Why the publisher model matters

### For you (the user)
- **Lower fees**: Midas charges a flat subscription ($9-$29/mo), not a % of assets under management (1%+ at advisers)
- **No KYC theater**: We don't ask for your age, income, goals, or risk tolerance. You pick a portfolio; we publish the signal.
- **You're always in control**: Every trade requires your approval. Midas never executes without you.

### For us (Midas operators)
- **No SEC registration**: Publisher exemption means we don't file Form ADV, maintain state registrations, or accept fiduciary liability
- **Scale**: Impersonal publication means one signal serves 10,000 subscribers — economies of scale
- **Focus**: We can build the best regime detector, not spend half our time on compliance paperwork

### Trade-offs
The publisher model has costs:
- **No personalization**: We can't tailor to your tax situation, retirement date, or goals
- **No fiduciary duty**: If the strategy underperforms, there's no adviser to blame. You chose the portfolio.
- **No tax optimization**: Can't do tax-loss harvesting at your level because we don't know your lots

For users who need personalization, a registered investment adviser (RIA) is the right choice. Midas is the middle ground between "DIY robo" and "1% adviser".

## The three tests

### Test 1: Impersonal

All subscribers to "Growth" get the exact same signal at the same time. We verify this structurally:

- The `signals` table has NO `user_id` column
- The `/signals/latest` endpoint is CDN-cacheable — no per-user variation
- Database grants prevent the publisher role from accessing user data

If we ever shipped a feature that personalized the signal (e.g., "account size under $50k gets a simpler allocation"), we'd break the impersonal test and convert into an adviser.

**What's OK**:
- User picks which portfolio to subscribe to (choice, not personalization)
- User sets notification preferences (UX, not signal content)
- User sets escalation timeout (preference, not signal content)
- Client-side (in the browser/app) computes order delta from impersonal signal + user's IBKR positions

**What's NOT OK**:
- Server-side computing a user-specific allocation
- Adjusting signal weights based on user age
- Showing "recommended for you" content that varies by user
- Using user's IBKR balance to size trade recommendations on the server

### Test 2: Disinterested

Midas's revenue is:
- Subscription fees: $9-$29/mo, flat
- Paid by: subscribers to model portfolios
- NOT tied to: specific trades, trade volume, assets under management

The financial incentive is to publish good signals so subscribers stay subscribed. Not to generate churn for commissions (we don't earn per-trade).

**What's OK**:
- Flat subscription
- Premium tier (more features, not more trades)
- Paper trading tier (free, different product)

**What's NOT OK**:
- Revenue share from IBKR on executed trades
- Fee tied to portfolio turnover
- Referral fees from ETF issuers for allocating to their funds
- AUM-based fees

We've explicitly chosen the flat subscription model to pass this test, even though AUM fees would produce more revenue. The trade-off is worth it for regulatory clarity.

### Test 3: Bona fide

Midas must be a genuine publication, not a shell.

Evidence we meet this:
- Weekly publication cadence (Sunday 7 PM ET), consistent schedule
- Content (signals, reasoning, backtests) is the publication, not a pretense
- Debate agent + reasoning outputs are editorial commentary
- No one-on-one consultation service
- No "premium tier" that unlocks personalized advice

Evidence that would FAIL:
- Infrequent or ad-hoc publication
- Thin content with most value coming from private consultations
- "Premium" tier that adds human advisors
- Content that's just a wrapper around advisory-style recommendations

## What we can and can't say

### We CAN say (publisher speech)
- "The Growth model portfolio recommends 25% equity, 15% gold, 10% bonds"
- "Our regime detector currently reads cautious"
- "Backtest shows Growth beat 60/40 by 1.5% annualized"
- "The Debate agent says XYZ with these citations"

### We CAN'T say (adviser speech)
- "Given your balance, you should allocate X"
- "For your tax situation, buy more bonds"
- "Based on your risk profile, we recommend..."
- "Your portfolio will beat the market"

You'll notice Midas's UI never uses second-person "you should" language for recommendations. We say "the model portfolio recommends" or "the signal is".

## The legal tells — how you can verify

### 1. No user_id in signal endpoints
```bash
curl http://localhost:8000/signals/latest
# Response has no user_id, no user-specific data
```

### 2. CDN-cacheable signals
```bash
curl -I http://localhost:8000/signals/latest
# Returns: Cache-Control: public, max-age=3600
# No Vary: Authorization header
```

If the endpoint varied by user, it couldn't be CDN-cacheable.

### 3. Database schema
Check the migration:
```sql
CREATE TABLE signals (
  id BIGSERIAL PRIMARY KEY,
  model_portfolio_id VARCHAR(50) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  -- ... other fields ...
  -- NO user_id column
);
```

### 4. Boot-time assertions
```bash
.venv/bin/python scripts/start_api.py
# Logs:
#   assertion.publisher_isolation.PASSED
#   assertion.audit_immutability.PASSED
#   assertion.broker_isolation.PASSED
```

If publisher role had grants on user tables, the API would refuse to start.

## Client-side personalization (the exception)

Midas allows ONE form of personalization: the client (your browser / mobile app) can personalize the display and the order preview. This is because:

1. The **server** publishes an impersonal signal
2. The **client** (in your browser or phone) fetches the signal
3. The **client** calls IBKR's API directly to get your positions
4. The **client** computes the delta: target - current = trades
5. The **client** submits trades to IBKR

At no point does the server see your positions or compute a user-specific allocation. Personalization happens on your device, not Midas's infrastructure.

This is the PC3 resolution (product-critical issue 3 from the redteam). Without this architecture, Midas would be advisory. With it, we're clearly publisher.

## What if the line is blurred?

We've designed Midas to be comfortably within the publisher zone, not on the edge. But if the SEC ever interpreted our operations as advisory, the consequences would be:

1. Required to register as an investment adviser
2. Required to file Form ADV, maintain fiduciary duty
3. Required to conduct KYC on all users
4. Required to comply with custody rules
5. Likely required to re-architect or shut down

To prevent this, every engineering decision passes the "would this survive an SEC review?" filter. When in doubt, we err conservative (less personalization, less targeting).

## Why not just register as an adviser?

Options considered:

### Register as RIA
- Pros: can do personalized advice, tax optimization, financial planning
- Cons: $10k/year regulatory cost, 6-month approval, fiduciary duty opens us to lawsuits, AUM fees penalize scale

### Register as BD (broker-dealer)
- Pros: can execute trades directly
- Cons: even more regulatory overhead, licensing, custody requirements

### Stay publisher
- Pros: no registration, scale-friendly, focus on product
- Cons: can't personalize, limited feature set

For v1, publisher is clearly the right choice. If Midas grows to 100k+ users and demand for personalization is overwhelming, registering as an RIA becomes viable.

## The exception: Canadian, UK, EU users

The US publisher exemption applies in the US. Other jurisdictions have different rules:
- **UK**: publishing stock picks requires FCA authorization
- **EU**: MiFID II captures publishing as "investment research" with its own regulations
- **Singapore**: MAS requires a license for "financial advisory services"
- **Canada**: varies by province, typically requires portfolio manager registration

That's why Midas v1 is **US-only**. Signups from other jurisdictions are geofenced at the edge (Cloudflare rules based on IP geolocation).

Phase 2 will consider specific international markets after legal review.

## What about AI?

The debate agent is an interesting legal question. Does an AI responding to a user's question constitute "personalized advice"?

Our position: **no**, if:
1. The AI only cites impersonal signals and impersonal backtests
2. The AI doesn't know the user's balance, positions, or personal circumstances
3. The AI's responses are editorial commentary on the published signal, not prescriptive advice

Our implementation:
- Debate tools fetch signal/backtest data — no user data
- Debate agent has no access to IBKR positions or user balance
- System prompt explicitly instructs the AI to NOT give personalized advice
- AI responses cite model portfolio IDs, not user IDs

If the SEC ever took a different view on AI as advisory, we'd add more explicit disclaimers and restrict the debate to pure explanation (no "what if" scenarios about the user).

## Disclosures required

At signup and in footers:

> Midas publishes impersonal model portfolios under the publisher exemption (Lowe v. SEC). Not personalized investment advice. Past performance does not guarantee future results. Consult a registered investment adviser for advice specific to your situation.

These disclosures are strategically placed where users will see them but not in a way that creates false reliance on them (disclaimer theater). The structural architecture is the real protection.

## For lawyers reviewing Midas

Key documents:
- `workspaces/midas-platform/01-analysis/03-adrs.md` — ADR-001 on the publisher exemption
- `workspaces/midas-platform/01-analysis/07-redteam-convergence.md` — red-team review of legal risks
- `packages/midas-governance/src/midas_governance/assertions.py` — code enforcing the publisher exemption
- `packages/midas-governance/src/midas_governance/migrations/0001_initial_schema.sql` — database grants

We're happy to walk through these on a call. Email `legal@midas.app`.

---

**Next**: [18 — FAQ](18-faq.md)
