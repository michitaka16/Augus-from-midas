# M08 — Web Application

Dependency: M07 (API handlers provide all data)
Deliverable: D7
Location: `apps/web`

## Todos

### M08-01: Initialize Next.js project
`apps/web/`
- Next.js 14+ with App Router
- TypeScript, Tailwind CSS, shadcn/ui
- Dark mode default (financial UX convention)
- Import shared types from `shared/types/`
- Import design tokens from `shared/tokens/`
- API client library in `apps/web/src/lib/api.ts`

### M08-02: Build design system foundation
`apps/web/src/components/`
- Color palette: dark mode first, financial-grade (Mercury/Stripe/Linear references)
- Typography scale, spacing tokens
- Card component (used for signal detail, approval card, regime banner)
- Chart components (line, bar, area — for backtest results, portfolio performance)
- Citation card component (for debate agent responses)
- Status indicator (regime: normal=green, cautious=amber, turbulent=red)

### M08-03: Build auth pages
- Login page (email + password + MFA)
- Signup page (email + password + MFA setup)
- Password reset flow
- Protected route wrapper (redirect to login if no JWT)

### M08-04: Build Dashboard page
The "calm state" screen — must give user permission to close the app.
- Portfolio value (current, change today, change this week)
- P&L vs benchmark (Growth vs 60/40, chart)
- Current regime indicator (normal/cautious/turbulent with confidence %)
- Next signal date countdown
- Pending approvals count (badge, links to approvals page)
- Quick summary: "Your portfolio is on track. Next rebalance in 3 days."

### M08-05: Wire Dashboard to API
- `GET /signals/{portfolio_id}/latest` for current allocation
- `GET /regime/current` for regime state
- `GET /approvals/pending` for count
- Polling: refresh every 60s when tab active (screen-active pull policy)

### M08-06: Build Signal Detail page
- Per-sleeve allocation breakdown (pie chart + table)
- Reasoning card: why each sleeve weight was chosen
- Cost estimate breakdown (commissions, slippage, impact)
- Backtest context: link to relevant backtest run
- Regime context: current regime + recent regime history

### M08-07: Wire Signal Detail to API
- `GET /signals/{portfolio_id}/latest` for allocations + reasoning
- `GET /backtests/{portfolio_id}/latest` for backtest context
- `GET /regime/current` for regime context

### M08-08: Build Pending Approvals page
- Grouped rebalance card (all trades in one view)
- Per-trade: ticker, direction, shares, estimated cost
- Per-item opt-out checkboxes (uncheck to skip a trade)
- Regime banner at top: current regime + confidence
- "Why this rebalance?" link → debate chat with context pre-loaded
- Approve All button (biometric/MFA confirm via WebAuthn)
- Skip button (acknowledge, no action)
- For turbulent: escalation countdown visible ("auto-defensive in 18h unless you decide")

### M08-09: Wire Pending Approvals to API + IBKR
- `GET /approvals/pending` for pending list
- `POST /approvals/{id}/approve` on confirm
- Client-side order preview: fetch positions from IBKR (via broker package), compute delta against signal
- Feature-flagged: if legal flag off, show only target allocation without position delta

### M08-10: Build Debate Chat page
- Full conversation UI (message list, input box)
- Citation cards: inline expandable cards showing cited signal/backtest data
- Backtest drill-down: click a citation to see the full backtest result
- Regime context sidebar (current signals, confidence)
- "Challenge this" button on AI responses (prompts counter-argument)
- Streaming response (SSE or WebSocket)

### M08-11: Wire Debate Chat to API
- `POST /debate/message` for sending messages
- `GET /debate/history` for conversation history
- Citation resolution: click citation → `GET /backtests/{run_id}` or `GET /signals/{id}`

### M08-12: Build Backtest Explorer page
- Model portfolio selector (tabs for 5 portfolios)
- Multi-horizon table: 1y, 3y, 5y, 10y, full — Sharpe, max drawdown, turnover, cost drag
- Deflated Sharpe + PBO display
- Regime view: performance split by normal/cautious/turbulent
- Sleeve view: per-sleeve contribution heatmap
- Cost drag view: cumulative cost chart over time
- Benchmark comparison: side-by-side vs 60/40, equal-weight, VTI

### M08-13: Wire Backtest Explorer to API
- `GET /backtests/{portfolio_id}/latest` for all metrics

### M08-14: Build Trade Log / Audit page
- Immutable timeline of every signal, approval, execution
- Filterable: by date range, by event type, by portfolio
- Each entry: timestamp, event type, details (expand for full JSON)
- Export to CSV

### M08-15: Wire Trade Log to API
- `GET /audit/trail` (paginated, filtered)

### ~~M08-16: Build Regime Call History page~~ — DEFERRED to v1.1
### ~~M08-17: Wire Regime History to API~~ — DEFERRED to v1.1

### M08-18: Build Settings page
- Model portfolio selection (switch between 5)
- Notification preferences (push, email, both, none per category)
- Escalation timeout slider (12h–72h)
- IBKR account link/unlink
- Paper trading toggle
- Account: email, password change, MFA management

### M08-19: Wire Settings to API
- `PUT /account/portfolio`
- `PUT /account/preferences`
- `POST /account/ibkr/link` / `DELETE /account/ibkr/unlink`

### ~~M08-20: Build Strategy Health dashboard~~ — DEFERRED to v1.1
### ~~M08-21: Wire Strategy Health to API~~ — DEFERRED to v1.1

### M08-22: Responsive polish + dark mode
- All pages responsive: desktop-first but functional on tablet/mobile-web
- Dark mode default, light mode toggle
- No layout breaks at any viewport

### M08-23: Build onboarding flow
- Progressive trust-building: paper trading week 1-2, small allocation week 3, full week 4 (per PH2)
- Step indicators, progress bar
- Each step explains "why" (trust-building copy)

### M08-26: Build error pages
- 404 (not found): friendly message + link to dashboard
- 500 (server error): friendly message + "try again" + support link
- Maintenance mode: scheduled maintenance banner with expected uptime
- IBKR connection error: specific guidance to re-link account
- Offline state: "no connection" banner (mobile web)

### M08-27: Accessibility audit (WCAG 2.1 AA)
- Keyboard navigation on all interactive elements
- Screen reader labels on charts (alt text for chart images, data tables as fallback)
- Color contrast verification (especially regime status indicators — not just red/green)
- Focus management in debate chat (auto-focus input, announce new messages)
- aria-live regions for real-time updates (regime status, pending count)

### M08-24: Test — web app Tier 1
- Component rendering tests (React Testing Library)
- Auth flow state management
- Citation card rendering with mock data

### M08-25: Test — web app Tier 3 (E2E, Playwright)
- Signup → login → dashboard → view signal → approve → confirm
- Debate chat: send message → receive response with citations → click citation
- Backtest explorer: switch portfolio, switch view, verify data renders
- Settings: change portfolio → verify dashboard updates
