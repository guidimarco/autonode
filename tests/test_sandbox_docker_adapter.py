"""Test DockerAdapter: immagine sandbox locale e build."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonode.core.sandbox.exceptions import SandboxImageNotFoundError
from autonode.infrastructure.sandbox.docker_adapter import DockerAdapter
from docker import errors as docker_errors  # type: ignore[attr-defined]


@pytest.fixture
def mock_docker_client() -> Iterator[MagicMock]:
    with patch("autonode.infrastructure.sandbox.docker_adapter.docker.from_env") as from_env:
        client = MagicMock()
        from_env.return_value = client
        yield client


def _fake_repo_with_dockerfile(tmp_path: Path) -> None:
    d = tmp_path / "docker"
    d.mkdir(parents=True)
    (d / "sandbox.Dockerfile").write_text("FROM scratch\n", encoding="utf-8")


def test_prepare_skips_build_when_image_exists(mock_docker_client: MagicMock) -> None:
    mock_docker_client.images.get.return_value = object()
    DockerAdapter(prepare_image=True, force_rebuild=False)
    mock_docker_client.images.get.assert_called_once()
    mock_docker_client.images.build.assert_not_called()


def test_prepare_builds_when_image_missing(
    mock_docker_client: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo_with_dockerfile(tmp_path)
    monkeypatch.chdir(tmp_path)
    mock_docker_client.images.get.side_effect = docker_errors.ImageNotFound("missing")
    mock_docker_client.images.build.return_value = (MagicMock(), [])
    DockerAdapter(prepare_image=True, force_rebuild=False)
    mock_docker_client.images.build.assert_called_once()
    call_kw = mock_docker_client.images.build.call_args.kwargs
    assert call_kw["tag"] == "autonode-sandbox:latest"
    assert call_kw["dockerfile"] == "docker/sandbox.Dockerfile"
    assert call_kw["path"] == "."


def test_force_rebuild_calls_build(
    mock_docker_client: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo_with_dockerfile(tmp_path)
    monkeypatch.chdir(tmp_path)
    mock_docker_client.images.build.return_value = (MagicMock(), [])
    DockerAdapter(prepare_image=True, force_rebuild=True)
    mock_docker_client.images.get.assert_not_called()
    mock_docker_client.images.build.assert_called_once()


def test_missing_dockerfile_raises(
    mock_docker_client: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    mock_docker_client.images.get.side_effect = docker_errors.ImageNotFound("missing")
    with pytest.raises(SandboxImageNotFoundError, match="Dockerfile non trovato"):
        DockerAdapter(prepare_image=True, force_rebuild=False)


def test_build_stream_error_raises(
    mock_docker_client: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_repo_with_dockerfile(tmp_path)
    monkeypatch.chdir(tmp_path)
    mock_docker_client.images.get.side_effect = docker_errors.ImageNotFound("missing")
    mock_docker_client.images.build.return_value = (
        MagicMock(),
        iter([{"error": "compile failed"}]),
    )
    with pytest.raises(SandboxImageNotFoundError, match="Build immagine sandbox fallita"):
        DockerAdapter(prepare_image=True, force_rebuild=False)


def test_prepare_image_false_skips(mock_docker_client: MagicMock) -> None:
    DockerAdapter(prepare_image=False)
    mock_docker_client.images.get.assert_not_called()
    mock_docker_client.images.build.assert_not_called()


def test_provision_passes_llm_env_vars(
    mock_docker_client: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_docker_client.images.get.return_value = object()
    monkeypatch.setenv("OPEN_ROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    adapter = DockerAdapter(prepare_image=True, force_rebuild=False)
    container_mock = MagicMock()
    container_mock.id = "abc123"
    mock_docker_client.containers.run.return_value = container_mock

    from autonode.core.sandbox.models import (
        CONTAINER_OUTPUTS_PATH,
        CONTAINER_WORKSPACE_PATH,
        WorkspaceBindingModel,
    )

    sid = "550e8400-e29b-41d4-a716-446655440099"
    ws = WorkspaceBindingModel(
        session_id=sid,
        repo_host_path=str(tmp_path),
        branch_name="autonode/session-x",
    )
    py = logging.getLogger("test.docker_adapter.provision")
    py.handlers.clear()
    with patch.object(adapter, "_start_sandbox_log_thread"):
        adapter.provision_environment(ws, session_python_logger=py)

    env = mock_docker_client.containers.run.call_args.kwargs.get("environment") or {}
    assert env.get("OPEN_ROUTER_API_KEY") == "sk-test"
    assert env.get("OPENAI_API_KEY") == "sk-openai"
    assert "ANTHROPIC_API_KEY" not in env
    assert env.get("PYTHONUNBUFFERED") == "1"

    run_kw = mock_docker_client.containers.run.call_args.kwargs
    assert run_kw.get("tty") is False

    from autonode.core.sandbox.session_paths import session_outputs_path, session_workspace_path
    from autonode.infrastructure.sandbox.host_bind_paths import host_bind_path_for_container_path

    vol = mock_docker_client.containers.run.call_args.kwargs.get("volumes") or {}
    exp_wt = host_bind_path_for_container_path(session_workspace_path(sid))
    exp_out = host_bind_path_for_container_path(session_outputs_path(sid))
    assert vol[exp_wt]["bind"] == CONTAINER_WORKSPACE_PATH
    assert vol[exp_out]["bind"] == CONTAINER_OUTPUTS_PATH
