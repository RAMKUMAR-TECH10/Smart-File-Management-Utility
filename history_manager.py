"""Audit trail of completed file operations (not an undo system)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from database import Database
from logger import get_logger

LOG = get_logger()


class HistoryManager:
    def __init__(self, db_path: str | Path | None = None, database: Database | None = None) -> None:
        self.database = database or Database(db_path)

    def record(
        self,
        operation: str,
        path: str | Path,
        status: str = "Success",
        destination: str | Path = "",
        details: str = "",
    ) -> bool:
        try:
            self.database.execute(
                "INSERT INTO operations (timestamp, operation, path, destination, status, details) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(operation),
                    str(path),
                    str(destination),
                    str(status),
                    str(details),
                ),
            )
            return True
        except Exception as error:  # database errors must not crash file operations
            LOG.error("Could not write operation history: %s", error)
            return False

    def get_all(self, limit: int | None = None) -> list[dict]:
        sql = "SELECT * FROM operations ORDER BY id DESC"
        parameters: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            parameters = (int(limit),)
        try:
            return [dict(row) for row in self.database.query(sql, parameters)]
        except Exception as error:
            LOG.error("Could not read operation history: %s", error)
            return []

    def search(self, keyword: str) -> list[dict]:
        pattern = f"%{keyword}%"
        try:
            rows = self.database.query(
                "SELECT * FROM operations WHERE operation LIKE ? OR path LIKE ? OR destination LIKE ? "
                "ORDER BY id DESC",
                (pattern, pattern, pattern),
            )
            return [dict(row) for row in rows]
        except Exception as error:
            LOG.error("Could not search operation history: %s", error)
            return []

    def clear(self) -> bool:
        try:
            self.database.execute("DELETE FROM operations")
            return True
        except Exception as error:
            LOG.error("Could not clear operation history: %s", error)
            return False

    def close(self) -> None:
        self.database.close()
