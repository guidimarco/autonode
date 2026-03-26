"""
Git worktree adapter for session-scoped workspace provisioning.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from autonode.core.sandbox.models import WorkspaceBindingModel
from autonode.core.workflow.ports import VCSProviderPort

logger = logging.getLogger(__name__)

_SESSION_ID_MARKER_FILENAME = ".autonode_session_id"


def _branch_label_for_session(session_id: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", session_id.strip()).strip("-") or "session"
    return f"autonode/session-{token[:80]}"


class GitWorktreeProvider(VCSProviderPort):
    """Provision a per-session git worktree (repository Git obbligatorio)."""

    def __init__(self, *, worktrees_root: str = ".autonode/worktrees") -> None:
        self._worktrees_root = worktrees_root

    def _resolved_worktrees_root(self, repo: Path) -> Path:
        return (repo / self._worktrees_root).resolve()

    def _git_worktree_remove(self, repo: Path, worktree_dir: Path) -> None:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree_dir)],
            check=False,
            capture_output=True,
            text=True,
        )
        if worktree_dir.exists():
            shutil.rmtree(worktree_dir, ignore_errors=True)

    def _git_worktree_prune(self, repo: Path) -> None:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "prune"],
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _path_age_seconds(path: Path) -> float:
        st = path.stat()
        birth = getattr(st, "st_birthtime", None)
        ts = float(birth) if birth is not None else float(st.st_mtime)
        return max(0.0, time.time() - ts)

    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        repo = Path(repo_path).resolve()
        branch_name = _branch_label_for_session(session_id)
        internal_worktree_id = str(uuid.uuid4())

        if not (repo / ".git").exists():
            msg = (
                f"La directory {repo} non è una checkout Git (.git assente): "
                "impossibile creare un worktree isolato."
            )
            raise RuntimeError(msg)

        worktree_root = self._resolved_worktrees_root(repo)
        worktree_root.mkdir(parents=True, exist_ok=True)
        worktree = (worktree_root / internal_worktree_id).resolve()

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

        marker_path = worktree / _SESSION_ID_MARKER_FILENAME
        marker_path.write_text(session_id, encoding="utf-8")

        return WorkspaceBindingModel(
            session_id=session_id,
            repo_host_path=str(repo),
            worktree_host_path=str(worktree),
            branch_name=branch_name,
        )

    def commit_changes(self, worktree_path: str, message: str) -> str:
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

        return commit_hash

    def remove_session_worktree(self, repo_path: str, session_id: str) -> None:
        repo = Path(repo_path).resolve()
        root = self._resolved_worktrees_root(repo)
        if not root.exists():
            logger.info("No worktrees root dir found for session %s (%s)", session_id, root)
            self._git_worktree_prune(repo)
            return

        target_dirs: list[Path] = []
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            marker_path = child / _SESSION_ID_MARKER_FILENAME
            try:
                content = marker_path.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if content == session_id:
                target_dirs.append(child.resolve())

        if not target_dirs:
            logger.info("No worktree found for session %s under %s", session_id, root)
            self._git_worktree_prune(repo)
            return

        for worktree_dir in target_dirs:
            self._git_worktree_remove(repo, worktree_dir)
            logger.info("Worktree sessione %s rimosso: %s", session_id, worktree_dir)
        self._git_worktree_prune(repo)

    def remove_all_session_worktrees(self, repo_path: str) -> None:
        repo = Path(repo_path).resolve()
        root = self._resolved_worktrees_root(repo)
        if not root.is_dir():
            logger.info("Nessuna directory worktree sessione sotto %s", root)
            return

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            self._git_worktree_remove(repo, child)
            logger.info("Worktree sessione rimosso: %s", child)

        self._git_worktree_prune(repo)
        logger.info("Rimossi tutti i worktree sotto %s", root)

    def delete_session_branch(self, repo_path: str, session_id: str) -> None:
        repo = Path(repo_path).resolve()
        branch = _branch_label_for_session(session_id)
        result = subprocess.run(
            ["git", "-C", str(repo), "branch", "-D", branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logger.info("Branch sessione rimosso: %s", branch)
        else:
            logger.info(
                "Branch %s non eliminato (assente o già rimosso): %s",
                branch,
                (result.stderr or result.stdout or "").strip(),
            )

    def delete_all_session_branches(self, repo_path: str) -> None:
        repo = Path(repo_path).resolve()
        listed = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "for-each-ref",
                "--format=%(refname:short)",
                "refs/heads/autonode/session-*",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        names = [ln.strip() for ln in listed.stdout.splitlines() if ln.strip()]
        for branch in names:
            subprocess.run(
                ["git", "-C", str(repo), "branch", "-D", branch],
                check=False,
                capture_output=True,
                text=True,
            )
            logger.info("Branch sessione rimosso: %s", branch)
        if not names:
            logger.info("Nessun branch autonode/session-* da rimuovere in %s", repo)

    def cleanup_orphaned_worktrees(self, repo_path: str, ttl_days: int = 1) -> list[str]:
        """
        Under ``<repo>/.autonode/worktrees/``, remove directories older than ``ttl_days``.

        Uses directory birth time when available, else mtime. Each removal is attempted via
        ``git worktree remove --force`` then ``shutil.rmtree`` if needed; ends with
        ``git worktree prune`` once on ``repo_path``.
        """
        repo = Path(repo_path).resolve()
        root = self._resolved_worktrees_root(repo)
        if not root.is_dir():
            return []

        ttl_seconds = max(0, ttl_days) * 86400
        removed: list[str] = []

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if self._path_age_seconds(child) <= ttl_seconds:
                continue
            self._git_worktree_remove(repo, child)
            removed.append(str(child))

        if removed:
            self._git_worktree_prune(repo)
        return removed
