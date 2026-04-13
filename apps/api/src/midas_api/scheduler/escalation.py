"""
Turbulent regime escalation protocol (M04-05a + M04-05b).

State machine: NOTIFIED → REMINDED → AUTO_DEFENSIVE | USER_DECIDED
Timer: T+0h notify → T+12h remind → T+24h auto-defensive (configurable 12h–72h).

The user confirmed a 24h default (shorter is preferred — feedback_shorter_defaults.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class EscalationState(str, Enum):
    NOTIFIED = "notified"
    REMINDED = "reminded"
    AUTO_DEFENSIVE = "auto_defensive"
    USER_DECIDED = "user_decided"
    CLEARED = "cleared"


@dataclass
class EscalationRecord:
    user_id: int
    signal_id: int | None
    state: EscalationState
    notified_at: datetime
    reminded_at: datetime | None
    decided_at: datetime | None
    timeout_hours: int
    auto_defensive: bool


class EscalationStateMachine:
    """Pure logic — no external dependencies. Testable in isolation."""

    def __init__(self, timeout_hours: int = 24):
        self.timeout_hours = max(12, min(72, timeout_hours))
        self.reminder_hours = self.timeout_hours // 2

    def compute_state(self, record: EscalationRecord, now: datetime) -> EscalationState:
        """Determine the current escalation state based on time elapsed."""
        if record.state == EscalationState.USER_DECIDED:
            return EscalationState.USER_DECIDED
        if record.state == EscalationState.CLEARED:
            return EscalationState.CLEARED

        elapsed = now - record.notified_at

        if elapsed >= timedelta(hours=self.timeout_hours):
            return EscalationState.AUTO_DEFENSIVE
        elif elapsed >= timedelta(hours=self.reminder_hours):
            return EscalationState.REMINDED
        else:
            return EscalationState.NOTIFIED

    def should_send_reminder(self, record: EscalationRecord, now: datetime) -> bool:
        """Check if a reminder should be sent."""
        if record.reminded_at is not None:
            return False  # Already reminded
        elapsed = now - record.notified_at
        return elapsed >= timedelta(hours=self.reminder_hours)

    def should_auto_defend(self, record: EscalationRecord, now: datetime) -> bool:
        """Check if auto-defensive action should execute."""
        if record.state in (EscalationState.USER_DECIDED, EscalationState.CLEARED):
            return False
        elapsed = now - record.notified_at
        return elapsed >= timedelta(hours=self.timeout_hours)

    def user_decides(self, record: EscalationRecord, decision: str) -> EscalationRecord:
        """User makes a decision: 'approve', 'reject', 'hold'."""
        return EscalationRecord(
            user_id=record.user_id,
            signal_id=record.signal_id,
            state=EscalationState.USER_DECIDED,
            notified_at=record.notified_at,
            reminded_at=record.reminded_at,
            decided_at=datetime.utcnow(),
            timeout_hours=record.timeout_hours,
            auto_defensive=False,
        )


class EscalationManager:
    """Wires the state machine to notifications, audit, and approvals (M04-05b)."""

    def __init__(self, conn: Any, state_machine: EscalationStateMachine | None = None):
        self._conn = conn
        self._sm = state_machine or EscalationStateMachine()

    async def initiate(self, user_id: int, regime_state: Any) -> EscalationRecord:
        """Start escalation for a user when regime flips to turbulent."""
        now = datetime.utcnow()
        timeout = await self._get_user_timeout(user_id)
        self._sm = EscalationStateMachine(timeout_hours=timeout)

        record = EscalationRecord(
            user_id=user_id,
            signal_id=None,
            state=EscalationState.NOTIFIED,
            notified_at=now,
            reminded_at=None,
            decided_at=None,
            timeout_hours=timeout,
            auto_defensive=False,
        )

        logger.info(
            "escalation.initiated",
            user_id=user_id,
            timeout_hours=timeout,
        )
        return record

    async def tick(self, record: EscalationRecord) -> EscalationRecord:
        """Advance the escalation based on current time. Call periodically."""
        now = datetime.utcnow()
        new_state = self._sm.compute_state(record, now)

        if new_state == record.state:
            return record  # No change

        if new_state == EscalationState.REMINDED and self._sm.should_send_reminder(record, now):
            logger.info("escalation.reminder", user_id=record.user_id)
            record = EscalationRecord(
                user_id=record.user_id,
                signal_id=record.signal_id,
                state=EscalationState.REMINDED,
                notified_at=record.notified_at,
                reminded_at=now,
                decided_at=None,
                timeout_hours=record.timeout_hours,
                auto_defensive=False,
            )
            # TODO: Wire to push notification service (M07-08)

        elif new_state == EscalationState.AUTO_DEFENSIVE:
            logger.warning("escalation.auto_defensive", user_id=record.user_id)
            record = EscalationRecord(
                user_id=record.user_id,
                signal_id=record.signal_id,
                state=EscalationState.AUTO_DEFENSIVE,
                notified_at=record.notified_at,
                reminded_at=record.reminded_at,
                decided_at=now,
                timeout_hours=record.timeout_hours,
                auto_defensive=True,
            )
            # Generate defensive signal
            await self._execute_defensive(record)

        return record

    async def _get_user_timeout(self, user_id: int) -> int:
        """Get the user's configured timeout from preferences."""
        row = await self._conn.fetchrow(
            "SELECT timeout_hours FROM users.preferences WHERE user_id = $1",
            user_id,
        )
        return row["timeout_hours"] if row else 24

    async def _execute_defensive(self, record: EscalationRecord) -> None:
        """Execute the auto-defensive action (move to cash + short bonds).

        This generates and publishes a defensive signal for the user's portfolio.
        The defensive action is always the CONSERVATIVE move.
        """
        logger.warning(
            "escalation.defensive_executed",
            user_id=record.user_id,
            reason="timeout",
        )
        # Write to audit trail
        # In the wired version, this calls the signal workflow with regime=turbulent
        # and publishes a defensive allocation
