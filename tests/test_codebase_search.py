"""Tests for search_codebase tool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from autonode.infrastructure.tools import codebase_search as cs


def test_search_codebase_python_fallback_finds_matches(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello UNIQUE_MARKER_123\nsecond line\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("no match here\n", encoding="utf-8")

    lines, truncated = cs._search_with_python(tmp_path, "UNIQUE_MARKER_123")
    assert len(lines) == 1
    assert "a.txt:1:" in lines[0]
    assert truncated is False


def test_search_codebase_python_respects_max_results(tmp_path: Path) -> None:
    for i in range(60):
        (tmp_path / f"f{i}.txt").write_text(f"MANY {i}\n", encoding="utf-8")

    lines, truncated = cs._search_with_python(tmp_path, "MANY")
    assert len(lines) == cs._MAX_RESULTS
    assert truncated is True


def test_search_codebase_tool_empty_query() -> None:
    tool = cs.make_search_codebase_tool(".")
    out = tool.invoke({"query": "   "})
    assert "ERRORE" in out and "vuota" in out


def test_make_search_codebase_invocation(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("findme_xyz\n", encoding="utf-8")
    tool = cs.make_search_codebase_tool(str(tmp_path))
    out = tool.invoke({"query": "findme_xyz"})
    assert "findme_xyz" in out or "z.txt" in out


def test_search_with_ripgrep_returns_none_when_rg_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "autonode.infrastructure.tools.codebase_search.shutil.which",
        lambda _: None,
    )
    assert cs._search_with_ripgrep(Path("/tmp"), "x") is None


def test_search_with_ripgrep_reads_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "autonode.infrastructure.tools.codebase_search.shutil.which",
        lambda _: "/bin/fake_rg",
    )

    buf = ["a.py:1:alpha\n", "b.py:2:beta\n", ""]

    def fake_readline() -> str:
        return buf.pop(0) if buf else ""

    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = fake_readline
    mock_stdout.close = MagicMock()

    mock_proc = MagicMock()
    mock_proc.stdout = mock_stdout
    mock_proc.poll.return_value = None
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0

    monkeypatch.setattr(
        "autonode.infrastructure.tools.codebase_search.subprocess.Popen",
        lambda *_a, **_k: mock_proc,
    )

    result = cs._search_with_ripgrep(tmp_path, "q")
    assert result is not None
    out_lines, truncated = result
    assert out_lines == ["a.py:1:alpha", "b.py:2:beta"]
    assert truncated is False


def test_search_with_ripgrep_truncation_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "autonode.infrastructure.tools.codebase_search.shutil.which",
        lambda _: "/bin/fake_rg",
    )

    buf = [f"file{i}.txt:1:hit\n" for i in range(cs._MAX_RESULTS + 2)]

    def fake_readline() -> str:
        return buf.pop(0) if buf else ""

    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = fake_readline
    mock_stdout.close = MagicMock()

    mock_proc = MagicMock()
    mock_proc.stdout = mock_stdout
    mock_proc.poll.return_value = None
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0

    monkeypatch.setattr(
        "autonode.infrastructure.tools.codebase_search.subprocess.Popen",
        lambda *_a, **_k: mock_proc,
    )

    result = cs._search_with_ripgrep(tmp_path, "q")
    assert result is not None
    out_lines, truncated = result
    assert len(out_lines) == cs._MAX_RESULTS
    assert truncated is True
