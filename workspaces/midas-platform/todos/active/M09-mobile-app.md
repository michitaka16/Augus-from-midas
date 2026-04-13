# M09 — Mobile Application

Dependency: M07 (API), M08 (shared design tokens)
Deliverable: D8
Location: `apps/mobile`

## Todos

### M09-01: Initialize React Native Expo project
`apps/mobile/`
- Expo SDK (latest)
- TypeScript
- NativeWind or Tamagui for styling (match web dark-mode-first palette)
- Import shared types from `shared/types/`
- Import design tokens from `shared/tokens/`
- Configure expo-local-authentication (biometrics)
- Configure expo-notifications (push)

### M09-02: Build biometric auth
- Face ID / Touch ID via expo-local-authentication
- Biometric required for: login, order approval, settings changes
- Fallback: PIN if biometric unavailable

### M09-03: Build push notification handler
- Register for Expo Push Notifications on login
- Handle notification types: regime_changed, approval_pending, execution_confirmed
- Deep link: tap notification → specific pending approval screen
- Badge count: pending approvals

### M09-04: Build Dashboard screen (read-only)
- Portfolio value + change
- Current regime indicator
- Pending approvals count (tap → approvals)
- "All clear" state when nothing needs attention

### M09-05: Wire Dashboard to API
- Same endpoints as web: `/signals/latest`, `/regime/current`, `/approvals/pending`
- Polling: refresh on screen focus

### M09-06: Build Approval Card screen
- One-screen rebalance card (mobile optimized)
- Swipe gestures: swipe right to approve, swipe left to skip
- Per-trade list with opt-out toggles
- Regime banner + escalation countdown
- Biometric confirm on approve

### M09-07: Wire Approval Card to API + IBKR
- `GET /approvals/pending`
- `POST /approvals/{id}/approve`
- Client-side order preview (positions fetched from IBKR, delta computed locally)

### M09-08: Build Debate Chat screen (simplified)
- Chat interface (mobile-optimized, fewer citation details)
- Citation cards: tap to expand
- Quick-reply suggestions ("Why this?", "What if I skip?", "Show backtest")

### M09-09: Wire Debate Chat to API
- `POST /debate/message`
- `GET /debate/history`

### M09-10: Build Settings screen
- Portfolio selection
- Notification preferences
- Escalation timeout
- IBKR link status
- Account management

### M09-11: Wire Settings to API
- Same endpoints as web

### M09-12: Test — mobile Tier 1
- Component rendering (React Native Testing Library)
- Deep link routing
- Biometric mock

### M09-13: Test — mobile Tier 3 (E2E, Detox)
- Push notification → open app → approval card → biometric → approve
- Dashboard renders with real API data
- Settings change persists
