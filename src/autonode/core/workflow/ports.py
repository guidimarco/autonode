"""
Abstract ports (interfaces) for workflow.

This module contains the ports for the workflow and the VCS provider.
"""

from abc import ABC, abstractmethod


class VCSProviderPort(ABC):
    """Abstract VCS adapter (worktree, commit, push) without GitPython in core."""

    @abstractmethod
    def setup_session_worktree(self, session_id: str, repo_path: str) -> str:
        """Return path to session worktree."""

    @abstractmethod
    def commit_and_push(self, message: str, *, push: bool = True) -> str:
        """Return commit hash (or placeholder)."""


class NoOpVcsProvider(VCSProviderPort):
    """No-op VCS: no real worktree or remote; satisfies graph wiring in tests."""

    def setup_session_worktree(self, session_id: str, repo_path: str) -> str:
        return repo_path

    def commit_and_push(self, message: str, *, push: bool = True) -> str:
        return ""
