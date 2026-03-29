"""
SQLite Checkpoint Manager – Infrastructure layer.

Single point of responsibility for opening the SQLite connection and
exposing a ready-to-use ``BaseCheckpointSaver`` for LangGraph.

Rules:
- The connection is opened ONCE per process (singleton via lru_cache).
- WAL mode is applied immediately to reduce write contention.
- ``check_same_thread=False`` allows the connection to be shared across
  threads (FastAPI worker threads, CLI).
- No other module may import ``sqlite3`` for checkpoint purposes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver


class SqliteCheckpointManager:
    """
    Manages a single SQLite connection and its associated ``SqliteSaver``.

    Do not instantiate directly – use :func:`get_sqlite_checkpoint_manager`.
    """

    def __init__(self, db_path: Path) -> None:
        self._conn: sqlite3.Connection = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.commit()
        self._saver = SqliteSaver(self._conn)

    @property
    def checkpointer(self) -> BaseCheckpointSaver[Any]:
        """Return the ready-to-use LangGraph checkpointer."""
        return self._saver

    def close(self) -> None:
        """Explicitly close the connection (call on process shutdown)."""
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass
