"""
Debate API handler — routes to DebateAgent (M07-06).

POST /debate/message — send user message, receive grounded AI response.
GET /debate/history — conversation history for user.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DebateHandlers:
    """Routes debate requests to the Kaizen DebateAgent."""

    def __init__(self, conn: Any, debate_agent: Any | None = None):
        self._conn = conn
        self._agent = debate_agent

    async def send_message(self, user_id: int, message: str) -> dict:
        """POST /debate/message — send message, receive AI response."""
        logger.info("debate.message.start", user_id=user_id, msg_len=len(message))

        # Store user message in debate history
        await self._conn.execute(
            """INSERT INTO users.debate_messages (user_id, role, content, model_portfolio_id)
               VALUES ($1, 'user', $2, $3)""",
            user_id, message, "growth",
        )

        # Load conversation history for context
        history_rows = await self._conn.fetch(
            """SELECT role, content FROM users.debate_messages
               WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20""",
            user_id,
        )
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(history_rows)]

        # Route to debate agent (wired: M10 → M07)
        if self._agent:
            from midas_debate.agent.signature import DebateInput
            debate_input = DebateInput(
                user_message=message,
                conversation_history=history[:-1],  # Exclude current msg (already in input)
                model_portfolio_id="growth",
            )
            debate_output = await self._agent.run(debate_input)

            if debate_output.ungrounded_claims:
                logger.warning(
                    "debate.ungrounded_response",
                    user_id=user_id,
                    claims=debate_output.ungrounded_claims,
                )

            response = {
                "content": debate_output.response,
                "citations": [
                    {"type": c.type, "id": c.id, "display_value": c.display_value,
                     "verified": c.verified, "external": c.external}
                    for c in debate_output.cited_ids
                ],
                "suggested_followups": debate_output.suggested_followups,
                "ungrounded_claims": debate_output.ungrounded_claims,
            }
        else:
            response = {
                "content": "Configure DEFAULT_LLM_MODEL in .env to enable the debate agent.",
                "citations": [],
                "suggested_followups": ["Set up .env with your LLM API key"],
            }

        # Store assistant response
        await self._conn.execute(
            """INSERT INTO users.debate_messages
               (user_id, role, content, citations_json, suggested_followups_json, ungrounded_claims_json, model_portfolio_id)
               VALUES ($1, 'assistant', $2, $3, $4, $5, $6)""",
            user_id,
            response.get("content", ""),
            json.dumps(response.get("citations", [])),
            json.dumps(response.get("suggested_followups", [])),
            json.dumps(response.get("ungrounded_claims", [])),
            "growth",
        )

        logger.info("debate.message.complete", user_id=user_id)
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
            "status": 200,
        }

    async def get_history(self, user_id: int, limit: int = 50) -> dict:
        """GET /debate/history — conversation history from debate_messages table."""
        rows = await self._conn.fetch(
            """SELECT id, role, content, citations_json, suggested_followups_json, created_at
               FROM users.debate_messages
               WHERE user_id = $1
               ORDER BY created_at ASC
               LIMIT $2""",
            user_id, limit,
        )

        messages = [{
            "id": str(r["id"]),
            "role": r["role"],
            "content": r["content"],
            "citations": json.loads(r["citations_json"]) if r["citations_json"] else [],
            "suggested_followups": json.loads(r["suggested_followups_json"]) if r["suggested_followups_json"] else [],
            "timestamp": r["created_at"].isoformat(),
        } for r in rows]

        return {"messages": messages, "status": 200}
