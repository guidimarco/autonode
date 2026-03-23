"""Tests for Aider tool and Git guardrail."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from autonode.infrastructure.tools.aider import make_aider_tool

# Capture before any monkeypatch: ``subprocess`` is a singleton module.
_SUBPROCESS_RUN = subprocess.run


def test_aider_blocks_when_working_tree_dirty(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "tracked.txt").write_text("v2-dirty\n", encoding="utf-8")

    tool = make_aider_tool(str(tmp_path))
    out = tool.invoke({"instruction": "noop", "files": []})

    assert "ERRORE" in out
    assert "modifiche non committate" in out


def test_aider_runs_when_clean_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    aider_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        if cmd[:1] == ["aider"]:
            aider_calls.append(cmd)
            return MagicMock(stdout="simulated", stderr="", returncode=0)
        return _SUBPROCESS_RUN(cmd, **kwargs)

    monkeypatch.setattr("autonode.infrastructure.tools.aider.subprocess.run", fake_run)

    tool = make_aider_tool(str(tmp_path))
    out = tool.invoke({"instruction": "say hi", "files": ["tracked.txt"]})

    assert "simulated" in out
    assert aider_calls and aider_calls[0][0] == "aider"


def test_aider_rejects_non_existing_files_in_clean_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    tool = make_aider_tool(str(tmp_path))
    out = tool.invoke({"instruction": "edit", "files": ["missing.txt"]})

    assert "ERRORE" in out
    assert "file inesistente" in out
