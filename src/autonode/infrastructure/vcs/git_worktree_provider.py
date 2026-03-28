"""
Git worktree adapter for session-scoped workspace provisioning.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from pathlib import Path

from autonode.core.sandbox.models import WorkspaceBindingModel
from autonode.core.sandbox.session_paths import (
    outputs_host,
    session_root_host,
    worktree_host,
)
from autonode.core.workflow.ports import VCSProviderPort

logger = logging.getLogger(__name__)

_SESSION_ID_MARKER_FILENAME = ".autonode_session_id"


def _branch_label_for_session(session_id: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", session_id.strip()).strip("-") or "session"
    return f"autonode/session-{token[:80]}"


class GitWorktreeProvider(VCSProviderPort):
    """Provision a per-session git worktree (repository Git obbligatorio)."""

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

    def _sessions_root(self, repo: Path) -> Path:
        return (repo.parent / "autonode_sessions").resolve()

    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        repo = Path(repo_path).resolve()
        branch_name = _branch_label_for_session(session_id)

        if not (repo / ".git").exists():
            msg = (
                f"La directory {repo} non è una checkout Git (.git assente): "
                "impossibile creare un worktree isolato."
            )
            raise RuntimeError(msg)

        session_root = Path(session_root_host(str(repo), session_id))
        wt = Path(worktree_host(str(repo), session_id))
        out = Path(outputs_host(str(repo), session_id))

        session_root.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)

        if wt.exists():
            shutil.rmtree(wt)

        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-B",
                branch_name,
                str(wt),
                "HEAD",
            ],
            check=True,
        )

        marker_path = wt / _SESSION_ID_MARKER_FILENAME
        marker_path.write_text(session_id, encoding="utf-8")

        return WorkspaceBindingModel(
            session_id=session_id,
            repo_host_path=str(repo),
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
        wt = Path(worktree_host(str(repo), session_id))
        session_root = Path(session_root_host(str(repo), session_id))

        if wt.is_dir():
            self._git_worktree_remove(repo, wt)
        if session_root.exists():
            shutil.rmtree(session_root, ignore_errors=True)
            logger.info("Sessione %s rimossa: %s", session_id, session_root)
        self._git_worktree_prune(repo)

    def remove_all_session_worktrees(self, repo_path: str) -> None:
        repo = Path(repo_path).resolve()
        root = self._sessions_root(repo)
        if not root.is_dir():
            logger.info("Nessuna directory autonode_sessions sotto %s", root)
            return

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            workspace = child / "workspace"
            if workspace.is_dir():
                self._git_worktree_remove(repo, workspace)
            shutil.rmtree(child, ignore_errors=True)
            logger.info("Sessione rimossa: %s", child)

        self._git_worktree_prune(repo)
        logger.info("Rimosse tutte le sessioni sotto %s", root)

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
        Sotto ``<repo.parent>/autonode_sessions/<session_id>/``, rimuove directory sessione
        più vecchie di ``ttl_days`` (mtime/birthtime della cartella sessione).
        """
        repo = Path(repo_path).resolve()
        root = self._sessions_root(repo)
        if not root.is_dir():
            return []

        ttl_seconds = max(0, ttl_days) * 86400
        removed: list[str] = []

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if self._path_age_seconds(child) <= ttl_seconds:
                continue
            workspace = child / "workspace"
            if workspace.is_dir():
                self._git_worktree_remove(repo, workspace)
            shutil.rmtree(child, ignore_errors=True)
            removed.append(str(child))

        if removed:
            self._git_worktree_prune(repo)
        return removed
