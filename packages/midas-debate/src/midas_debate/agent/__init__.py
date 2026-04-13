"""Debate agent — LLM-first, zero deterministic routing."""
from midas_debate.agent.debate import DebateAgent
from midas_debate.agent.signature import DebateInput, DebateOutput, CitationRef, DEBATE_SYSTEM_PROMPT
__all__ = ["DebateAgent", "DebateInput", "DebateOutput", "CitationRef", "DEBATE_SYSTEM_PROMPT"]
