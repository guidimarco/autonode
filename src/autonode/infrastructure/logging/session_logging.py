"""Logger di sessione: file dedicato (rotating) + stderr; nessun registry globale."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from autonode.core.sandbox.session_paths import session_log_file, validate_session_id
from autonode.infrastructure.logging.stderr_adapter import StandardErrorAutonodeLogger

_SESSION_LOGGER_PREFIX = "autonode.session."

_ROTATE_MAX_BYTES = int(os.environ.get("AUTONODE_SESSION_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
_ROTATE_BACKUP_COUNT = int(os.environ.get("AUTONODE_SESSION_LOG_BACKUP_COUNT", "3"))


class _FlushAfterEmitRotatingFileHandler(RotatingFileHandler):
    """Rotational + flush after each record (tail -f / real-time reading)."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def attach_session_logging(session_id: str) -> tuple[StandardErrorAutonodeLogger, logging.Logger]:
    """
    Create an isolated logger for the session (``session.log`` under session data root + stderr).

    Return ``(adapter AutonodeLogger, logging.Logger stdlib)`` to pass to the use case and
    to the ``DockerAdapter`` without using ``LoggerFactory`` (parallel sessions safe).
    """
    sid = validate_session_id(session_id)
    log_path = Path(session_log_file(sid))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    name = f"{_SESSION_LOGGER_PREFIX}{sid}"
    py_logger = logging.getLogger(name)
    py_logger.handlers.clear()
    py_logger.setLevel(logging.INFO)
    py_logger.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = _FlushAfterEmitRotatingFileHandler(
        log_path,
        maxBytes=_ROTATE_MAX_BYTES,
        backupCount=_ROTATE_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(stream=sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    py_logger.addHandler(fh)
    py_logger.addHandler(sh)

    return StandardErrorAutonodeLogger(py_logger), py_logger


def detach_session_logging(python_logger: logging.Logger) -> None:
    """
    Rimuove e chiude tutti gli handler del ``logging.Logger`` di sessione.

    Non modifica ``LoggerFactory`` (compatibile con più task in parallelo).
    """
    for h in list(python_logger.handlers):
        python_logger.removeHandler(h)
        try:
            h.flush()
        finally:
            h.close()
