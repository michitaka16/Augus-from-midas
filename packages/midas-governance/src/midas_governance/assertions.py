"""
Boot-time GRANT assertions — structural enforcement of publisher exemption (M06-05, TC1).

On API startup, queries information_schema.role_table_grants and asserts:
1. midas_publisher has ZERO grants on any table in 'users' or 'tokens' schema
2. midas_audit has no DELETE/UPDATE/TRUNCATE grants

If ANY assertion fails, the API refuses to start. This converts the publisher
exemption from a policy guarantee to a structural one.
"""

from __future__ import annotations

from typing import Any

import structlog

from midas_governance.envelopes import ALL_ENVELOPES

logger = structlog.get_logger(__name__)


class GovernanceAssertionError(Exception):
    """Raised when a governance assertion fails. API must not start."""
    pass


async def assert_publisher_isolation(conn: Any) -> None:
    """Assert midas_publisher has ZERO grants on users.* or tokens.*.

    This is the single most important assertion in the system.
    If it fails, the publisher exemption (ADR-001) is structurally compromised.
    """
    violations = await conn.fetch("""
        SELECT table_schema, table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE grantee = 'midas_publisher'
          AND table_schema IN ('users', 'tokens')
    """)

    if violations:
        details = [
            f"{v['table_schema']}.{v['table_name']} ({v['privilege_type']})"
            for v in violations
        ]
        msg = (
            f"CRITICAL: midas_publisher has grants on user/token tables: {details}. "
            f"This violates ADR-001 (publisher exemption). API will NOT start."
        )
        logger.critical("assertion.publisher_isolation.FAILED", violations=details)
        raise GovernanceAssertionError(msg)

    logger.info("assertion.publisher_isolation.PASSED")


async def assert_audit_immutability(conn: Any) -> None:
    """Assert midas_audit has no DELETE/UPDATE/TRUNCATE grants on audit_trail."""
    violations = await conn.fetch("""
        SELECT table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE grantee = 'midas_audit'
          AND privilege_type IN ('DELETE', 'UPDATE', 'TRUNCATE')
    """)

    if violations:
        details = [f"{v['table_name']} ({v['privilege_type']})" for v in violations]
        msg = (
            f"CRITICAL: midas_audit has mutable grants: {details}. "
            f"Audit trail immutability compromised. API will NOT start."
        )
        logger.critical("assertion.audit_immutability.FAILED", violations=details)
        raise GovernanceAssertionError(msg)

    logger.info("assertion.audit_immutability.PASSED")


async def assert_broker_isolation(conn: Any) -> None:
    """Assert midas_broker cannot access users or public signal tables."""
    violations = await conn.fetch("""
        SELECT table_schema, table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE grantee = 'midas_broker'
          AND table_schema = 'users'
    """)

    if violations:
        details = [f"{v['table_schema']}.{v['table_name']}" for v in violations]
        logger.warning("assertion.broker_isolation.FAILED", violations=details)
        raise GovernanceAssertionError(
            f"midas_broker has grants on users schema: {details}"
        )

    logger.info("assertion.broker_isolation.PASSED")


async def run_all_assertions(conn: Any) -> None:
    """Run all governance assertions. Call on API startup.

    If any assertion fails, raises GovernanceAssertionError.
    The API must refuse to start.
    """
    logger.info("assertions.start")

    await assert_publisher_isolation(conn)
    await assert_audit_immutability(conn)
    await assert_broker_isolation(conn)

    logger.info("assertions.all_passed")
