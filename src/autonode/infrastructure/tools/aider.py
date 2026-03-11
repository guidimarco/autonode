"""
Aider tool: external process adapter for code edits via Aider CLI.
"""

import os
import subprocess

from langchain_core.tools import tool


@tool
def aider_tool(instruction: str, files: list[str]) -> str:
    """Usa Aider per modificare il codice nei file specificati."""
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
    ] + list(files)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd="./playground",
        )
        return f"Aider: {result.stdout}"
    except Exception as e:
        return f"Aider: {e}"
