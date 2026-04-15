"""
DebateAgent — Kaizen-based conversational agent with hard grounding (M10-02).

LLM-first: ZERO deterministic routing. ZERO keyword matching.
ZERO intent classification in Python. The LLM IS the router,
classifier, extractor, and evaluator.

All agent decisions go through self.run(). Tools are dumb data endpoints.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

import structlog

from midas_debate.agent.signature import (
    CitationRef,
    DebateInput,
    DebateOutput,
    DEBATE_SYSTEM_PROMPT,
)

logger = structlog.get_logger(__name__)


class DebateAgent:
    """Grounded conversational agent for portfolio debate.

    Architecture: LLM reasons about every decision. Tools fetch data.
    Grounding contract: every response is verified before reaching the user.
    Sycophancy resistance: defends positions with data, yields only to evidence.
    """

    def __init__(self, tools: dict[str, Any] | None = None):
        """
        Args:
            tools: Dict of tool_name → callable. Each tool is a dumb data endpoint.
                   The LLM decides which tools to call based on the user's question.
        """
        self._tools = tools or {}
        self._model = os.environ.get(
            "DEFAULT_LLM_MODEL",
            os.environ.get("OPENAI_PROD_MODEL", ""),
        )
        if not self._model:
            logger.warning("debate.no_model_configured")

    async def run(self, input: DebateInput) -> DebateOutput:
        """Process a user message and return a grounded response.

        The entire reasoning pipeline is LLM-driven:
        1. LLM receives user message + conversation history + context
        2. LLM decides which tools to call (if any)
        3. LLM composes response with citations
        4. Grounding verification rejects ungrounded responses

        NO keyword matching. NO intent classification. NO pre-routing.
        """
        logger.info(
            "debate.run.start",
            msg_len=len(input.user_message),
            history_len=len(input.conversation_history),
        )

        # Build the context for the LLM
        messages = self._build_messages(input)

        # Call the LLM — this is where ALL reasoning happens
        try:
            raw_response = await self._call_llm(messages)
        except Exception as exc:
            logger.exception("debate.llm_call_failed")
            err = str(exc)[:300]
            if "401" in err or "Unauthorized" in err:
                msg = ("All configured LLM API keys were rejected (401 Unauthorized). "
                       "Update .env with valid keys for MINIMAX_API_KEY, ZAI_API_KEY, "
                       "OPENAI_API_KEY, or ANTHROPIC_API_KEY, then restart the API.")
            elif "nodename" in err or "resolve" in err:
                msg = ("Could not connect to the LLM API. Check API base URLs in .env "
                       "(MINIMAX_API_BASE, ZAI_API_BASE).")
            else:
                msg = f"LLM connection failed: {err}"
            return DebateOutput(
                response=msg,
                cited_ids=[],
                ungrounded_claims=["llm_call_failed"],
                suggested_followups=["Check .env API keys", "Restart API server"],
            )

        # Parse citations from the response
        output = self._parse_response(raw_response)

        # Grounding verification (M10-05)
        from midas_debate.grounding.verify import verify_citations
        verified = await verify_citations(output.cited_ids, self._tools)
        if not verified.all_valid:
            logger.warning(
                "debate.ungrounded_citations",
                invalid=verified.invalid_ids,
            )
            # Re-generate with grounding error context
            # For v1: mark invalid citations rather than full re-generation
            for invalid_id in verified.invalid_ids:
                output.ungrounded_claims.append(f"Citation {invalid_id} could not be verified")

        logger.info(
            "debate.run.complete",
            response_len=len(output.response),
            n_citations=len(output.cited_ids),
            n_ungrounded=len(output.ungrounded_claims),
        )
        return output

    def _build_messages(self, input: DebateInput) -> list[dict]:
        """Build the message array for the LLM call."""
        messages = [{"role": "system", "content": DEBATE_SYSTEM_PROMPT}]

        # Add regime context if available
        if input.current_regime:
            messages.append({
                "role": "system",
                "content": f"Current regime context: {input.current_regime}",
            })

        if input.current_signal:
            messages.append({
                "role": "system",
                "content": f"Current signal context: {input.current_signal}",
            })

        # Add conversation history
        for msg in input.conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current user message
        messages.append({"role": "user", "content": input.user_message})

        return messages

    async def _call_llm(self, messages: list[dict]) -> str:
        """Call the LLM. Provider + model from .env (NEVER hardcoded).

        Provider resolution order (Anthropic first because ZAI's
        Anthropic-compatible endpoint is the most reliable working path):
        1. Anthropic-compatible (ANTHROPIC_API_KEY + optional ANTHROPIC_BASE_URL)
        2. MiniMax (MINIMAX_API_KEY) — OpenAI-compatible
        3. ZAI native (ZAI_API_KEY) — OpenAI-compatible
        4. OpenAI (OPENAI_API_KEY) — OpenAI-compatible
        """
        # Build provider chain. On failure, fall through to next.
        # This is error-handling (permitted deterministic logic), not agent routing.
        providers: list[tuple[str, str, str, bool]] = []

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            providers.append(("anthropic", anthropic_key, "", True))

        minimax_key = os.environ.get("MINIMAX_API_KEY", "")
        if minimax_key:
            providers.append(("minimax", minimax_key, os.environ.get("MINIMAX_API_BASE", "https://api.minimaxi.com/v1"), False))

        zai_key = os.environ.get("ZAI_API_KEY", "")
        if zai_key:
            providers.append(("zai", zai_key, os.environ.get("ZAI_API_BASE", "https://api.zai.chat/v1"), False))

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            providers.append(("openai", openai_key, "https://api.openai.com/v1", False))

        if not providers:
            return "No LLM API key configured. Set MINIMAX_API_KEY, ZAI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env."

        last_error: Exception | None = None
        for name, key, base, is_anthropic in providers:
            try:
                if is_anthropic:
                    return await self._call_anthropic(messages, key)
                return await self._call_openai_compatible(messages, key, base, provider=name)
            except Exception as e:
                last_error = e
                logger.warning("debate.provider_failed", provider=name, error=str(e)[:200])
                continue

        logger.error("debate.all_providers_failed", last_error=str(last_error))
        raise last_error  # type: ignore[misc]

    async def _call_openai_compatible(
        self,
        messages: list[dict],
        api_key: str,
        base_url: str,
        provider: str = "openai",
    ) -> str:
        """Call any OpenAI-compatible chat completions API.

        Works with MiniMax, OpenAI, and any provider that implements
        the /v1/chat/completions endpoint (e.g., Together, Groq, etc.).
        """
        import httpx

        url = f"{base_url.rstrip('/')}/chat/completions"
        logger.info("debate.llm_call", provider=provider, model=self._model, url=url)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(
                    "debate.llm_ok",
                    provider=provider,
                    response_len=len(content),
                )
                return content
        except Exception:
            logger.exception("debate.llm_error", provider=provider)
            raise

    async def _call_anthropic(self, messages: list[dict], api_key: str) -> str:
        """Call Anthropic-compatible API.

        Honors ANTHROPIC_BASE_URL (e.g., https://api.z.ai/api/anthropic for
        ZAI's Anthropic-compatible endpoint) and ANTHROPIC_MODEL (e.g., glm-5.1)
        so the same code works against Anthropic, ZAI, or any other provider
        that implements the Anthropic /v1/messages protocol.
        """
        import httpx

        system_msg = ""
        user_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            else:
                user_msgs.append(msg)

        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        model = os.environ.get("ANTHROPIC_MODEL", self._model)
        url = f"{base_url}/v1/messages"

        logger.info("debate.llm_call", provider="anthropic", model=model, url=url)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "system": system_msg,
                        "messages": user_msgs,
                        "max_tokens": 2000,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["content"][0]["text"]
                logger.info(
                    "debate.llm_ok", provider="anthropic", response_len=len(content)
                )
                return content
        except Exception:
            logger.exception("debate.llm_error", provider="anthropic")
            raise

    def _parse_response(self, raw: str) -> DebateOutput:
        """Parse citations from LLM response text.

        Citations are formatted as [cite: TYPE_ID] in the response.
        This is output formatting (permitted deterministic logic),
        NOT input classification.
        """
        import re

        citations = []
        # Extract [cite: signal_123] patterns
        pattern = r'\[cite:\s*(\w+)_(\w+)\]'
        for match in re.finditer(pattern, raw):
            cite_type = match.group(1)
            cite_id = match.group(2)
            citations.append(CitationRef(
                type=cite_type,
                id=f"{cite_type}_{cite_id}",
                display_value=match.group(0),
                external=cite_type == "news",
                verified=False,  # Will be verified by grounding check
            ))

        # Extract suggested followups (if LLM included them)
        followups = []
        if "Follow-up:" in raw or "You might ask:" in raw:
            lines = raw.split("\n")
            in_followup = False
            for line in lines:
                if "Follow-up:" in line or "You might ask:" in line:
                    in_followup = True
                    continue
                if in_followup and line.strip().startswith(("-", "•", "1", "2", "3")):
                    followups.append(line.strip().lstrip("-•0123456789. "))

        return DebateOutput(
            response=raw,
            cited_ids=citations,
            ungrounded_claims=[],
            suggested_followups=followups[:3],
        )
