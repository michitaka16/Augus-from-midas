# Broker Integration & Regulatory Posture — Midas Platform

**Status**: Research note for v1 scope. Phase 01 analysis.
**Scope**: IBKR API choice, commission modelling, jurisdictional licensing, signal-distribution law, custody.
**Source caveat**: WebSearch was not available in this session. Figures below are drawn from training data (primarily 2024–early 2026) and MUST be verified against live IBKR fee schedules and regulator websites before any implementation commit or customer-facing claim. Citations point to primary-source URLs; the agent did not fetch them live.
**Assumptions inherited**: A1 (IBKR Pro, $50k–$1M/account), A2 (v1 = signal-only, user confirms every trade).

---

## 1. IBKR API Options

Interactive Brokers exposes four distinct programmatic surfaces. Each was designed for a different operator profile, and the differences matter for a multi-user SaaS.

### 1.1 TWS API (native socket — `ibapi`, `ib_insync`)

- **Transport**: TCP socket to a running TWS desktop or IB Gateway process on the user's (or server's) machine. Python wrapper is `ibapi`; the de-facto community wrapper is `ib_insync` (async, far friendlier API).
- **Auth model**: Login is per-TWS-instance. The TWS/Gateway process authenticates the user (username + password + 2FA via IBKR mobile) once; the socket API inherits that session. Auto-restart daily (or weekly on weekends) is required because IBKR force-logs-out TWS/Gateway on a schedule.
- **Latency**: Lowest of the REST options; sub-50ms order round-trip on a co-located gateway is realistic. Market data ticks are streamed.
- **Multi-user suitability**: POOR. One TWS/Gateway = one user account. Running 1,000 gateways on a server farm is feasible but operationally brittle (2FA nag, IP allow-list, daily restarts, GUI dependency on TWS — Gateway is headless but still JVM-based). This is the pattern "home-gamer" quant shops use for themselves, not for SaaS.
- **Order types**: Full catalogue — market, limit, stop, stop-limit, MOC, LOC, MIT, TWAP, VWAP, adaptive, IBKR-native algos (Midprice, Accumulate/Distribute, etc.), bracket, OCA, conditional.
- **Rate limits**: ~50 messages/sec per client; historical data pacing (max ~60 historical requests in any 10-minute window; small-bar-size requests throttled harder).
- **Paper trading**: Yes — separate paper account; toggled at TWS login.
- **Sandbox**: Paper account is the sandbox.

### 1.2 Client Portal Web API (CP API / REST)

- **Transport**: HTTPS REST + WebSocket against a "Client Portal Gateway" (Java) that the user or operator runs. Session-authenticated; the user logs in through a web redirect to IBKR, then the gateway holds a session cookie/token.
- **Auth model**: Browser-based login to a gateway instance. A "keep-alive" ping is required every few minutes or the session dies. In 2024 IBKR added a "headless" CP gateway mode but manual 2FA is still required on first login each day (or after session timeout).
- **Latency**: Higher than the socket API — REST overhead plus gateway hop; typical 100–300ms round-trip.
- **Multi-user suitability**: MODERATE. Conceptually the same "one gateway per user" pattern, but because it is HTTP-based it composes better with containerisation and load balancers than TWS does. Still requires the user to interactively log in.
- **Order types**: Nearly the full TWS catalogue; a few exotic algo order types are missing or lag behind TWS releases.
- **Rate limits**: Documented at 10 req/sec per session for most endpoints; market-data streaming counted separately.
- **Paper trading**: Yes (paper account credentials).
- **Sandbox**: Paper.

### 1.3 FIX CTCI

