"""
Docker sandbox adapter using the official docker SDK.

La CLI va eseguita dalla root del repository: contesto di build ``.`` e Dockerfile
``docker/sandbox.Dockerfile``.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docker.client import DockerClient

import docker
from autonode.core.sandbox.exceptions import SandboxImageNotFoundError
from autonode.core.sandbox.models import (
    CONTAINER_OUTPUTS_PATH,
    CONTAINER_WORKSPACE_PATH,
    ExecutionEnvironmentModel,
    WorkspaceBindingModel,
)
from autonode.core.sandbox.ports import SandboxProviderPort
from autonode.infrastructure.sandbox.host_bind_paths import host_bind_path_for_container_path
from docker import errors as docker_errors  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

SANDBOX_IMAGE_TAG = "autonode-sandbox:latest"
SANDBOX_DOCKERFILE = "docker/sandbox.Dockerfile"
SANDBOX_CONTAINER_PREFIX = "autonode-sandbox-"

_SANDBOX_ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "OPEN_ROUTER_API_KEY",
)


def _host_env_for_container() -> dict[str, str]:
    env = {k: v for k in _SANDBOX_ENV_KEYS if (v := os.environ.get(k, "").strip())}
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _sandbox_image_abort(message: str) -> None:
    raise SandboxImageNotFoundError(message)


class DockerAdapter(SandboxProviderPort):
    """Provision and tear down runtime container for a session."""

    def __init__(
        self,
        *,
        image: str = SANDBOX_IMAGE_TAG,
        startup_command: list[str] | None = None,
        prepare_image: bool = True,
        force_rebuild: bool = False,
    ) -> None:
        self._image = image
        self._startup_command = startup_command or ["sleep", "infinity"]
        self._client: DockerClient = docker.from_env()  # type: ignore[attr-defined]
        self._sandbox_log_threads: dict[str, threading.Thread] = {}
        if prepare_image:
            self._ensure_sandbox_image(force_rebuild=force_rebuild)

    @staticmethod
    def _forward_sandbox_container_logs(
        container: Any, session_python_logger: logging.Logger
    ) -> None:
        """Legge lo stream Docker (stdout/stderr) e lo appende al ``logging.Logger`` di sessione."""
        try:
            for chunk in container.logs(
                stdout=True,
                stderr=True,
                stream=True,
                follow=True,
            ):
                if not chunk:
                    continue
                text = (
                    chunk.decode("utf-8", errors="replace")
                    if isinstance(chunk, bytes)
                    else str(chunk)
                )
                for line in text.splitlines():
                    if line:
                        session_python_logger.info("[sandbox] %s", line)
        except Exception as e:
            session_python_logger.warning(
                "[sandbox] Log stream failed: %s",
                e,
                exc_info=True,
            )

    def _start_sandbox_log_thread(
        self,
        container: Any,
        session_id: str,
        session_python_logger: logging.Logger,
    ) -> None:
        t = threading.Thread(
            target=self._forward_sandbox_container_logs,
            args=(container, session_python_logger),
            daemon=True,
            name=f"autonode-sandbox-logs-{session_id}",
        )
        self._sandbox_log_threads[session_id] = t
        t.start()

    def _ensure_sandbox_image(self, *, force_rebuild: bool) -> None:
        if not force_rebuild:
            try:
                self._client.images.get(self._image)
                return
            except docker_errors.ImageNotFound:
                pass

        context = Path.cwd()
        dockerfile_path = context / SANDBOX_DOCKERFILE
        if not dockerfile_path.is_file():
            _sandbox_image_abort(
                "Sandbox Docker: Dockerfile non trovato "
                f"(cwd={context}, atteso ./{SANDBOX_DOCKERFILE}). "
                "Esegui autonode dalla root del repository.",
            )

        try:
            _, build_logs = self._client.images.build(
                path=".",
                dockerfile=SANDBOX_DOCKERFILE,
                tag=self._image,
                rm=True,
            )
            for chunk in build_logs:
                if not isinstance(chunk, dict):
                    continue
                if "errorDetail" in chunk:
                    detail: object = chunk["errorDetail"]
                    if isinstance(detail, dict):
                        raw_msg = detail.get("message", str(detail))
                        err_msg = raw_msg if isinstance(raw_msg, str) else str(raw_msg)
                    else:
                        err_msg = str(detail)
                    _sandbox_image_abort(f"Build immagine sandbox fallita: {err_msg}")
                if "error" in chunk:
                    _sandbox_image_abort(f"Build immagine sandbox fallita: {chunk['error']}")
        except docker_errors.BuildError as e:
            _sandbox_image_abort(
                f"Impossibile preparare l'ambiente sandbox Docker (build fallita): {e}",
            )
        except docker_errors.APIError as e:
            _sandbox_image_abort(
                f"Impossibile preparare l'ambiente sandbox Docker (errore API Docker): {e}",
            )

    def provision_environment(
        self,
        workspace: WorkspaceBindingModel,
        *,
        session_python_logger: logging.Logger,
    ) -> ExecutionEnvironmentModel:
        env = _host_env_for_container()
        container = self._client.containers.run(
            self._image,
            command=self._startup_command,
            detach=True,
            tty=False,
            auto_remove=True,
            name=f"{SANDBOX_CONTAINER_PREFIX}{workspace.session_id}",
            working_dir=CONTAINER_WORKSPACE_PATH,
            environment=env,
            volumes={
                host_bind_path_for_container_path(workspace.worktree_host_path): {
                    "bind": CONTAINER_WORKSPACE_PATH,
                    "mode": "rw",
                },
                host_bind_path_for_container_path(workspace.outputs_host_path): {
                    "bind": CONTAINER_OUTPUTS_PATH,
                    "mode": "rw",
                },
            },
        )

        self._start_sandbox_log_thread(container, workspace.session_id, session_python_logger)

        return ExecutionEnvironmentModel(
            session_id=workspace.session_id,
            sandbox_id=str(container.id),
            repo_host_path=workspace.repo_host_path,
        )

    def release_environment(self, environment: ExecutionEnvironmentModel) -> None:
        if not environment.sandbox_id or environment.sandbox_id == "host-runtime":
            return

        sid = environment.session_id
        try:
            container = self._client.containers.get(environment.sandbox_id)
        except docker_errors.NotFound:
            self._join_sandbox_log_thread(sid)
            return

        # Stop/remove first so the logs follow stream ends; then join the reader thread.
        container.remove(force=True)
        self._join_sandbox_log_thread(sid)

    def _join_sandbox_log_thread(self, session_id: str) -> None:
        t = self._sandbox_log_threads.pop(session_id, None)
        if t is not None and t.is_alive():
            t.join(timeout=15.0)

    def list_active_sandboxes(self) -> list[str]:
        """Return names of containers whose name starts with ``autonode-sandbox-``."""
        prefix = SANDBOX_CONTAINER_PREFIX
        names: list[str] = []
        for container in self._client.containers.list(all=True):
            name = (container.name or "").lstrip("/")
            if name.startswith(prefix):
                names.append(name)
        return sorted(names)

    def _container_age_days(self, created_iso: str) -> float:
        s = created_iso
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return (datetime.now(UTC) - dt).total_seconds() / 86400.0

    def remove_stale_autonode_sandboxes(self, ttl_days: float = 1.0) -> list[str]:
        """Remove autonode sandbox containers older than ``ttl_days`` (Docker Created)."""
        prefix = SANDBOX_CONTAINER_PREFIX
        removed: list[str] = []
        for container in self._client.containers.list(all=True):
            name = (container.name or "").lstrip("/")
            if not name.startswith(prefix):
                continue
            created = container.attrs.get("Created") or ""
            try:
                age_days = self._container_age_days(str(created))
            except (TypeError, ValueError):
                continue
            if age_days <= ttl_days:
                continue
            try:
                container.remove(force=True)
                removed.append(name)
            except docker_errors.NotFound:
                continue
        return sorted(removed)

    def remove_session_sandbox(self, session_id: str) -> None:
        name = f"{SANDBOX_CONTAINER_PREFIX}{session_id}"
        self.remove_autonode_sandboxes([name])
        logger.info("Removed sandbox: %s", name)

    def remove_all_session_sandboxes(self) -> None:
        removed = self.remove_autonode_sandboxes()
        logger.info("Removed all sandbox containers: %s", removed)

    def remove_autonode_sandboxes(self, names: list[str] | None = None) -> list[str]:
        """
        Force-remove autonode sandbox containers. If ``names`` is None, removes all active
        sandboxes returned by :meth:`list_active_sandboxes`.
        """
        target = names if names is not None else self.list_active_sandboxes()
        removed: list[str] = []
        for name in target:
            try:
                c = self._client.containers.get(name)
                c.remove(force=True)
                removed.append(name)
            except docker_errors.NotFound:
                continue
        return sorted(removed)
