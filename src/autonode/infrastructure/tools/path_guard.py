"""
Path sandbox utilities: resolve roots and reject paths outside the allowed directory.

La root effettiva è sempre il worktree host della sessione (nessun fallback su altre directory).
"""

from __future__ import annotations

import shlex
from pathlib import Path

from autonode.core.sandbox.models import ExecutionEnvironmentModel


def resolved_root(root_dir: str) -> Path:
    """Return the canonical absolute path for the sandbox root."""
    return Path(root_dir).expanduser().resolve()


def resolve_under_root(sandbox_root: str, relative_path: str) -> Path:
    """
    Resolve ``relative_path`` under ``sandbox_root`` (tipicamente ``worktree_host_path``).

    Raises:
        ValueError: If ``relative_path`` resolves outside the root or is an absolute path.
    """
    root = resolved_root(sandbox_root)
    rel = (relative_path or ".").strip() or "."
    if Path(rel).is_absolute():
        msg = "path assoluto non permesso: la sandbox accetta solo path relativi alla root"
        raise ValueError(msg)

    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise ValueError(
            f"path fuori dalla sandbox: {candidate} (root: {root})",
        ) from e
    return candidate


class PathGuard:
    """Validate paths against the session worktree (host) and container root."""

    def __init__(self, execution_env: ExecutionEnvironmentModel) -> None:
        if not execution_env.worktree_host_path.strip():
            raise ValueError("PathGuard: worktree_host_path obbligatorio")
        if execution_env.sandbox_id == "host-runtime":
            raise ValueError(
                "PathGuard: solo container Docker (sandbox_id 'host-runtime' non ammesso)"
            )
        self._execution_env = execution_env
        self._host_root = resolved_root(execution_env.worktree_host_path)
        self._container_root = execution_env.container_workspace_path

    @property
    def host_root(self) -> str:
        return str(self._host_root)

    def resolve_relative_path(self, relative_path: str) -> Path:
        return resolve_under_root(str(self._host_root), relative_path)

    def validate_shell_command(self, command: str) -> None:
        tokens = shlex.split(command)
        for token in tokens:
            if ".." in token:
                raise ValueError("path traversal ('..') non permesso nella sandbox.")
            if token.startswith("/") and not token.startswith(self._container_root):
                raise ValueError(f"path assoluto non permesso: {token}")
