"""Session logging: handler dedicati e cleanup senza LoggerFactory."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.infrastructure.logging.session_logging import (
    attach_session_logging,
    detach_session_logging,
)

_VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


def test_attach_returns_loggers_and_detach_closes_handlers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_src = tmp_path / "src"
    fake_src.mkdir()
    fake_data = tmp_path / "data"
    fake_data.mkdir()
    monkeypatch.setattr("autonode.core.sandbox.session_paths.REPOS_ROOT", str(fake_src))
    monkeypatch.setattr("autonode.core.sandbox.session_paths.DATA_ROOT", str(fake_data))

    autonode_log, py_logger = attach_session_logging(_VALID_UUID)

    log = fake_data / _VALID_UUID / "session.log"
    assert log.is_file()
    assert len(py_logger.handlers) == 2

    autonode_log.info("riga di test")
    assert "riga di test" in log.read_text(encoding="utf-8")

    detach_session_logging(py_logger)
    assert py_logger.handlers == []
