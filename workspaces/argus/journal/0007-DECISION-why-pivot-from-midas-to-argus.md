---
type: DECISION
date: 2026-04-19
created_at: 2026-04-19T00:00:00
author: co-authored
session_id: current
project: argus
topic: Why Argus — reframing from portfolio execution to guideline governance
phase: analyze
tags: [midas-to-argus, product-strategy, scope-change, argus-vs-midas]
---

## Decision: Why the Project Reframed from Midas to Argus

### The Framing Shift

Midas was designed as a portfolio execution system — it generates allocation signals and executes trades. Argus was introduced as a separate concern: verifying whether the portfolio actually follows the investment guidelines the user intended to follow.

This is not a feature addition — it is a new primary function with a distinct user need: "Did I stay within my own rules?" rather than "What should I buy next?"

### What Was Kept from Midas

- ETF universe (23 tickers)
- Signal generation pipeline (momentum, volatility, covariance)
- Sleeve taxonomy (10 sleeves as domain prior)
- IBKR integration for live positions

### What Was Added in Argus

- Guideline rule engine (hard/soft constraint evaluation)
- ETF similarity / substitution detection (cosine similarity on feature vectors)
- Backtest capability for guideline rules
- Forward-looking violation detection

### What Was Explicitly Excluded

- Trade execution (remains in Midas)
- Real-time signal generation (not needed for governance)
- Position history storage (publisher exemption concern — the publisher of a model does not store client positions)

### Why the Pivot Was Necessary

The allocator (Midas) produces allocation signals. Those signals — once executed — need to be verified against the guidelines that motivated them. Without Argus, there is no feedback loop: the investor knows what they bought but not whether the portfolio actually complies with their stated constraints. The Geopolitical Screen, Ethical Investor, and Climate First presets exist because the user set them — Argus ensures they are actually honored.

## For Discussion

1. Is the primary user of Argus the same investor using Midas, or a compliance officer reviewing a client's portfolio? The answer affects terminology ("my guidelines" vs "their guidelines") and alert severity.

2. Is there a future where Argus operates independently of Midas, evaluating guidelines for a portfolio built outside this system entirely? If so, the IBKR position fetch is the only required integration.

3. Should the repository be reorganized (`midas/` becomes `midas/` + `argus/`) to reflect the two distinct products, or does keeping them in one repo reflect that Argus is a feature of the Midas platform?
