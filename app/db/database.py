from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("app/db/owners.db")
MIGRATIONS_DIR = Path("app/db/migrations")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY)"
        )


def run_migrations() -> None:
    initialize_db()
    with get_connection() as conn:
        applied = {
            row["id"] for row in conn.execute("SELECT id FROM schema_migrations")
        }
        migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for migration in migrations:
            if migration.name in applied:
                continue
            conn.executescript(migration.read_text())
            conn.execute(
                "INSERT INTO schema_migrations (id) VALUES (?)", (migration.name,)
            )
        conn.commit()
