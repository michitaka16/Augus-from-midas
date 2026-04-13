"""Tier 1 tests for audit trail chain hashing (M06-07)."""

import pytest

from midas_governance.audit import compute_hash


class TestChainHashing:
    @pytest.mark.unit
    def test_hash_deterministic(self):
        payload = {"event": "signal_published", "signal_id": 42}
        prev_hash = "0" * 64
        h1 = compute_hash(payload, prev_hash)
        h2 = compute_hash(payload, prev_hash)
        assert h1 == h2

    @pytest.mark.unit
    def test_different_payload_different_hash(self):
        prev_hash = "0" * 64
        h1 = compute_hash({"event": "a"}, prev_hash)
        h2 = compute_hash({"event": "b"}, prev_hash)
        assert h1 != h2

    @pytest.mark.unit
    def test_different_prev_hash_different_hash(self):
        payload = {"event": "test"}
        h1 = compute_hash(payload, "a" * 64)
        h2 = compute_hash(payload, "b" * 64)
        assert h1 != h2

    @pytest.mark.unit
    def test_hash_is_sha256_hex(self):
        h = compute_hash({"x": 1}, "0" * 64)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    @pytest.mark.unit
    def test_chain_integrity(self):
        """Simulate a 3-record chain and verify linkage."""
        h0 = "0" * 64
        p1 = {"event": "first"}
        h1 = compute_hash(p1, h0)

        p2 = {"event": "second"}
        h2 = compute_hash(p2, h1)

        p3 = {"event": "third"}
        h3 = compute_hash(p3, h2)

        # Verify chain: h3 depends on h2 which depends on h1
        assert h3 != h2 != h1
        # Tamper with record 2: recompute h2 with different payload
        h2_tampered = compute_hash({"event": "TAMPERED"}, h1)
        assert h2_tampered != h2
        # h3 no longer valid because it was computed with original h2
        h3_from_tampered = compute_hash(p3, h2_tampered)
        assert h3_from_tampered != h3


class TestEnvelopeSQL:
    @pytest.mark.unit
    def test_publisher_generates_sql(self):
        from midas_governance.envelopes import PUBLISHER, generate_grant_sql
        sql = generate_grant_sql(PUBLISHER)
        assert any("GRANT" in s for s in sql)
        assert any("midas_publisher" in s for s in sql)
        # Publisher must NOT have grants on users schema
        assert not any("users" in s.lower() and "GRANT" in s for s in sql)

    @pytest.mark.unit
    def test_audit_no_delete_grants(self):
        from midas_governance.envelopes import AUDIT, generate_grant_sql
        sql = generate_grant_sql(AUDIT)
        combined = " ".join(sql).upper()
        assert "DELETE" not in combined
        assert "UPDATE" not in combined
        assert "TRUNCATE" not in combined
        assert "INSERT" in combined
        assert "SELECT" in combined

    @pytest.mark.unit
    def test_all_envelopes_have_role_names(self):
        from midas_governance.envelopes import ALL_ENVELOPES
        roles = {e.role_name for e in ALL_ENVELOPES}
        assert roles == {"midas_publisher", "midas_subscriber", "midas_broker", "midas_audit"}

    @pytest.mark.unit
    def test_publisher_denied_schemas(self):
        from midas_governance.envelopes import PUBLISHER
        assert "users" in PUBLISHER.denied_schemas
        assert "tokens" in PUBLISHER.denied_schemas
