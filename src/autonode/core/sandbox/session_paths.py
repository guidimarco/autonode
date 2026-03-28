"""
Percorsi host deterministici per sessione: ``../autonode_sessions/{session_id}/``.

``repo_host_path`` è la root del repository Git (directory che contiene ``.git``).
La directory sessione è ``(repo.parent / "autonode_sessions" / session_id).resolve()``.
"""

from __future__ import annotations

from pathlib import Path


def session_root_host(repo_host_path: str, session_id: str) -> str:
    """Directory radice della sessione sul host (contiene ``workspace`` e ``outputs``)."""
    repo = Path(repo_host_path).resolve()
    # Immagine Docker compose: repo in ``/app``, volume ``../autonode_sessions:/autonode_sessions``.
    if str(repo) == "/app":
        return str((Path("/autonode_sessions") / session_id).resolve())
    return str((repo.parent / "autonode_sessions" / session_id).resolve())


def worktree_host(repo_host_path: str, session_id: str) -> str:
    """Directory Git worktree sul host (montata come ``/workspace`` nel container)."""
    return str(Path(session_root_host(repo_host_path, session_id)) / "workspace")


def outputs_host(repo_host_path: str, session_id: str) -> str:
    """Directory output sessione sul host (montata come ``/outputs`` nel container)."""
    return str(Path(session_root_host(repo_host_path, session_id)) / "outputs")
