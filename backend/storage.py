"""Storage abstraction for Pharma Signal Full DSP.

Defaults to SQLite (file at FULL_DSP_DB). If DATABASE_URL points at Postgres,
the same code runs against Postgres via psycopg — so local dev stays
zero-config while production can use a managed Postgres.

The rest of the app writes plain `?`-placeholder SQL; this layer translates
placeholders and the couple of SQLite-isms (`INSERT OR IGNORE`) for Postgres.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Sequence

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))
SQLITE_PATH = os.environ.get("FULL_DSP_DB", str(Path(__file__).with_name("pharma_signal_dsp.db")))
STORAGE_BACKEND = "postgres" if IS_POSTGRES else "sqlite"

if IS_POSTGRES:  # imported lazily so SQLite installs need no psycopg
    import psycopg
    from psycopg.rows import dict_row


class Connection:
    """Thin wrapper that normalizes placeholders, row access, and commit/close."""

    def __init__(self, raw: Any, is_pg: bool) -> None:
        self.raw = raw
        self.is_pg = is_pg

    def _translate(self, sql: str) -> str:
        if not self.is_pg:
            return sql
        sql = sql.replace("?", "%s")
        if "INSERT OR IGNORE" in sql:
            sql = sql.replace("INSERT OR IGNORE", "INSERT").rstrip() + " ON CONFLICT DO NOTHING"
        return sql

    def execute(self, sql: str, params: Sequence[Any] = ()):  # noqa: ANN201
        cur = self.raw.cursor()
        cur.execute(self._translate(sql), tuple(params))
        return cur

    def executescript(self, script: str) -> None:
        for statement in (s.strip() for s in script.split(";")):
            if statement:
                self.execute(statement)

    def commit(self) -> None:
        self.raw.commit()

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.raw.commit()
            else:
                self.raw.rollback()
        finally:
            self.raw.close()


def conn() -> Connection:
    if IS_POSTGRES:
        return Connection(psycopg.connect(DATABASE_URL, row_factory=dict_row), True)
    connection = sqlite3.connect(SQLITE_PATH)
    connection.row_factory = sqlite3.Row
    return Connection(connection, False)


def dicts(rows: List[Any]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]
