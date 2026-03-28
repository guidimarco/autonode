"""Bind mount path mapping HOST_PROJECTS_ROOT → container paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.infrastructure.sandbox.host_bind_paths import host_bind_path_for_container_path


def test_without_host_projects_root_returns_container_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOST_PROJECTS_ROOT", raising=False)
    p = "/src/autonode_docker/x/workspace"
    assert host_bind_path_for_container_path(p) == p


def test_with_host_projects_root_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST_PROJECTS_ROOT", "/home/user/projects")
    got = host_bind_path_for_container_path("/src/foo/bar")
    assert got == str(Path("/home/user/projects/foo/bar"))


def test_with_host_data_root_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOST_PROJECTS_ROOT", raising=False)
    monkeypatch.setenv("HOST_DATA_ROOT", "/host/autonode_data")
    got = host_bind_path_for_container_path("/data/sess-uuid/logs")
    assert got == str(Path("/host/autonode_data/sess-uuid/logs"))
