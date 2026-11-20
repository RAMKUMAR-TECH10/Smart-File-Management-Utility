"""SQLite connection and operation-history table management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "file_manager.db"


class Database:
    """Small SQLite wrapper used by the history manager."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self.connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.initialize()
        return self.connection

    def initialize(self) -> None:
        connection = self.connect()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                operation   TEXT NOT NULL,
                path        TEXT NOT NULL,
                destination TEXT DEFAULT '',
                status      TEXT NOT NULL,
                details     TEXT DEFAULT ''
            )
            """
        )
        connection.commit()

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        connection = self.connect()
        cursor = connection.execute(sql, parameters)
        connection.commit()
        return cursor

    def query(self, sql: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        return list(self.connect().execute(sql, parameters).fetchall())

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
