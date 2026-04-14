# 13 — Mobile App

The Midas mobile app is designed for one job: **approve trades from your phone when a signal publishes**.

## Installation

### iOS (TestFlight)

1. Email `beta@midas.app` with your Apple ID email
2. You'll receive a TestFlight invite within 24 hours
3. Install TestFlight from the App Store
4. Tap the invite link → install Midas

### Android (Play Store internal testing)

1. Email `beta@midas.app` with your Google Play email
2. You'll receive an internal tester invite
3. Accept the invite → install from Play Store

### Expo Go (developers only)

If you're running the development environment:
```bash
cd apps/mobile
npx expo start
# Scan the QR code with Expo Go app
```

## First launch

1. Open the app
2. Log in with your Midas credentials (same as web)
3. Grant notification permissions (strongly recommended)
4. Face ID / Touch ID setup prompt — enable to skip password on every approval

## The two core screens

Mobile is intentionally minimal. Only two screens.

### Dashboard

Fetches the same `/regime/current` and `/signals/latest` endpoints as the web Dashboard.

Layout:
```
┌──────────────────────────┐
│  ● Normal        82%     │  <- regime banner
│                          │
│  Portfolio Value         │
│  $142,850                │
│  +$1,230 (0.87%) today   │
│                          │
│  Pending Approvals       │
│  0                       │
│  All clear               │
│                          │
│  [Debate with AI]        │
└──────────────────────────┘
```

Tap the regime banner → expands to show the 8 signal values.

Tap "Pending Approvals" → navigates to the approval card (if > 0).

### Approval Card

This is the most important screen. Designed for one-handed, under-10-second approvals.

Layout:
```
┌──────────────────────────┐
│  ● Normal Regime   82%   │
│                          │
│  Growth Portfolio        │
│  Weekly Rebalance — 2    │
│                          │
│  ┌─────────────────────┐ │
│  │ GLD   BUY 15        │ │
│  │ $2,847   $1.02 cost │ │
│  │ ─────────────────   │ │
│  │ TLT   SELL 8        │ │
│  │ $832     $0.68 cost │ │
│  └─────────────────────┘ │
│                          │
│  Net Cost: $1.70         │
│  Impact: +0.3% gold      │
│                          │
│  ┌──────────────────┐    │
│  │   Approve All    │    │
│  └──────────────────┘    │
│  [Skip]                  │
│  Why this rebalance?     │
└──────────────────────────┘
```

Swipe right on a trade → toggle include/exclude.
Tap "Approve All" → Face ID / Touch ID prompt → trades submit.

## Push notifications

### Setup

On first launch, iOS/Android asks for notification permission. Grant it.

If you decline and want to re-enable:
- iOS: Settings → Notifications → Midas → Allow Notifications
- Android: Settings → Apps → Midas → Notifications

### Types

Same as web (see chapter 12):
- Regime changes
- Signal published
- Approval pending
- Execution confirmed

### Deep linking

Every notification deep-links to the relevant screen:
- "Regime: Turbulent" → opens the approval card directly
- "Growth signal published" → opens the approval card
- "Trades executed" → opens the Dashboard

Tap the notification → biometric → done. Ideal flow takes 8 seconds.

## Biometric authentication

### When it's used

Every trade approval. Mobile requires biometric confirmation before submitting orders to IBKR. This is NOT a Midas requirement — it's an IBKR compliance requirement for third-party apps.

### Setup

iOS: Settings → Face ID & Passcode → enable for Midas app
Android: Settings → Biometrics → enable Fingerprint for Midas

If biometric isn't available (older device), falls back to device PIN.

### Failed biometric

If Face ID fails 3 times, fallback to password. If password fails 5 times, account locks for 15 minutes.

## What mobile doesn't have

To keep the mobile app minimal, these web-only features are not on mobile:
- Signal history list
- Backtest explorer (too data-dense for small screens)
- Audit log (view on web)
- Settings deep dive (use web for portfolio switching, IBKR linking)
- Debate chat (coming in Phase 2)

The philosophy: mobile is for **action**. Complex review happens on web.

## Offline support

The app caches:
- Last known regime state
- Last published signal
- Pending approvals

When offline, you can view this data but can't approve (approval requires network to submit to IBKR).

When you regain connectivity, the app syncs with the server. Any signals or regime changes that happened while you were offline appear as catch-up notifications.

## Background behavior

### iOS

Midas uses:
- Silent push notifications (for regime changes that require immediate action)
- Regular push notifications (for signals, approvals)
- NO background fetch (battery drain not worth the marginal freshness)

### Android

Similar. Uses Firebase Cloud Messaging for push.

### Battery impact

Minimal. The app does no polling when backgrounded. Only wakes on push.

## Privacy

The mobile app stores:
- Your login token (keychain on iOS, EncryptedSharedPreferences on Android)
- Cached dashboard/approval data (plain storage, no PII beyond what's already in the app)
- Notification tokens (sent to Midas server for push delivery)

The app does NOT store:
- Your password (use Face ID / re-enter on session expiry)
- Your IBKR credentials (stored server-side, encrypted)
- Any data from other users

## Logging out

Settings → Log Out. This:
- Deletes the login token from keychain
- Clears cached data
- Unregisters push notifications

Next launch requires fresh login.

## Updating

App updates ship through TestFlight / Play Store. We aim for monthly releases. Urgent security updates ship within 48 hours.

## Known limitations (v1)

- No tablet layout (iPhone/Android phone only)
- No Apple Watch complication (planned for Phase 2)
- No widget on home screen (planned)
- English only
- US time zones only (other zones show times in ET)

---

**Next**: [14 — IBKR Integration](14-ibkr.md)
