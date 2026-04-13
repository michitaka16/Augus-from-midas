"""
Audit trail model — append-only with mandatory chain hashing (ADR-014).

The midas_audit Postgres role has INSERT + SELECT only.
No UPDATE, no DELETE, no TRUNCATE.

Every record includes prev_hash (SHA-256 of previous record JSON).
Tamper detection verifies the chain on read.
Daily export to S3 versioned bucket provides external immutability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AuditTrail:
    """Immutable audit trail entry with chain hashing.

    TimescaleDB hypertable for efficient time-range queries.
    """

    id: int = field(default=0, metadata={"primary_key": True})
    prev_hash: str = field(default="", metadata={"max_length": 64})
    timestamp: datetime = field(default_factory=datetime.utcnow, metadata={"index": True})
    event_type: str = field(default="", metadata={"max_length": 50, "index": True})
    payload_json: str = field(default="{}")
    actor: str = field(default="system", metadata={"max_length": 100})
    hash: str = field(default="", metadata={"max_length": 64})
