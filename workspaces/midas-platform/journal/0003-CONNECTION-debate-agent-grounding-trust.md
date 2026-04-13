---
type: CONNECTION
date: 2026-04-12
created_at: 2026-04-12T12:10:00Z
author: agent
session_id: analyze-session-1
session_turn: 14
project: midas-platform
topic: Debate agent grounding contract is both the product differentiator and the trust foundation
phase: analyze
tags: [debate-agent, grounding, trust, ux, kaizen, hallucination]
---

# Grounding = Product Differentiator = Trust Foundation

## Connection

Three independent research streams converged on the same conclusion:

1. **Competitive landscape** (01-research/01): No competitor offers an interactive debate agent. Titan has pre-recorded human video explainers, Composer shows IF/THEN logic, but nobody lets the user argue with the system's reasoning interactively.

2. **UI/UX research** (01-research/05): The debate screen is identified as the #1 screen that justifies the price. "If the AI ever invents a number or backtest result, the product is dead." Hard grounding contract required.

3. **Framework architecture** (01-research/06): Kaizen lacks a first-class grounded-citation primitive (`GroundedSignature`). Midas must hand-build it: every DebateAgent response includes `cited_ids: list[CitationRef]`, and `ungrounded_claims` must be empty or the response is rejected before reaching the user.

The connection: the grounding contract is not just a safety feature — it IS the product. If the debate agent is grounded, it is trustworthy, and trust is why Alex pays. If it is ungrounded, it is a chatbot wearing a financial advisor costume, and the product has no reason to exist.

This means:
- Grounding verification must be tested in CI with the same rigor as the backtest engine
- The debate agent's tools must return structured data (signal values, backtest stats, cost numbers), not prose
- The LLM composes natural language AROUND the structured data, not from memory
- Any Kaizen upgrade that changes tool-calling behavior is a release blocker for Midas

## For Discussion

1. The grounding contract rejects responses with ungrounded claims. What happens when the user asks a question that genuinely cannot be answered with existing signals/backtests (e.g., "what do you think about Bitcoin?")? Should the agent say "I don't have data on that" or attempt a grounded analogy from the commodity sleeve?
2. If Kaizen had shipped a first-class `GroundedSignature` primitive (counterfactual), would you trust it out-of-the-box, or would Midas still need its own verification layer on top?
3. The grounding contract creates a hard dependency between the debate agent and the data fabric (every cited ID must resolve). How does this affect the deployment order — can the debate agent launch before all historical backtests are loaded?