- **Transport**: FIX 4.2 / 4.4 / 5.0 SP2 over SSL. IBKR calls it "CTCI" (Computer to Computer Interface).
- **Auth model**: Bilateral session — SenderCompID / TargetCompID, negotiated with IBKR. IBKR requires a minimum account commitment (historically USD 1,500/month institutional fee, plus negotiated approval) and you speak to an institutional rep to enable it.
- **Latency**: Lowest (designed for HFT / prime-brokerage flow). Sub-10ms achievable with cross-connect.
- **Multi-user suitability**: EXCELLENT for a true institutional model — one FIX session carries flow for many sub-accounts under an IBKR Prime or Broker-Dealer master. BUT: this requires IBKR Prime Services or an institutional master account with sub-accounts, which in turn typically requires you to be a registered broker-dealer or RIA with custody-adjacent permissions. Not available to a plain SaaS.
- **Order types**: Full institutional catalogue including IOIs, allocation instructions.
- **Rate limits**: Negotiated per session.
- **Paper trading**: Limited FIX paper environment on request.
- **Sandbox**: Via institutional onboarding.

### 1.4 IBKR OAuth (third-party app flow)

- **Transport**: OAuth 1.0a (yes, 1.0a — RSA-SHA256 signed requests) layered on top of the Client Portal Web API. IBKR's official name is "IBKR OAuth" or "Third-Party Access".
- **Auth model**: The user logs in to IBKR's consent screen, approves your application's requested scopes, and IBKR returns an access token. Your app signs subsequent CP Web API requests with the consumer key + access token. No TWS/Gateway process on the user's side; the app talks directly to IBKR's hosted endpoints.
- **Onboarding**: You (Midas) must apply for OAuth credentials via IBKR's "Third-Party Application" program. IBKR reviews your business, security, and — crucially — your regulatory standing. Historically this has been approved for registered advisers, registered broker-dealers, and a small number of fintech partners. A pure unregulated SaaS is unlikely to be approved for production OAuth; you can often get sandbox keys for development.
- **Latency**: Same as CP Web API (IBKR-hosted, so arguably better than a self-hosted CP gateway).
- **Multi-user suitability**: EXCELLENT — this is the only IBKR surface explicitly designed for a multi-tenant third-party app. No per-user gateway process, user retains custody at IBKR, signals/orders flow through signed REST calls.
- **Order types**: Full CP Web API catalogue.
- **Rate limits**: Similar to CP Web API, counted per access token.
- **Paper trading**: Yes (OAuth sandbox tokens against paper accounts).
- **Sandbox**: Yes — this is how you build before IBKR approves production.
- **Primary reference**: `https://www.interactivebrokers.com/en/trading/ib-api.php` and `https://www.interactivebrokers.com/campus/ibkr-api-page/oauth/` (verify live).

### 1.5 Recommendation

**v1 (signal-only, user confirms every trade): Client Portal Web API via IBKR OAuth, sandbox tier.**
- No per-user gateway process → Midas backend scales horizontally without a TWS farm.
- User retains full custody at IBKR; Midas never holds funds.
- "User confirms every trade" is natively supported: Midas displays the signal in the Midas UI, the user clicks "Execute", Midas posts a preview + place-order call against the user's OAuth token, the user sees the IBKR confirmation in their own IBKR app. For the Midas UI flow we can use the OAuth token to **prepare** the order and **require a final user click in Midas** before POSTing `place-order`. This matches the A2 posture.
- The IBKR OAuth approval gate is the main risk: IBKR may refuse production credentials until Midas has some regulatory footing (see §3). Mitigation: run v1 private-beta with self-hosted CP Gateways (each beta user runs their own) until OAuth production is approved; the application code is identical.

**v2 (discretionary, post-licensing): IBKR OAuth + optional FIX CTCI for institutional scale.**
- Same OAuth surface once Midas is a registered RIA / FCA-authorised / MAS CMS-licensed firm — IBKR production approval becomes routine.
- At >~$250M AUM or >1,000 active accounts, consider adding FIX CTCI under an IBKR Prime / Broker master for allocation efficiency and lower per-order cost.

**Rejected for v1**:
- **TWS API**: operationally impossible at multi-tenant scale.
- **FIX CTCI**: requires institutional master account Midas cannot obtain pre-licensing.

---

## 2. IBKR Commissions & Fees (US ETFs, IBKR Pro)

*All figures as of training data (late 2024 / early 2026). Verify at `https://www.interactivebrokers.com/en/pricing/commissions-stocks.php` before any customer-facing claim or cost-model calibration.*

