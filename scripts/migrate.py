#!/usr/bin/env python3
"""
Midas database migration CLI.

Usage:
    uv run python scripts/migrate.py migrate    # Apply all pending migrations
    uv run python scripts/migrate.py rollback   # Rollback last migration
    uv run python scripts/migrate.py status      # Show applied migrations
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add package src directories to path (workaround for editable installs on Python 3.14+)
_root = Path(__file__).parent.parent
for pkg_dir in (_root / "packages").iterdir():
    src = pkg_dir / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))
for app_dir in (_root / "apps").iterdir():
    src = app_dir / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv(_root / ".env")


async def cmd_migrate():
    from midas_governance.migrations import apply_migrations
    count = await apply_migrations()
    print(f"Applied {count} migration(s).")


async def cmd_rollback():
    from midas_governance.migrations import rollback_last
    filename = await rollback_last()
    if filename:
        print(f"Rolled back: {filename}")
    else:
        print("Nothing to rollback.")


async def cmd_status():
    try:
        import asyncpg
    except ImportError:
        print("asyncpg required. Install with: uv pip install asyncpg")
        sys.exit(1)

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set in .env")
        sys.exit(1)

    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(
            "SELECT filename, applied_at FROM _migrations ORDER BY applied_at"
        )
        if not rows:
            print("No migrations applied yet.")
        else:
            print(f"{'Filename':<50} {'Applied At'}")
            print("-" * 80)
            for row in rows:
                print(f"{row['filename']:<50} {row['applied_at']}")
    except Exception:
        print("Migration table does not exist yet. Run 'migrate' first.")
    finally:
        await conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    commands = {
        "migrate": cmd_migrate,
        "rollback": cmd_rollback,
        "status": cmd_status,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands)}")
        sys.exit(1)

    asyncio.run(commands[command]())


if __name__ == "__main__":
    main()
