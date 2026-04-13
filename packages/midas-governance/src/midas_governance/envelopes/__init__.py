"""
PACT envelope definitions — publisher/subscriber/broker/audit separation.

Each envelope defines a Postgres role's access boundaries. The definitions
are the source of truth; SQL GRANTs derive from them. Boot-time assertions
verify actual grants match.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaGrant:
    schema: str
    table: str
    privileges: tuple[str, ...]


@dataclass(frozen=True)
class EnvelopeDef:
    role_name: str
    description: str
    grants: tuple[SchemaGrant, ...]
    denied_schemas: tuple[str, ...]


PUBLISHER = EnvelopeDef(
    role_name="midas_publisher",
    description="Reads market data, writes signals. NO access to user data.",
    grants=(
        SchemaGrant("public", "bars", ("SELECT",)),
        SchemaGrant("public", "fundamentals", ("SELECT",)),
        SchemaGrant("public", "corp_actions", ("SELECT",)),
        SchemaGrant("public", "etf_universe", ("SELECT",)),
        SchemaGrant("public", "regime_signals", ("SELECT", "INSERT", "UPDATE")),
        SchemaGrant("public", "model_portfolios", ("SELECT",)),
        SchemaGrant("public", "signals", ("SELECT", "INSERT", "UPDATE")),
        SchemaGrant("public", "signal_inputs", ("SELECT", "INSERT")),
        SchemaGrant("public", "backtest_runs", ("SELECT",)),
        SchemaGrant("public", "news_items", ("SELECT",)),
    ),
    denied_schemas=("users", "tokens"),
)

SUBSCRIBER = EnvelopeDef(
    role_name="midas_subscriber",
    description="Reads signals, manages user preferences and approvals.",
    grants=(
        SchemaGrant("public", "signals", ("SELECT",)),
        SchemaGrant("public", "model_portfolios", ("SELECT",)),
        SchemaGrant("public", "backtest_runs", ("SELECT",)),
        SchemaGrant("public", "news_items", ("SELECT",)),
        SchemaGrant("public", "regime_signals", ("SELECT",)),
        SchemaGrant("public", "bars", ("SELECT",)),
        SchemaGrant("users", "accounts", ("SELECT", "INSERT", "UPDATE")),
        SchemaGrant("users", "preferences", ("SELECT", "INSERT", "UPDATE")),
        SchemaGrant("users", "approvals", ("SELECT", "INSERT", "UPDATE")),
    ),
    denied_schemas=("tokens",),
)

BROKER = EnvelopeDef(
    role_name="midas_broker",
    description="Manages IBKR OAuth tokens only.",
    grants=(
        SchemaGrant("tokens", "user_tokens", ("SELECT", "INSERT", "UPDATE", "DELETE")),
    ),
    denied_schemas=("users",),
)

AUDIT = EnvelopeDef(
    role_name="midas_audit",
    description="Append-only audit trail. INSERT + SELECT only.",
    grants=(
        SchemaGrant("public", "audit_trail", ("SELECT", "INSERT")),
    ),
    denied_schemas=("users", "tokens"),
)

ALL_ENVELOPES = [PUBLISHER, SUBSCRIBER, BROKER, AUDIT]


def generate_grant_sql(envelope: EnvelopeDef) -> list[str]:
    """Generate SQL GRANT statements from an envelope definition."""
    statements = []
    schemas = set(g.schema for g in envelope.grants)
    for schema in schemas:
        statements.append(f"GRANT USAGE ON SCHEMA {schema} TO {envelope.role_name};")
    for grant in envelope.grants:
        privs = ", ".join(grant.privileges)
        table = f"{grant.schema}.{grant.table}" if grant.schema != "public" else grant.table
        statements.append(f"GRANT {privs} ON {table} TO {envelope.role_name};")
    return statements
