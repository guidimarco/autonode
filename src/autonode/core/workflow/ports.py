"""
Abstract ports (interfaces) for workflow.

This module contains the ports for the workflow and the VCS provider.
"""

from abc import ABC, abstractmethod

from autonode.core.sandbox.models import WorkspaceBindingModel


class VCSProviderPort(ABC):
    """Abstract VCS adapter (worktree, commit, push) without GitPython in core."""

    @abstractmethod
    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        """Provision and return host workspace binding for this session."""

    @abstractmethod
    def commit_and_push(self, worktree_path: str, message: str, *, push: bool = True) -> str:
        """Return commit hash (or empty string if nothing to commit)."""

    @abstractmethod
    def remove_session_worktree(self, repo_path: str, session_id: str) -> None:
        """Remove session worktree."""

    @abstractmethod
    def remove_all_session_worktrees(self, repo_path: str) -> None:
        """Remove all session worktrees."""

    @abstractmethod
    def delete_session_branch(self, repo_path: str, session_id: str) -> None:
        """Delete session branch in ``repo_path`` (e.g. ``autonode/session-<id>``)."""

    @abstractmethod
    def delete_all_session_branches(self, repo_path: str) -> None:
        """Delete local branches in ``repo_path`` named ``autonode/session-*``."""
