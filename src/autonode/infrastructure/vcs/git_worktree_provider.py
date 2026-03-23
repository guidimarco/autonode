"""
Git worktree adapter for session-scoped workspace provisioning.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from autonode.core.sandbox.models import WorkspaceBindingModel
from autonode.core.workflow.ports import VCSProviderPort


def _branch_label_for_session(session_id: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", session_id.strip()).strip("-") or "session"
    return f"autonode/session-{token[:80]}"


class GitWorktreeProvider(VCSProviderPort):
    """Provision a per-session git worktree (repository Git obbligatorio)."""

    def __init__(self, *, worktrees_root: str = ".autonode/worktrees") -> None:
        self._worktrees_root = worktrees_root

    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        repo = Path(repo_path).resolve()
        branch_name = _branch_label_for_session(session_id)

        if not (repo / ".git").exists():
            msg = (
                f"La directory {repo} non è una checkout Git (.git assente): "
                "impossibile creare un worktree isolato."
            )
            raise RuntimeError(msg)

        worktree_root = (repo / self._worktrees_root).resolve()
        worktree_root.mkdir(parents=True, exist_ok=True)
        worktree = (worktree_root / session_id).resolve()

        if worktree.exists():
            shutil.rmtree(worktree)

        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-B",
                branch_name,
                str(worktree),
                "HEAD",
            ],
            check=True,
        )

        return WorkspaceBindingModel(
            session_id=session_id,
            repo_host_path=str(repo),
            worktree_host_path=str(worktree),
            branch_name=branch_name,
        )

    def commit_and_push(self, worktree_path: str, message: str, *, push: bool = True) -> str:
        worktree = str(Path(worktree_path).resolve())
        subprocess.run(["git", "-C", worktree, "add", "-A"], check=True)

        status = subprocess.run(
            ["git", "-C", worktree, "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
        if not status.stdout.strip():
            return ""

        subprocess.run(["git", "-C", worktree, "commit", "-m", message], check=True)
        commit_hash = subprocess.run(
            ["git", "-C", worktree, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        if push:
            branch_name = subprocess.run(
                ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", worktree, "push", "-u", "origin", branch_name],
                check=True,
            )

        return commit_hash
