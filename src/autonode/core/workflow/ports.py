"""
Abstract ports (interfaces) for workflow.

This module contains the ports for the workflow and the VCS provider.
"""

from abc import ABC, abstractmethod

from autonode.core.sandbox.models import WorkspaceBindingModel


class VCSProviderPort(ABC):
    """Abstract VCS adapter (worktree, local commit) without GitPython in core."""

    @abstractmethod
    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        """Provision and return host workspace binding for this session."""

    @abstractmethod
    def commit_changes(self, worktree_path: str, message: str) -> str:
        """Return commit hash (or empty string if nothing to commit)."""

    @abstractmethod
    def remove_session_worktree(self, session_id: str, repo_path: str) -> None:
        """Rimuove il worktree Git (cartella ``workspace``); ``repo_path`` identifica il repo."""

    @abstractmethod
    def remove_all_session_worktrees(self, repo_path: str) -> None:
        """Remove all session worktrees."""

    @abstractmethod
    def delete_session_branch(self, repo_path: str, session_id: str) -> None:
        """Delete session branch in ``repo_path`` (e.g. ``autonode/session-<id>``)."""

    @abstractmethod
    def delete_all_session_branches(self, repo_path: str) -> None:
        """Delete local branches in ``repo_path`` named ``autonode/session-*``."""
