"""Session host paths: layout Docker sotto REPOS_ROOT e dati persistenti sotto DATA_ROOT."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.core.sandbox.session_paths import (
    docker_sessions_root,
    session_data_root,
    session_logs_dir,
    session_op_root,
    session_outputs_path,
    session_status_file,
    session_workspace_path,
    validate_session_id,
)

_VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


def test_session_paths_layout() -> None:
    sid = _VALID_UUID
    expected_docker = Path("/src/autonode_docker") / sid
    assert session_op_root(sid) == str(expected_docker.resolve())
    assert session_workspace_path(sid) == str((expected_docker / "workspace").resolve())
    assert session_outputs_path(sid) == str((expected_docker / "outputs").resolve())
    assert session_data_root(sid) == str((Path("/data") / sid).resolve())
    assert session_logs_dir(sid) == str((Path("/data") / sid / "logs").resolve())
    assert session_status_file(sid) == str((Path("/data") / sid / "status.json").resolve())
    assert docker_sessions_root() == str(Path("/src/autonode_docker").resolve())


def test_validate_session_id_rejects_non_uuid_v4() -> None:
    with pytest.raises(ValueError, match="UUID"):
        validate_session_id("sid-1")


def test_session_root_rejects_invalid_id() -> None:
    with pytest.raises(ValueError, match="UUID"):
        session_op_root("not-uuid")
