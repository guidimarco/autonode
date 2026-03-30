"""
Percorsi sessione: dati operativi (Docker) sotto ``REPOS_ROOT`` e dati persistenti sotto
``DATA_ROOT`` (log/stato), senza mount del data root verso la sandbox.
"""

from __future__ import annotations

import re
from pathlib import Path

REPOS_ROOT = "/src"
# ^ ^ ^ Container root: mount ``..`` → ``/src``
DATA_ROOT = "/data"
# ^ ^ ^ Root data session (log, status.json); on the host typically ``.../autonode_data``.

_DOCKER_DIR_NAME = "autonode_docker"

_UUID4_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
)


def validate_session_id(session_id: str) -> str:
    """Validate that ``session_id`` is a valid UUID v4; return the normalized string."""
    s = session_id.strip()
    if not _UUID4_PATTERN.fullmatch(s):
        msg = "session_id must be a valid UUID v4"
        raise ValueError(msg)
    return s


def docker_sessions_root() -> str:
    """Directory that contains the session Docker folders: ``{REPOS_ROOT}/autonode_docker``."""
    return str((Path(REPOS_ROOT) / _DOCKER_DIR_NAME).resolve())


def session_op_root(session_id: str) -> str:
    """
    Root operational data of the session (worktree, outputs) under
    `{REPOS_ROOT}/autonode_docker/{session_id}/`.
    """
    sid = validate_session_id(session_id)
    return str((Path(REPOS_ROOT) / _DOCKER_DIR_NAME / sid).resolve())


def session_workspace_path(session_id: str) -> str:
    """Directory Git worktree (mount ``/workspace`` nella sandbox)."""
    return str(Path(session_op_root(session_id)) / "workspace")


def session_outputs_path(session_id: str) -> str:
    """Directory output session (mount ``/outputs`` in the sandbox)."""
    return str(Path(session_op_root(session_id)) / "outputs")


def session_data_root(session_id: str) -> str:
    """Root persistent data of the session: ``{DATA_ROOT}/{session_id}/``."""
    sid = validate_session_id(session_id)
    return str((Path(DATA_ROOT) / sid).resolve())


def session_log_file(session_id: str) -> str:
    """
    Session log path: ``{DATA_ROOT}/{session_id}/session.log`` (session root; no ``logs/`` folder).
    """
    return str(Path(session_data_root(session_id)) / "session.log")


def session_status_file(session_id: str) -> str:
    """File status machine: ``{DATA_ROOT}/{session_id}/status.json``."""
    return str(Path(session_data_root(session_id)) / "status.json")
