"""Tests for ignore_rules blacklist."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.infrastructure.tools.ignore_rules import SKIP_DIR_NAMES, should_skip


def test_skip_dir_names_contains_expected_entries() -> None:
    assert ".git" in SKIP_DIR_NAMES
    assert "node_modules" in SKIP_DIR_NAMES
    assert "vendor" in SKIP_DIR_NAMES
    assert ".venv" in SKIP_DIR_NAMES
    assert "__pycache__" in SKIP_DIR_NAMES
    assert ".cache" in SKIP_DIR_NAMES
    assert "dist" in SKIP_DIR_NAMES
    assert "build" in SKIP_DIR_NAMES


@pytest.mark.parametrize(
    "path",
    [
        Path("node_modules/foo/bar.js"),
        Path("src/.git/hooks/pre-commit"),
        Path(".venv/lib/python3.12/site-packages/x.py"),
        Path("pkg/vendor/dep/readme.md"),
        Path("__pycache__/mod.cpython-312.pyc"),
        Path("project/.cache/index"),
        Path("dist/bundle.js"),
        Path("build/out.o"),
    ],
)
def test_should_skip_true_when_blacklisted_segment_appears(path: Path) -> None:
    assert should_skip(path) is True


def test_should_skip_false_for_clean_source_paths() -> None:
    assert should_skip(Path("src/autonode/main.py")) is False
    assert should_skip(Path("lib/utils.ts")) is False
