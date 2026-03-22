"""
Static ignore rules for repository walks and search (blacklist by directory name).
"""

from __future__ import annotations

from pathlib import Path

# Directory name segments to skip anywhere in a path (fast, language-agnostic).
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        ".venv",
        "__pycache__",
        ".cache",
        "dist",
        "build",
    },
)


def should_skip(path: Path) -> bool:
    """
    Return True if ``path`` lies under (or equals) a blacklisted directory segment.

    Works for both files and directories by inspecting :attr:`path.parts`.
    """
    return any(part in SKIP_DIR_NAMES for part in path.parts)
