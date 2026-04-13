"""
Grounding verification — rejects responses with unresolvable citations (M10-05, ADR-008).

Post-generation check: every CitationRef must resolve to a real database record.
If ANY cited ID doesn't resolve → response rejected, re-generated.
If ungrounded_claims is non-empty → response rejected unconditionally.

This is the core trust mechanism. Without it, the debate agent is just a chatbot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from midas_debate.agent.signature import CitationRef

logger = structlog.get_logger(__name__)


@dataclass
class VerificationResult:
    all_valid: bool
    valid_ids: list[str] = field(default_factory=list)
    invalid_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


async def verify_citations(
    citations: list[CitationRef],
    tools: dict[str, Any],
) -> VerificationResult:
    """Verify that every citation resolves to a real record.

    For each citation type:
    - signal → call fetch_signal(id), check it returns non-None
    - backtest → call fetch_backtest_run(id), check non-None
    - cost → always valid (can be re-computed)
    - news → call fetch_news_by_id(id), check non-None; mark as "external, unverified"
    """
    if not citations:
        return VerificationResult(all_valid=True)

    valid = []
    invalid = []
    errors = []

    for cite in citations:
        try:
            is_valid = await _verify_single(cite, tools)
            if is_valid:
                cite.verified = True
                valid.append(cite.id)
            else:
                invalid.append(cite.id)
        except Exception as e:
            errors.append(f"{cite.id}: {str(e)}")
            invalid.append(cite.id)

    result = VerificationResult(
        all_valid=len(invalid) == 0 and len(errors) == 0,
        valid_ids=valid,
        invalid_ids=invalid,
        errors=errors,
    )

    if not result.all_valid:
        logger.warning(
            "grounding.verification_failed",
            valid=len(valid),
            invalid=len(invalid),
            errors=len(errors),
        )
    else:
        logger.info("grounding.verified", n_citations=len(valid))

    return result


async def _verify_single(cite: CitationRef, tools: dict[str, Any]) -> bool:
    """Verify a single citation resolves."""
    cite_type = cite.type.lower()
    cite_id = cite.id

    # Extract numeric ID from formatted IDs like "signal_42"
    numeric_id = cite_id
    if "_" in cite_id:
        parts = cite_id.split("_")
        numeric_id = parts[-1]

    try:
        numeric = int(numeric_id)
    except (ValueError, TypeError):
        return False

    if cite_type == "signal":
        fetch = tools.get("fetch_signal")
        if fetch:
            result = await fetch(numeric)
            return result is not None
        return False

    elif cite_type == "backtest":
        fetch = tools.get("fetch_backtest_run")
        if fetch:
            result = await fetch(numeric)
            return result is not None
        return False

    elif cite_type == "cost":
        # Cost citations are always valid — they can be re-computed
        return True

    elif cite_type == "news":
        fetch = tools.get("fetch_news_by_id")
        if fetch:
            result = await fetch(numeric)
            # News is external and unverified, but the ID must exist
            if result:
                cite.external = True
                cite.verified = True
                return True
        return False

    else:
        logger.warning("grounding.unknown_type", type=cite_type)
        return False
