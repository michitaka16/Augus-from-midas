"""
User models — auth, preferences, tokens, approvals.

CRITICAL SCHEMA SEPARATION: These tables live in a separate Postgres schema
from the signals tables. The midas_publisher role has ZERO grants on these
tables. This is the structural enforcement of ADR-001 (publisher exemption).

- Boot-time assertion: M06-05
- CI check: M06-06
- PACT envelope: M06-01 (publisher), M06-02 (subscriber)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User account. Lives in the 'users' schema, not accessible by publisher role."""

    id: int = field(default=0, metadata={"primary_key": True})
    email: str = field(default="", metadata={"max_length": 255, "unique": True})
    password_hash: str = field(default="", metadata={"max_length": 255})
    mfa_secret: Optional[str] = field(default=None, metadata={"max_length": 255})
    mfa_enabled: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class UserPreference:
    """User preferences — notification settings, portfolio choice, timeout.

    These preferences live CLIENT-SIDE of the publisher/subscriber boundary.
    The server reads them to send notifications and manage escalation, but
    they never join with the signals table.
    """

    id: int = field(default=0, metadata={"primary_key": True})
    user_id: int = field(default=0, metadata={"index": True})
    model_portfolio_id: str = field(default="growth", metadata={"max_length": 50})
    notification_settings_json: str = field(default='{"regime_change":"push","signal_published":"push","approval_pending":"push","execution_confirmed":"push"}')
    timeout_hours: int = 24
    paper_trading: bool = True


@dataclass
class UserToken:
    """IBKR OAuth tokens — encrypted at rest (ADR-013).

    access_token_enc and refresh_token_enc are BYTEA columns containing
    AES-256-GCM encrypted tokens. The encryption key comes from
    IBKR_TOKEN_ENCRYPTION_KEY env var (never stored in DB).

    This table lives in its own schema, accessible ONLY by the midas_broker
    Postgres role. Not the publisher role, not the debate agent role.
    """

    id: int = field(default=0, metadata={"primary_key": True})
    user_id: int = field(default=0, metadata={"index": True, "unique": True})
    access_token_enc: bytes = field(default=b"")
    refresh_token_enc: bytes = field(default=b"")
    expires_at: Optional[datetime] = None
    scopes: str = field(default="read_positions,preview_order,place_order", metadata={"max_length": 255})
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Approval:
    """Trade approval record — links a user's decision to a signal."""

    id: int = field(default=0, metadata={"primary_key": True})
    user_id: int = field(default=0, metadata={"index": True})
    signal_id: int = field(default=0, metadata={"index": True})
    status: str = field(default="pending", metadata={"max_length": 20})
    decided_at: Optional[datetime] = None
    method: Optional[str] = field(default=None, metadata={"max_length": 20})
    trades_json: str = field(default="[]")
    created_at: datetime = field(default_factory=datetime.utcnow)
