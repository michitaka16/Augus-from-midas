# M10 — Debate Agent

Dependency: M01 (data fabric for tools), M02 (strategy for signal reads), M03 (backtest for citation targets)
Deliverable: D6
Package: `packages/midas-debate`

## Todos

### M10-01: Build DebateSignature
`packages/midas-debate/src/midas_debate/agent/signature.py`
- Kaizen `Signature` subclass
- Input fields: `user_message: str`, `conversation_history: list[Message]`, `current_regime: RegimeState`, `current_signal: Signal`
- Output fields: `response: str`, `cited_ids: list[CitationRef]`, `ungrounded_claims: list[str]` (MUST be empty), `suggested_followups: list[str]`
- `CitationRef`: type (signal/backtest/cost/news), id, display_value

### M10-02: Build DebateAgent
`packages/midas-debate/src/midas_debate/agent/debate.py`
- Kaizen `BaseAgent` subclass with `DebateSignature`
- System prompt: "You are the Midas portfolio debate agent. Every claim must cite a signal, backtest, or cost model output. Defend positions with data. Do not capitulate to bad arguments. If the user disagrees, show counter-scenarios."
- LLM-first: ZERO deterministic routing, ZERO keyword matching, ZERO intent classification in Python (per `rules/agent-reasoning.md`)
- LLM model from `.env` (LLM_MODEL)

### M10-03: Build dumb data tools
`packages/midas-debate/src/midas_debate/tools/`
Each tool is a pure data endpoint — fetch, return, no decisions:
- `fetch_signal(signal_id) -> Signal` — reads from `signals` table
- `fetch_current_recommendation(portfolio_id) -> Signal` — latest signal
- `fetch_backtest_run(run_id) -> BacktestReport` — reads from `backtest_runs`
- `fetch_cost_model(ticker, shares, direction) -> CostBreakdown` — calls TransactionCostNode
- `fetch_regime_state() -> RegimeState` — current regime + all signal values
- `fetch_news_by_id(news_id) -> NewsItem` — reads from `news_items`
- `search_news(query, k=5) -> list[NewsItem]` — pgvector semantic search
- `fetch_regime_history(limit=20) -> list[RegimeTransition]` — past transitions + outcomes

### M10-04: Wire tools to data fabric + strategy packages
- Tools call `midas_data.fabric.*` for reads
- Tools call `midas_strategy.cost.*` for cost model
- Tools call `midas_backtest.reports.*` for backtest data
- NO decision logic in wiring — tools return raw data, LLM interprets

### M10-05: Build grounding verification
`packages/midas-debate/src/midas_debate/grounding/verify.py`
- Post-generation check: for every `CitationRef` in `cited_ids`, verify the ID resolves
  - Signal ID → exists in `signals` table
  - Backtest run ID → exists in `backtest_runs` table
  - Cost model → valid computation (can be re-run)
  - News ID → exists in `news_items` table
- If ANY cited ID doesn't resolve → reject response, re-generate with error context
- If `ungrounded_claims` is non-empty → reject response unconditionally
- News citations marked as "external, unverified" in the CitationRef (per TH2)

### M10-06: Build counter-scenario capability
`packages/midas-debate/src/midas_debate/scenarios/counter.py`
- Tool: `compute_counter_scenario(override_allocations) -> CounterResult`
- User says "what if I skip this rebalance" → tool runs the strategy workflow with zero rebalance and returns:
  - Expected portfolio drift over 1 week, 1 month
  - Cost saved by not rebalancing
  - Risk change (vol target drift)
  - Historical analogy: times when skipping would have helped/hurt
- LLM composes natural language around the structured result

### M10-07: Build sycophancy resistance
- System prompt includes: "When the user challenges your recommendation with weak arguments, explain why their reasoning is flawed. Cite data. Do not agree just because the user pushed back. You may yield ONLY when the user presents evidence you haven't considered."
- Test dataset: 20 adversarial challenges (e.g., "gold is definitely going up" with no data) — agent should defend its position in >80% of cases

### M10-08: Test — debate agent Tier 1 (unit)
- DebateSignature construction
- Grounding verification: valid IDs pass, invalid IDs rejected, empty ungrounded_claims enforced
- Counter-scenario tool returns structured data
- Tools are pure data endpoints (no conditionals on input content)

### M10-09: Test — debate agent Tier 2 (integration, real Postgres + LLM)
- 20-turn conversation about a regime flip: zero ungrounded claims
- Counter-scenario: "what if I skip" returns grounded cost/opportunity analysis
- Sycophancy: 20 adversarial challenges, agent defends >80%
- All tools resolve correctly against real database

### M10-11: Build news content sanitization layer
`packages/midas-debate/src/midas_debate/tools/sanitize.py`
- Sanitize Perplexity responses BEFORE they reach the debate agent tools
- Strip HTML/script tags, control characters, prompt injection patterns
- Detect and log potential injection attempts (e.g., "ignore previous instructions")
- News tool returns structured data (title, summary, date, source) not raw prose
- This is defense-in-depth: even if midas-data ingestion sanitizes (M01-06), tools sanitize again on read

### M10-10: Wire grounding assertions to CI
- `.github/workflows/grounding-assertions.yml`
- Run 10 sample conversations against the agent
- Assert: zero ungrounded_claims in any response
- Assert: all cited IDs resolve
- Failure = release blocker
