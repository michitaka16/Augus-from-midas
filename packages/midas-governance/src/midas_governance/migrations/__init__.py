"""
Database migration runner for Midas platform.

Applies numbered SQL migrations from this directory in order.
Tracks applied migrations in a `_migrations` table.
Idempotent: running twice is a no-op.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


def get_migration_files() -> list[Path]:
    """Return migration SQL files sorted by number."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


async def apply_migrations(database_url: str | None = None) -> int:
    """Apply all pending migrations. Returns count of newly applied migrations.

    Uses raw asyncpg connection (not DataFlow) because migrations must run
    before DataFlow models are registered.
    """
    try:
        import asyncpg
    except ImportError as exc:
        raise ImportError(
            "asyncpg is required for PostgreSQL migrations. "
            "Install it with: pip install asyncpg"
        ) from exc

    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL must be set in .env or passed as argument")

    conn = await asyncpg.connect(url)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        applied = {row["filename"] for row in await conn.fetch("SELECT filename FROM _migrations")}

        count = 0
        for migration_file in get_migration_files():
            filename = migration_file.name
            if filename in applied:
                logger.debug("migration.skipped", filename=filename)
                continue

            logger.info("migration.applying", filename=filename)
            sql = migration_file.read_text()

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO _migrations (filename) VALUES ($1)", filename
                )

            logger.info("migration.applied", filename=filename)
            count += 1

        if count == 0:
            logger.info("migrations.up_to_date")
        else:
            logger.info("migrations.complete", applied_count=count)

        return count
    finally:
        await conn.close()


async def rollback_last(database_url: str | None = None) -> str | None:
    """Rollback the most recently applied migration. Returns filename or None."""
    try:
        import asyncpg
    except ImportError as exc:
        raise ImportError("asyncpg required for rollback") from exc

    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL must be set")

    conn = await asyncpg.connect(url)
    try:
        row = await conn.fetchrow(
            "SELECT filename FROM _migrations ORDER BY applied_at DESC LIMIT 1"
        )
        if not row:
            logger.info("rollback.nothing_to_rollback")
            return None

        filename = row["filename"]
        logger.warning("rollback.removing", filename=filename)

        async with conn.transaction():
            await conn.execute("DELETE FROM _migrations WHERE filename = $1", filename)

        logger.info("rollback.complete", filename=filename)
        return filename
    finally:
        await conn.close()
