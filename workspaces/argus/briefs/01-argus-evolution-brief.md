# Argus — Investment Guideline Monitoring

## Source: User, 2026-04-18

## What is Argus?

"Argus" monitors investment portfolios against user-defined investment guidelines. Unlike Midas (which actively trades), Argus observes, checks compliance, and alerts when guidelines are violated or at risk.

**Core metaphor:** Argus Panoptes — the all-seeing giant. The system watches everything.

## Core Distinction from Midas

| | Midas | Argus |
|---|---|---|
| **Primary action** | Generate trade signals | Monitor guideline compliance |
| **Decision maker** | AI (auto-trading) | Human (AI monitors + alerts) |
| **Core loop** | Signal → approval → execution | Position → check → alert |
| **Failure mode** | Missing a trade | False alarm, missed violation |

## What "Investment Guidelines" Means

Examples of guidelines a user might define:
- "Portfolio beta to SPY must stay below 1.2"
- "No more than 30% in any single sector"
- "Maximum 10% allocation to emerging markets"
- "Precious metals allocation between 5-15%"
- "Drawdown cannot exceed 15% from peak"
- "Minimum 20% in investment-grade bonds"
- "No leveraged ETFs"

## User's ML Design Questions

### Q1: Is K-means the right algorithm for ETF clustering?
### Q2: Is cosine similarity the right metric for ETF recommendation?
### Q3: Is 10 features enough?

## Key Constraints
- Week 9 deadline
- Existing Midas codebase exists — must migrate, not rebuild from scratch
