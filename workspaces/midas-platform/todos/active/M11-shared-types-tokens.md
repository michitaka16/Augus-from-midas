# M11 — Shared Types & Design Tokens

Dependency: M00 (monorepo)
Deliverable: Cross-cutting (D7 + D8)
Location: `shared/`

## Todos

### M11-01: Build shared TypeScript domain types
`shared/types/src/`
- `signal.ts`: Signal, Allocation, SleeveWeight, CostBreakdown, SignalHistory
- `regime.ts`: RegimeState, RegimeTransition, SignalValue
- `portfolio.ts`: ModelPortfolio, PortfolioSummary, PerformanceMetrics
- `backtest.ts`: BacktestRun, BacktestMetrics, RegimeConditionalStats, BenchmarkComparison
- `approval.ts`: Approval, ApprovalStatus, EscalationState
- `debate.ts`: Message, CitationRef, CounterScenario
- `user.ts`: User, UserPreferences, NotificationSettings
- `audit.ts`: AuditEntry, EventType
- All types match the Python dataclass equivalents in backend packages

### M11-02: Build design tokens
`shared/tokens/src/`
- Colors: dark mode primary (background, surface, accent, status: green/amber/red for regime)
- Typography: font family (Inter or equivalent), size scale, weight scale
- Spacing: 4px grid system
- Shadows, borders, radii
- Chart colors: per-sleeve color coding (consistent across all charts)
- Export as CSS custom properties + JS object + Tailwind config extension

### M11-03: Build pricing/tier configuration
- 5 model portfolios with pricing: Aggressive Growth ($29/mo), Growth ($29/mo), Balanced ($19/mo), Conservative ($9/mo), Income ($19/mo)
- Flat rate (no AUM %) — preserves publisher exemption (per PH5)
- Free tier: delayed signals (1 week) + limited debate (5 messages/week) + backtest explorer (read-only)
- Shared config consumed by web + mobile + API (subscription validation)

### M11-04: Test — shared types + tokens Tier 1
- TypeScript types compile without errors
- Design tokens export correctly (CSS variables, JS object, Tailwind extension)
- Pricing config internal consistency: every portfolio has a name, price, vol_target, description
- Token color contrast verification (automated WCAG check on palette pairs)
