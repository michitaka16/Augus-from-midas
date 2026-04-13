"""
Append-only audit trail with mandatory chain hashing (M06-07, ADR-014).

Every record includes prev_hash (SHA-256 of previous record JSON).
Tamper detection verifies the chain on read. The midas_audit role
has INSERT + SELECT only — no UPDATE, DELETE, or TRUNCATE.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def compute_hash(payload: dict, prev_hash: str) -> str:
    """Compute SHA-256 hash for chain integrity."""
    content = json.dumps({"prev_hash": prev_hash, "payload": payload}, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


class AuditTrail:
    """Append-only audit trail with chain hashing."""

    def __init__(self, conn: Any):
        self._conn = conn

    async def append(
        self,
        event_type: str,
        payload: dict,
        actor: str = "system",
    ) -> int:
        """Append an audit record. Returns the record ID.

        Chain hashing: fetches the previous record's hash and includes
        it in the new record. This creates a tamper-evident chain.
        """
        prev = await self._conn.fetchrow(
            "SELECT hash FROM audit_trail ORDER BY id DESC LIMIT 1"
        )
        prev_hash = prev["hash"] if prev else "0" * 64

        record_hash = compute_hash(payload, prev_hash)

        record_id = await self._conn.fetchval(
            """INSERT INTO audit_trail (prev_hash, timestamp, event_type, payload_json, actor, hash)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING id""",
            prev_hash,
            datetime.utcnow(),
            event_type,
            json.dumps(payload, default=str),
            actor,
            record_hash,
        )

        logger.info(
            "audit.appended",
            event_type=event_type,
            record_id=record_id,
            actor=actor,
        )
        return record_id

    async def verify_chain(self, n_records: int = 100) -> tuple[bool, list[int]]:
        """Verify the hash chain for the most recent N records.

        Returns (is_valid, list_of_broken_record_ids).
        """
        rows = await self._conn.fetch(
            """SELECT id, prev_hash, hash, payload_json
               FROM audit_trail
               ORDER BY id DESC
               LIMIT $1""",
            n_records,
        )

        if not rows:
            return True, []

        broken = []
        rows = list(reversed(rows))  # Oldest first

        for i, row in enumerate(rows):
            payload = json.loads(row["payload_json"])
            expected_hash = compute_hash(payload, row["prev_hash"])

            if expected_hash != row["hash"]:
                broken.append(row["id"])
                logger.warning(
                    "audit.chain_broken",
                    record_id=row["id"],
                    expected=expected_hash[:16],
                    actual=row["hash"][:16],
                )

            # Verify chain linkage (prev_hash of current = hash of previous)
            if i > 0:
                prev_row = rows[i - 1]
                if row["prev_hash"] != prev_row["hash"]:
                    broken.append(row["id"])
                    logger.warning(
                        "audit.chain_link_broken",
                        record_id=row["id"],
                        expected_prev=prev_row["hash"][:16],
                        actual_prev=row["prev_hash"][:16],
                    )

        is_valid = len(broken) == 0
        if is_valid:
            logger.info("audit.chain_verified", n_records=len(rows))
        else:
            logger.warning("audit.chain_invalid", broken_count=len(broken))

        return is_valid, broken

    async def get_recent(self, limit: int = 50, event_type: str | None = None) -> list[dict]:
        """Fetch recent audit records, optionally filtered by event type."""
        if event_type:
            rows = await self._conn.fetch(
                """SELECT id, timestamp, event_type, payload_json, actor
                   FROM audit_trail
                   WHERE event_type = $1
                   ORDER BY timestamp DESC LIMIT $2""",
                event_type, limit,
            )
        else:
            rows = await self._conn.fetch(
                """SELECT id, timestamp, event_type, payload_json, actor
                   FROM audit_trail
                   ORDER BY timestamp DESC LIMIT $1""",
                limit,
            )

        return [{
            "id": row["id"],
            "timestamp": row["timestamp"].isoformat(),
            "event_type": row["event_type"],
            "payload": json.loads(row["payload_json"]),
            "actor": row["actor"],
        } for row in rows]