### 2.1 Equity / ETF commissions

| Plan | Structure | Notes |
|---|---|---|
| **IBKR Pro — Fixed** | USD 0.005/share, min USD 1.00, max 1% of trade value. Includes all exchange + regulatory fees (IBKR absorbs them). | Simplest to model. Best for small trades where the 1% cap binds. |
| **IBKR Pro — Tiered** | 0.0035/share for monthly volume ≤300k shares, declining to 0.0005/share at >100M shares. Plus exchange/ECN fees (can be rebate or cost), plus regulatory pass-through. Min USD 0.35/order. | Lower total cost for typical mid-size trades if you capture liquidity rebates. Requires modelling per-venue fees. |
| **IBKR Lite** | Zero commission on US-listed stocks/ETFs, PFOF-routed. Not available to non-US residents. No API for some account types. | Not suitable: Midas needs deterministic routing and global residency support. |

**Recommendation for v1 cost model**: Default to **IBKR Pro Tiered** with a conservative all-in estimate of **USD 0.0035/share commission + ~0.0003/share average exchange fee + regulatory pass-through (§2.2)**. Expose a "Fixed" toggle for users who prefer the 1%-cap simplicity. Calibrate against real fills once paper trading is live.

### 2.2 Exchange and regulatory pass-throughs (Tiered only; Fixed absorbs)

| Fee | Side | Amount (2024–2026) | Source |
|---|---|---|---|
| **SEC Section 31 fee** | Sell only | Rate is set by SEC annually; **FY2025 rate was USD 27.80 per $1,000,000** of sale proceeds (i.e. 0.00278%). Rate changes each fiscal year (Oct 1) and mid-year when the SEC collects its target. Always verify. | `https://www.sec.gov/divisions/marketreg/mrfeepricingspecs.htm` |
| **FINRA Trading Activity Fee (TAF)** | Sell only | **USD 0.000166 per share** on equities (as of 2024 update), max USD 8.30 per trade. Applies to covered securities including ETFs. | `https://www.finra.org/rules-guidance/rulebooks/finra-rules/7000` (Schedule A) |
| **OCC clearing fee** | Options only | N/A for ETF sleeves unless options overlay is added. | |
| **NSCC / DTC clearing** | Both | Bundled into IBKR's clearing fee on tiered; typically <USD 0.0002/share. Not separately itemised. | IBKR commission schedule. |
| **Exchange/ECN fees & rebates** | Both | Varies by venue and add/remove. NYSE/NASDAQ taker fee ~0.0030/share, maker rebate ~0.0020–0.0030/share. IBKR passes through. | Venue fee schedules. |

### 2.3 FX fees (non-USD ETFs or international sleeves)

- IBKR FX conversion: **0.2 bp (0.00002) of trade value, minimum USD 2.00 per conversion** on IBKR Pro. Spot FX spread is interbank (among the tightest in retail).
- For the 8 sleeves as described (US-listed ETFs, precious metals ETFs, gov/corp bond ETFs, REIT ETFs, commodity ETFs, dividend ETFs, EM ETFs), everything can be transacted in USD — FX is only relevant if the user funds in non-USD or Midas recommends a LSE/Xetra-listed ETF. Default the v1 universe to US-listed USD ETFs to avoid FX entirely.

### 2.4 Inactivity fees

- **Eliminated in 2021**. IBKR no longer charges inactivity or account maintenance fees on IBKR Pro or IBKR Lite accounts as of July 2021. Verify at `https://www.interactivebrokers.com/en/pricing/commissions-home.php`.

### 2.5 Market data subscriptions required for the 8 sleeves

Midas backtesting and rebalancing is mostly offline (EODHD primary + Yahoo backup per brief §9), so IBKR market data is only needed for **order routing and fill confirmation at execution time**, not for the decision engine. Minimum viable subscription set:

