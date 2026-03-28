"""VCS port stub: solo per compilazione grafo nei test (niente Git reale)."""

from __future__ import annotations

from autonode.core.sandbox.models import WorkspaceBindingModel
from autonode.core.workflow.ports import VCSProviderPort


class StubVcsProviderForCompileTests(VCSProviderPort):
    """
    Implementa VCSProviderPort per `compile_workflow` nei test.
    Il CLI di produzione deve usare sempre GitWorktreeProvider.
    """

    def setup_session_worktree(self, session_id: str, repo_path: str) -> WorkspaceBindingModel:
        raise RuntimeError(
            "StubVcsProviderForCompileTests: provisioning solo con GitWorktreeProvider (CLI)."
        )

    def commit_changes(self, worktree_path: str, message: str) -> str:
        _ = (worktree_path, message)
        return ""

    def remove_session_worktree(self, session_id: str, repo_path: str) -> None:
        _ = (session_id, repo_path)

    def remove_all_session_worktrees(self, repo_path: str) -> None:
        _ = repo_path

    def delete_session_branch(self, repo_path: str, session_id: str) -> None:
        _ = (repo_path, session_id)

    def delete_all_session_branches(self, repo_path: str) -> None:
        _ = repo_path
