"""
Risoluzione del repository Git sotto ``REPOS_ROOT`` (sicurezza path).
"""

from __future__ import annotations

from pathlib import Path

import autonode.core.sandbox.session_paths as session_paths


def ensure_git_repo_under_root(repo_path: str) -> Path:
    """
    Risolve un percorso di repository Git sotto ``REPOS_ROOT``.

    Accetta path relativi a ``REPOS_ROOT`` o assoluti già sotto quella radice.
    Rifiuta percorsi che risolvono fuori da ``REPOS_ROOT`` (inclusi ``..``).
    """
    root = Path(session_paths.REPOS_ROOT).resolve()
    raw = (repo_path or ".").strip() or "."
    candidate_in = Path(raw)
    if candidate_in.is_absolute():
        resolved = candidate_in.resolve()
    else:
        resolved = (root / candidate_in).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as e:
        msg = f"repo_path outside of REPOS_ROOT ({root}): {resolved}"
        raise ValueError(msg) from e
    if not (resolved / ".git").exists():
        msg = f"The path {resolved} is not a Git repository."
        raise ValueError(msg)
    return resolved