| Sleeve | Required IBKR real-time feed | Approx monthly (professional tier) | Notes |
|---|---|---|---|
| US ETFs (broad, sector, dividend, EM ADRs) | NYSE (Network A/CTA), Nasdaq (UTP), NYSE American | ~USD 4.50 (non-pro bundle) / ~USD 45+ (pro) | Non-pro users: "US Securities Snapshot and Futures Value Bundle" covers it. Pro users (Midas as an entity) pay materially more. |
| US Bond ETFs (TLT, IEF, LQD, HYG, etc.) | Same as above — they trade on NYSE Arca. | — | Underlying bond market data not needed. |
| Precious metals / commodity ETFs (GLD, SLV, DBC, USO) | Same (NYSE Arca). | — | |
| REIT ETFs (VNQ, IYR) | Same. | — | |

**Key subtlety**: IBKR classifies "professional" vs "non-professional" by the **end-user**. A retail user running Midas signals against their own IBKR account remains non-professional and pays the ~USD 4.50 bundle. If Midas is the subscriber (e.g. a master account pulling data for all users), it is **professional** and fees jump 5–20x. **Design implication**: v1 should route all real-time data subscriptions through the **user's own IBKR account**, not a Midas master data feed. Midas's backend uses EODHD (already licensed) for pricing — IBKR data is only used in the order-confirmation handshake, which the user-side gateway handles.

### 2.6 Cost-model ready table (per round-trip, IBKR Pro Tiered, US ETF, 100 shares at $50)

| Component | Buy | Sell | Notes |
|---|---|---|---|
| IBKR commission (tiered) | USD 0.35 | USD 0.35 | Min USD 0.35/order binds at 100 shares. |
| Exchange fee (avg taker) | ~USD 0.30 | ~USD 0.30 | NYSE Arca taker fee ≈ 0.0030/share. |
| SEC §31 fee | — | USD 0.00014 | 100 × $50 × 0.0000278. |
| FINRA TAF | — | USD 0.0166 | 100 × 0.000166. |
| Clearing pass-through | ~USD 0.02 | ~USD 0.02 | Embedded. |
| **Total per leg** | **~USD 0.67** | **~USD 0.69** | |
| **Round-trip all-in** | | **~USD 1.36** | ~2.7 bp on USD 5,000 notional. |

This is the starting point for the transaction-cost algorithm in brief §7. Slippage and price-impact models sit on top.

---

## 3. Regulatory Posture by Jurisdiction

*Training-data snapshot. Every number, threshold, and exemption must be re-verified against the live regulator site before any customer onboarding. Primary sources linked.*

### 3.1 United States

**Investment Advisers Act 1940** is the controlling federal statute for "investment advisers". State statutes mirror it with carve-outs under USD 100M AUM.

