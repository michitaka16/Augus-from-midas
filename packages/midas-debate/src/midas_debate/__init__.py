"""Midas Debate Agent — grounded conversational AI for portfolio debate."""
from midas_debate.agent.debate import DebateAgent
from midas_debate.agent.signature import DebateInput, DebateOutput, CitationRef
from midas_debate.tools.data_tools import DebateTools
from midas_debate.grounding.verify import verify_citations
from midas_debate.scenarios.counter import compute_counter_scenario, CounterResult
__all__ = ["DebateAgent", "DebateInput", "DebateOutput", "CitationRef", "DebateTools", "verify_citations", "compute_counter_scenario", "CounterResult"]
