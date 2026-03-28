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

import autonode.core.sandbox.session_paths as session_paths
from autonode.core.sandbox.models import WorkspaceBindingModel
from autonode.core.workflow.ports import VCSProviderPort
from autonode.infrastructure.paths.repo_resolution import ensure_git_repo_under_root

logger = logging.getLogger(__name__)

_SESSION_ID_MARKER_FILENAME = ".autonode_session_id"
_SOURCE_REPO_METADATA = ".source_repo"


def _branch_label_for_session(session_id: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", session_id.strip()).strip("-") or "session"
    return f"autonode/session-{token[:80]}"


def _repo_rel_posix(repo: Path) -> str:
    root = Path(session_paths.REPOS_ROOT).resolve()
    return repo.resolve().relative_to(root).as_posix()


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

    @staticmethod
    def _session_repo_matches(session_root: Path, expected_rel_posix: str) -> bool:
        meta = session_root / _SOURCE_REPO_METADATA
        if not meta.is_file():
            return False
        return meta.read_text(encoding="utf-8").strip() == expected_rel_posix

    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        repo = ensure_git_repo_under_root(repo_path)
        branch_name = _branch_label_for_session(session_id)

        if not (repo / ".git").exists():
            msg = (
                f"The directory {repo} is not a Git checkout (.git missing): "
                "impossible to create an isolated worktree."
            )
            raise RuntimeError(msg)

        session_root = Path(session_paths.session_op_root(session_id))
        wt = Path(session_paths.session_workspace_path(session_id))
        out = Path(session_paths.session_outputs_path(session_id))

        session_root.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)

        (session_root / _SOURCE_REPO_METADATA).write_text(
            _repo_rel_posix(repo),
            encoding="utf-8",
        )

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

    def remove_session_worktree(self, session_id: str, repo_path: str) -> None:
        repo = ensure_git_repo_under_root(repo_path)
        wt = Path(session_paths.session_workspace_path(session_id))
        session_root = Path(session_paths.session_op_root(session_id))

        if wt.is_dir():
            self._git_worktree_remove(repo, wt)
            logger.info("Worktree sessione %s rimosso: %s", session_id, wt)
        self._git_worktree_prune(repo)

        if session_root.is_dir():
            shutil.rmtree(session_root, ignore_errors=True)
            logger.info(
                "Cartella operativa Docker rimossa (dati persistenti in DATA_ROOT): %s",
                session_root,
            )

    def remove_all_session_worktrees(self, repo_path: str) -> None:
        repo = ensure_git_repo_under_root(repo_path)
        expected_rel = _repo_rel_posix(repo)
        root = Path(session_paths.docker_sessions_root())
        if not root.is_dir():
            logger.info("Nessuna directory autonode_docker: %s", root)
            return

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if not self._session_repo_matches(child, expected_rel):
                continue
            workspace = child / "workspace"
            if workspace.is_dir():
                self._git_worktree_remove(repo, workspace)
            logger.info("Worktree rimosso (cartella sessione conservata): %s", child)

        self._git_worktree_prune(repo)
        logger.info("Rimossi i worktree per repo %s sotto %s", expected_rel, root)

    def delete_session_branch(self, repo_path: str, session_id: str) -> None:
        repo = ensure_git_repo_under_root(repo_path)
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
        repo = ensure_git_repo_under_root(repo_path)
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
        Under ``{REPOS_ROOT}/autonode_docker/<session_id>/``, remove worktree and operational folder
        for this repository older than ``ttl_days``.
        """
        repo = ensure_git_repo_under_root(repo_path)
        expected_rel = _repo_rel_posix(repo)
        root = Path(session_paths.docker_sessions_root())
        if not root.is_dir():
            return []

        ttl_seconds = max(0, ttl_days) * 86400
        removed: list[str] = []

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if not self._session_repo_matches(child, expected_rel):
                continue
            if self._path_age_seconds(child) <= ttl_seconds:
                continue
            workspace = child / "workspace"
            if workspace.is_dir():
                self._git_worktree_remove(repo, workspace)
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            removed.append(str(child))

        if removed:
            self._git_worktree_prune(repo)
        return removed