- **Federal vs state RIA threshold**: Advisers with **regulatory AUM ≥ USD 100M** register with the SEC. Below USD 100M, most register with state securities regulators (NASAA model). A few states require registration even for "advice-only" businesses; CA, TX, NY enforce aggressively. Source: `https://www.sec.gov/investment/investment-adviser-registration` and Advisers Act §203A.
- **Form ADV**: Parts 1 (public, machine-readable), 2A (narrative brochure), 2B (brochure supplement for individual advisers), 3 (CRS — Customer Relationship Summary, a 2-page retail-facing disclosure). Filed via IARD. Initial + annual updating amendments.
- **Custody rule (Advisers Act Rule 206(4)-2)**: If the adviser has "custody" of client assets, a qualified custodian must hold them and a surprise annual audit (by an independent PCAOB-registered accountant) is required. **If Midas never holds funds or securities and does not have the authority to withdraw from the client's IBKR account beyond trading, v1 does NOT trigger custody.** The SEC proposed a broadened "safeguarding rule" in 2023 that would expand custody to include discretionary trading authority; status in 2026 should be verified but it was still in proposal/re-proposal stage last known. Source: `https://www.sec.gov/rules-regulations/2023/02/safeguarding-advisory-client-assets`.
- **"Solely incidental" exemption (broker-dealer exclusion)**: Broker-dealers can give investment advice that is "solely incidental" to brokerage without registering as advisers. This does NOT help Midas — Midas is not a BD.
- **Publisher's exemption (Lowe v. SEC, 472 U.S. 181 (1985))**: The Supreme Court held that the Advisers Act does not apply to publishers of **bona fide, impersonal, regular-circulation** investment publications. Three prongs: **(i) bona fide** (genuine publication, not a sham for personalised advice), **(ii) impersonal** (not tailored to the individual client's specific situation), **(iii) regular-circulation** (not episodic, timed to market events). Source: `https://supreme.justia.com/cases/federal/us/472/181/`.
  - **Applicability to Midas v1**: THIS IS THE KEY QUESTION. Midas generates signals that are displayed to the user, who then clicks execute. If each user receives the **same** signal (e.g. "rotate 15% from LQD into TLT"), published on a regular cadence (e.g. weekly rebalance), without reference to the user's personal circumstances → plausible publisher's exemption. If each user receives a **personalised** signal that accounts for their account balance, tax situation, risk tolerance questionnaire, existing positions → **NOT** a publication, it is personalised investment advice and Midas IS acting as an adviser.
  - **The edge Midas v1 sits on**: Sleeve allocations that depend on the user's current portfolio (to compute the trade delta) are arguably personalised. The conservative posture: Midas v1 publishes model portfolios on a schedule; the "what to actually trade" delta is computed client-side by the user's own UI against their IBKR balances; Midas does not store account balances on the server. This posture is defensible under Lowe.
  - **Watch**: The SEC has consistently tried to narrow Lowe when advisers used software to simulate "personalisation at scale". See SEC enforcement actions against robo-newsletters 2019–2024.

**v1 verdict (US)**: **CONDITIONAL GO** — legal without SEC/state RIA registration IF Midas operates strictly as a publisher: impersonal model portfolios, regular cadence, no personalised advice, no account-balance awareness on the server, user clicks every trade. Any deviation (personalised sleeve weights, tax-aware recommendations, per-user risk overrides) falls outside Lowe and requires state RIA (initially) → SEC RIA above USD 100M. State RIA: ~USD 2k–10k in fees, 2–4 months, Series 65 exam for principals. SEC RIA: similar cost, ~3–6 months, no Series 65 requirement at the firm level.

**v2 (discretionary)**: Requires RIA registration unconditionally. Cost USD 15k–50k all-in incl. legal + E&O insurance. Timeline 3–6 months state / 4–9 months SEC.

### 3.2 United Kingdom

- **Controlling statute**: Financial Services and Markets Act 2000 (FSMA). Regulator: Financial Conduct Authority (FCA).
- **Regulated activities (RAO 2001)**: "Advising on investments" (Art 53) and "Arranging deals in investments" (Art 25) are both regulated. Merely publishing a newsletter has a narrower UK publication exemption (RAO Art 54 "advice given in newspapers etc.") but it is more restrictive than Lowe — the publication must be a **newspaper, journal, magazine or other periodical publication, the principal purpose of which is not to give advice of a kind mentioned in Art 53**. A dedicated investment-signals app almost certainly fails the "principal purpose" test.
- **Source**: `https://www.legislation.gov.uk/uksi/2001/544/article/54` and FCA PERG 8.
- **"Arranging"**: Even presenting a "Click to execute" button that passes the order to IBKR is likely "making arrangements" under Art 25 unless structured as pure information display.

**v1 verdict (UK)**: **NO-GO without FCA authorisation.** The UK publication exemption is narrower than Lowe and the "arranging" regulated activity catches the one-click-execute flow. Options: (a) block UK residents from v1 (geofence + ToS), (b) obtain FCA authorisation as an investment adviser with arranging permissions (~6–12 months, ~GBP 50k–150k incl. capital requirement ~GBP 20k, legal, and FCA fees), (c) operate as an Appointed Representative of an authorised principal (~3–6 months, ~GBP 30k/year + profit share). Recommendation: **geofence UK for v1**, pursue FCA or AR route in parallel for v2.

### 3.3 Singapore

