"""Tier 1 tests for the turbulent escalation state machine (M04-05a)."""

from datetime import datetime, timedelta

import pytest

from midas_api.scheduler.escalation import (
    EscalationStateMachine,
    EscalationRecord,
    EscalationState,
)


def _make_record(hours_ago: float = 0, state: EscalationState = EscalationState.NOTIFIED) -> EscalationRecord:
    return EscalationRecord(
        user_id=1,
        signal_id=None,
        state=state,
        notified_at=datetime.utcnow() - timedelta(hours=hours_ago),
        reminded_at=None,
        decided_at=None,
        timeout_hours=24,
        auto_defensive=False,
    )


class TestEscalationStateMachine:
    def setup_method(self):
        self.sm = EscalationStateMachine(timeout_hours=24)

    @pytest.mark.unit
    def test_initial_state_is_notified(self):
        record = _make_record(hours_ago=0)
        state = self.sm.compute_state(record, datetime.utcnow())
        assert state == EscalationState.NOTIFIED

    @pytest.mark.unit
    def test_reminder_after_12h(self):
        record = _make_record(hours_ago=13)
        state = self.sm.compute_state(record, datetime.utcnow())
        assert state == EscalationState.REMINDED

    @pytest.mark.unit
    def test_auto_defensive_after_24h(self):
        record = _make_record(hours_ago=25)
        state = self.sm.compute_state(record, datetime.utcnow())
        assert state == EscalationState.AUTO_DEFENSIVE

    @pytest.mark.unit
    def test_user_decided_stays(self):
        record = _make_record(hours_ago=25, state=EscalationState.USER_DECIDED)
        state = self.sm.compute_state(record, datetime.utcnow())
        assert state == EscalationState.USER_DECIDED

    @pytest.mark.unit
    def test_should_send_reminder(self):
        record = _make_record(hours_ago=13)
        assert self.sm.should_send_reminder(record, datetime.utcnow()) is True

    @pytest.mark.unit
    def test_no_double_reminder(self):
        record = _make_record(hours_ago=13)
        record = EscalationRecord(
            user_id=1, signal_id=None, state=EscalationState.REMINDED,
            notified_at=record.notified_at,
            reminded_at=datetime.utcnow() - timedelta(hours=1),
            decided_at=None, timeout_hours=24, auto_defensive=False,
        )
        assert self.sm.should_send_reminder(record, datetime.utcnow()) is False

    @pytest.mark.unit
    def test_should_auto_defend_after_timeout(self):
        record = _make_record(hours_ago=25)
        assert self.sm.should_auto_defend(record, datetime.utcnow()) is True

    @pytest.mark.unit
    def test_no_auto_defend_if_user_decided(self):
        record = _make_record(hours_ago=25, state=EscalationState.USER_DECIDED)
        assert self.sm.should_auto_defend(record, datetime.utcnow()) is False

    @pytest.mark.unit
    def test_custom_timeout(self):
        sm = EscalationStateMachine(timeout_hours=12)
        record = _make_record(hours_ago=13)
        record = EscalationRecord(
            user_id=1, signal_id=None, state=EscalationState.NOTIFIED,
            notified_at=datetime.utcnow() - timedelta(hours=13),
            reminded_at=None, decided_at=None, timeout_hours=12, auto_defensive=False,
        )
        assert sm.should_auto_defend(record, datetime.utcnow()) is True

    @pytest.mark.unit
    def test_timeout_clamped_to_range(self):
        sm = EscalationStateMachine(timeout_hours=5)  # Below 12h minimum
        assert sm.timeout_hours == 12
        sm = EscalationStateMachine(timeout_hours=100)  # Above 72h max
        assert sm.timeout_hours == 72
