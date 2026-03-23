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

    def commit_and_push(self, worktree_path: str, message: str, *, push: bool = True) -> str:
        _ = (worktree_path, message, push)
        return ""