- **Controlling statutes**: Securities and Futures Act 2001 (SFA) and Financial Advisers Act 2001 (FAA). Regulator: Monetary Authority of Singapore (MAS).
- **Capital Markets Services (CMS) licence** (SFA): Required for "dealing in capital markets products" and "fund management" (discretionary).
- **Financial Adviser (FA) licence** (FAA): Required for "advising others concerning any investment product". The FAA has an exemption for publications — **FAA §23(1)(f)** covers advice given "in a newspaper, journal, magazine, book, or other periodic publication that is generally available to the public" — similar in spirit to the UK test, requiring genuine publication status.
- **Source**: `https://sso.agc.gov.sg/Act/FAA2001` and MAS guidelines on the FAA.
- MAS has been active in scoping "robo-advisers": 2018 "Guidelines on Provision of Digital Advisory Services" explicitly brought automated advisory under FA licensing with some streamlined requirements for lower-complexity offerings.

**v1 verdict (SG)**: **NO-GO without MAS FA licence** — MAS's 2018 robo-advisory guidelines deliberately close the publication loophole for app-based signal services, and "click to execute" likely trips the FAA advising limb. Options: (a) geofence SG, (b) apply for FA licence (timeline 9–12 months, SGD 30k base capital + legal ~SGD 100k+), (c) partner with an MAS-licensed FA as distributor. Recommendation: **geofence SG for v1**, FA licence is a v2 milestone.

### 3.4 EU / MiFID II

- MiFID II defines "investment advice" as **personal recommendation** to a client. Generic research and model portfolios that are not presented as suitable for the specific client are outside the definition, under ESMA Q&A on investor protection. This is closer to Lowe than the UK RAO.
- BUT: Each EU Member State has national carve-outs and some (DE, FR, NL) interpret "personal recommendation" more broadly. Providing the service into the EU from outside also triggers the third-country regime (MiFIR Art 46/47) which in 2026 is still in flux post-Brexit.

**v1 verdict (EU)**: **GEOFENCE for v1**. Even if a pure-publisher posture is defensible under MiFID II at the EU level, national-level variance and the third-country regime make it too risky for a US-based unregulated SaaS. Revisit in v2 with an EU-authorised partner or a Luxembourg / Ireland investment-firm licence (6–12 months, EUR 125k+ capital).

### 3.5 Summary table

| Jurisdiction | v1 signal-only (user-executes) | v2 discretionary | Rough licensing cost / time for v2 |
|---|---|---|---|
| US | **CONDITIONAL GO** — publisher posture under Lowe | RIA required | USD 15–50k / 3–9 months |
| UK | NO-GO — geofence | FCA authorisation or AR | GBP 50–150k / 6–12 months |
| Singapore | NO-GO — geofence | MAS FA / CMS licence | SGD 100k+ / 9–12 months |
| EU | GEOFENCE (variance too high) | MiFID II investment firm | EUR 150k+ / 6–12 months |

---

## 4. Copy-Trading / Signal Distribution Laws

- **Publisher's exemption (US)**: Covered in §3.1. The core protection for a signal-distribution SaaS in the US.
- **Newsletter rules**: The SEC has periodically enforced against "newsletters" that crossed into personalised advice — e.g. SEC v. Park (2000s), and more recent actions against trading-signal Discord and Telegram groups that took performance fees. Performance-based compensation + personalised channel = adviser.
- **SEC Marketing Rule — Advisers Act Rule 206(4)-1 (effective Nov 2022)**: The "new marketing rule" governs how **registered advisers** advertise performance. Key constraints:
  - Hypothetical / backtest performance requires "policies and procedures reasonably designed to ensure that the performance is relevant to the likely financial situation and investment objectives" of the intended audience — effectively **banning broadcast hypothetical performance to retail**.
  - Gross performance must be accompanied by net performance in equal prominence.
  - All time periods shown must include 1-, 5-, and 10-year (or since-inception if shorter).
  - Testimonials/endorsements now permitted but with disclosures.
  - Source: `https://www.sec.gov/rules-regulations/2020/12/investment-adviser-marketing`.
