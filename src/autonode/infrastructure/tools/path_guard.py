"""
Path sandbox utilities: resolve roots and reject paths outside the allowed directory.
"""

from __future__ import annotations

from pathlib import Path


def resolved_root(root_dir: str) -> Path:
    """Return the canonical absolute path for the sandbox root."""
    return Path(root_dir).expanduser().resolve()


def resolve_under_root(root_dir: str, relative_path: str) -> Path:
    """
    Resolve ``relative_path`` (relative to ``root_dir``) and ensure it stays inside
    the sandbox. Blocks directory traversal via ``..`` or symlinks that escape root.

    Raises:
        ValueError: If ``relative_path`` resolves outside ``root_dir`` or is an absolute path.
    """
    root = resolved_root(root_dir)
    rel = (relative_path or ".").strip() or "."
    if Path(rel).is_absolute():
        msg = "path assoluto non permesso: la sandbox accetta solo path relativi alla root"
        raise ValueError(msg)

    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise ValueError(
            f"path fuori dalla sandbox: {candidate} (root: {root})",
        ) from e
    return candidate
