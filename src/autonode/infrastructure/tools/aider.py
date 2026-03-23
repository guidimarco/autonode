"""
Aider tool: external process adapter for code edits via Aider CLI.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from autonode.infrastructure.tools.path_guard import resolve_under_root


def _git_worktree_dirty(working_dir: str) -> bool:
    """Return True if ``git status --porcelain`` reports uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def make_aider_tool(working_dir: str = ".") -> BaseTool:
    """
    Build the Aider LangChain tool with cwd set to ``working_dir`` (project root).

    Git Guardrail: if the directory is a Git repo with a dirty working tree,
    the tool returns an error and does not start Aider.
    """

    abs_wd = str(Path(working_dir).resolve())

    @tool
    def aider(instruction: str, files: list[str]) -> str:
        """Usa Aider per modificare il codice nei file specificati (root progetto)."""
        if _git_worktree_dirty(abs_wd):
            return (
                "ERRORE: il repository Git ha modifiche non committate. "
                "Esegui commit o stash prima di usare Aider."
            )

        normalized_files: list[str] = []
        for f in files:
            try:
                candidate = resolve_under_root(abs_wd, f)
            except ValueError as e:
                return f"ERRORE: path file non valido '{f}': {e}"
            if not candidate.exists():
                return "ERRORE: file inesistente per Aider: " f"'{f}' (risolto in '{candidate}')"
            if not candidate.is_file():
                return (
                    "ERRORE: il path indicato non e' un file regolare: "
                    f"'{f}' (risolto in '{candidate}')"
                )
            normalized_files.append(str(candidate.relative_to(abs_wd)))

        command = [
            "aider",
            "--model",
            "openrouter/mistralai/devstral-2512",
            "--yes",
            "--no-git",
            "--no-auto-commit",
            "--cache-prompts",
            "--no-stream",
            "--message",
            instruction,
            "--api-key",
            f"openrouter={os.getenv('OPEN_ROUTER_API_KEY')}",
        ] + normalized_files
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=abs_wd,
            )
            return f"Aider: {result.stdout}"
        except Exception as e:
            return f"Aider: {e}"

    return aider