- **Applicability to Midas v1 (pre-RIA)**: The Marketing Rule binds registered advisers, not publishers. BUT: Midas's public performance claims (e.g. "our 2000–2025 backtest returned X%") will attract SEC attention if v1 ever operates as anything more than a pure publisher, and they will certainly bind Midas the moment it registers. **Design implication**: build the backtest reporting and marketing infrastructure to the Marketing Rule spec from day one — net-of-fee, standardised time periods, hypothetical disclaimers — so there is nothing to retrofit when Midas becomes an RIA.
- **Copy-trading specifically**: Copy-trading services in the US have mostly been structured either as (a) registered advisers offering a model-portfolio service or (b) broker-dealer platforms where the "copier" is actually opening a managed account at the underlying BD. A pure "we push signals, you click" product that does not touch client funds remains publisher-adjacent, but CFTC and SEC have both warned about "signal provider" fraud. Midas needs strong disclaimers, clear "not investment advice" language, and no performance-fee take.

---

## 5. Custody Implications

### 5.1 v1 (signal-only)

- **Midas never holds client funds or securities.** The user opens their own IBKR account under their own name. IBKR is the qualified custodian under Advisers Act Rule 206(4)-2.
- **Midas never has withdrawal authority.** OAuth scopes must be restricted to trading and read-only portfolio queries — no money-movement scope. IBKR's OAuth lets you scope exactly this.
- **No "inadvertent custody" risks**: avoid standing letters of authorisation (SLOAs), avoid taking possession of user credentials, avoid any fee-deduction arrangement where Midas debits the user's IBKR account (charge users through a separate Stripe/bank channel).
- **Net effect**: Midas v1 is outside the custody rule entirely. This is the single biggest compliance simplification and must be defended aggressively — any product decision that tempts Midas towards holding funds, moving money, or debiting client accounts must be rejected unless the custody rule is explicitly planned for.

### 5.2 v2 (discretionary)

Two practical options:
1. **Discretionary RIA with IBKR as qualified custodian**: Midas registers as an RIA, obtains limited trading authority on user IBKR accounts, does NOT hold funds. Still outside direct custody (the proposed 2023 safeguarding rule may change this — monitor). Simplest path. IBKR supports this via its "Advisor" account structure — Midas becomes an IBKR Advisor master and users link their accounts.
2. **Full custody (not recommended)**: Midas takes custody, must use a separate qualified custodian, undergo surprise audits, carry higher E&O insurance. Only justified if Midas wants to offer unified multi-broker views or its own pooled investment vehicle.

**Recommendation**: v2 = option 1 (IBKR Advisor master account + RIA registration). No Midas custody. Ever.

---

## 6. Cross-Reference Hooks

- **Broker integration implementation**: A2 (assumptions), §1.5 recommendation → Phase 02 todo to scaffold IBKR OAuth + CP Web API client.
- **Transaction cost model**: §2.6 table → feeds the cost-modelling workstream called out in user brief §7.
- **Marketing Rule pre-compliance**: §4 → Phase 02 todo to build backtest reporting to 206(4)-1 spec.
- **Geofencing**: §3 → Phase 02 todo for geo/IP/KYC gate blocking UK, SG, EU at signup.
- **No-custody invariant**: §5.1 → Phase 05 codify into a project rule ("no money-movement OAuth scopes, no SLOAs, no fee-deduction from IBKR").

---

## 7. Open Questions for Human Gate

1. Is Midas willing to operate as a strict "publisher" under Lowe for US v1 (impersonal model portfolios, no per-user customisation on the server)? If no, US v1 also becomes NO-GO without state RIA.
2. Is geofencing UK / SG / EU acceptable for v1, or does the product need day-one global reach? Global reach materially changes the v1 timeline (becomes v2 = licensing track).
3. Acceptable to require each beta user to run their own local IBKR CP Gateway while Midas pursues IBKR OAuth production approval? (Adds friction but unblocks v1.)
4. Is v2's target jurisdiction order US → UK → SG, or different? Drives which licence application starts first.
