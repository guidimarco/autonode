"""Logger di sessione minimale per test (nessun file, NullHandler)."""

from __future__ import annotations

import logging
import uuid

from autonode.infrastructure.logging.stderr_adapter import StandardErrorAutonodeLogger


def make_test_session_logger() -> StandardErrorAutonodeLogger:
    py = logging.getLogger(f"test.session.{uuid.uuid4().hex[:12]}")
    py.handlers.clear()
    py.addHandler(logging.NullHandler())
    return StandardErrorAutonodeLogger(py)
