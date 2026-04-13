---
type: DISCOVERY
date: 2026-04-12
created_at: 2026-04-12T12:00:00Z
author: agent
session_id: analyze-session-1
session_turn: 8
project: midas-platform
topic: Publisher's exemption reshapes v1 from personalized advisor to impersonal publisher
phase: analyze
tags: [regulatory, legal, publisher-exemption, lowe-v-sec, architecture]
---

# The Publisher's Exemption Reshapes Everything

## Finding

The user's original brief described a personalized autonomous portfolio manager: "make me money, don't trade without my permission in turbulent markets." The natural implementation is a per-user risk profile with per-user portfolio optimization.

Regulatory research revealed this requires an RIA license (SEC state registration for <$100M AUM), which takes 6–12 months and significantly expands scope (compliance, Form ADV, custody rule). The only legally-clean v1 path in the US is the **publisher's exemption** (Lowe v. SEC, 1985): publish impersonal model portfolios to all subscribers on a regular cadence. No per-user personalization on the server.

This single constraint cascades through the entire architecture:
- `signals` table has NO `user_id` column — structurally enforced, not policy
- No tax-loss harvesting, no account-balance-aware recommendations, no personalized risk scoring
- 3 model portfolios (Growth/Balanced/Conservative) instead of per-user optimization
- User-specific state (which portfolio they subscribe to, notification prefs) lives in a separate schema never joined with signals
- PACT envelopes enforce publisher/subscriber separation at the Postgres role level
- Marketing copy must avoid "your portfolio" language

The user's "go big or go home" risk appetite is expressed by CHOOSING the Growth model portfolio — not by the server computing a personalized aggressive allocation.

## Impact

This is the single most consequential finding of the analysis phase. It transforms Midas from "personalized robo-advisor" to "impersonal signal publisher with a debate layer." The product is still valuable — but the value proposition shifts from "it manages YOUR money" to "it publishes the best model portfolios and helps you understand them."

## For Discussion

1. Given that the publisher's exemption requires impersonal delivery, does the "debate with AI" feature risk collapsing the exemption if the AI tailors its responses based on the user's stated portfolio or risk preferences? Where is the line between "editorial commentary" and "personalized advice"?
2. If the exemption had not existed (counterfactual), would you have chosen to pursue RIA registration for v1, or would you have launched as paper-trading/educational only?
3. The 3 model portfolios (Growth/Balanced/Conservative) are a proxy for the user's risk appetite. Is 3 enough granularity, or should there be 5–7 portfolios to capture more of the "go big" spectrum?
