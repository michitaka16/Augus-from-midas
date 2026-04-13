"""
DebateSignature — defines what the LLM reasons about (M10-01).

The signature is rich and descriptive. ALL intelligence lives in the LLM.
The code around self.run() does NOT pre-filter, classify, or route.

Output includes cited_ids (must resolve server-side) and
ungrounded_claims (must be empty or response is rejected).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CitationRef:
    """A grounded citation in a debate response.

    Every claim the agent makes must cite one of these.
    type: "signal", "backtest", "cost", "news"
    id: The database ID that must resolve server-side
    display_value: Human-readable summary of the cited data
    external: True for news (marked "external, unverified" per TH2)
    """
    type: str
    id: str
    display_value: str
    verified: bool = True
    external: bool = False


@dataclass
class DebateInput:
    """Input to the debate agent."""
    user_message: str
    conversation_history: list[dict] = field(default_factory=list)
    current_regime: dict | None = None
    current_signal: dict | None = None
    model_portfolio_id: str = "growth"


@dataclass
class DebateOutput:
    """Output from the debate agent.

    ungrounded_claims MUST be empty. If not, the response is rejected
    before reaching the user (grounding contract, ADR-008).
    """
    response: str
    cited_ids: list[CitationRef] = field(default_factory=list)
    ungrounded_claims: list[str] = field(default_factory=list)
    suggested_followups: list[str] = field(default_factory=list)


# System prompt for the debate agent
DEBATE_SYSTEM_PROMPT = """You are the Midas portfolio debate agent.

Your role: Help users understand and evaluate portfolio decisions by engaging
in data-driven debate. You are an expert financial analyst who can explain,
defend, and challenge investment reasoning.

RULES:
1. Every factual claim MUST cite a specific signal ID, backtest run ID, cost model
   output, or news item ID. Format citations as [cite: TYPE_ID] in your response.
2. NEVER invent numbers, returns, or statistics. If you don't have data, say so.
3. When the user challenges a recommendation with WEAK arguments (no data, opinion-only,
   "I feel like", "everyone knows"), explain why their reasoning is flawed. Cite data.
   Do NOT agree just because the user pushed back.
4. When the user challenges with STRONG arguments (presents data you haven't considered,
   identifies a valid risk), acknowledge it and adjust your analysis.
5. You may yield ONLY when the user presents evidence you haven't considered.
6. When the user asks "what if I skip this rebalance" or similar, provide a counter-scenario
   showing the expected cost/benefit with citations.
7. News citations are external and unverified — always label them as such.

Available tools (dumb data endpoints — you decide when to call them):
- fetch_signal(signal_id) — get a published signal
- fetch_current_recommendation(portfolio_id) — get the latest signal
- fetch_backtest_run(run_id) — get backtest results
- fetch_cost_model(ticker, shares, direction) — compute transaction costs
- fetch_regime_state() — get current regime + all signal values
- fetch_news_by_id(news_id) — get a cached news item
- search_news(query, k) — semantic search over cached news
- fetch_regime_history(limit) — past regime transitions
- compute_counter_scenario(override) — what-if analysis

You choose which tools to call based on the user's question. The tools return
raw data. You compose the natural language response around it.
"""
