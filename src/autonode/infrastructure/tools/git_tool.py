"""
Host-side git diff tools scoped to the worktree root.
"""

from __future__ import annotations

import subprocess

from langchain_core.tools import BaseTool, tool

from autonode.infrastructure.tools.path_guard import resolved_root


def _run_git_diff(root_dir: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root_dir,
        capture_output=True,
        text=True,
    )


def make_git_diff_tool(root_dir: str) -> BaseTool:
    """Factory: tool that returns `git diff --stat` and `git diff` output."""

    root_abs = str(resolved_root(root_dir))

    @tool
    def git_diff() -> str:
        """Mostra differenze Git correnti (`git diff --stat` e patch completa)."""
        stat = _run_git_diff(root_abs, ["diff", "--stat"])
        patch = _run_git_diff(root_abs, ["diff"])

        if stat.returncode != 0:
            return f"ERRORE: git diff --stat fallito.\n{stat.stderr.strip()}"
        if patch.returncode != 0:
            return f"ERRORE: git diff fallito.\n{patch.stderr.strip()}"

        stat_out = stat.stdout.strip() or "(nessuna differenza)"
        patch_out = patch.stdout.strip()
        if not patch_out:
            return stat_out
        return f"{stat_out}\n\n{patch_out}"

    return git_diff
