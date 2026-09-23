"""
db.py

SQLite connection management for the URL Shortener prototype.

The single source of truth for table structure is artifacts/schema.sql at
the repository root (produced by TASK-004) — this module does not
duplicate schema definitions, it only executes that file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def default_db_path() -> str:
    """Default on-disk location for the prototype database."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "url_shortener.db")


def _schema_path() -> Path:
    # generated/url_shortener/app/db.py -> repo_root/artifacts/schema.sql
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "artifacts" / "schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Apply artifacts/schema.sql (idempotent: uses IF NOT EXISTS everywhere)."""
    schema_sql = _schema_path().read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()

