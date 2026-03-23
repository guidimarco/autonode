"""
Docker sandbox adapter using the official docker SDK.

La CLI va eseguita dalla root del repository: contesto di build ``.`` e Dockerfile
``docker/sandbox.Dockerfile``.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from docker.client import DockerClient

import docker
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel
from autonode.core.sandbox.ports import SandboxProviderPort
from docker import errors as docker_errors  # type: ignore[attr-defined]

SANDBOX_IMAGE_TAG = "autonode-sandbox:latest"
SANDBOX_DOCKERFILE = "docker/sandbox.Dockerfile"

_SANDBOX_ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "OPEN_ROUTER_API_KEY",
)


def _host_env_for_container() -> dict[str, str]:
    return {k: v for k in _SANDBOX_ENV_KEYS if (v := os.environ.get(k, "").strip())}


def _sandbox_image_abort(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


class DockerAdapter(SandboxProviderPort):
    """Provision and tear down runtime container for a session."""

    def __init__(
        self,
        *,
        image: str = SANDBOX_IMAGE_TAG,
        container_workspace_path: str = "/workspace",
        startup_command: list[str] | None = None,
        prepare_image: bool = True,
        force_rebuild: bool = False,
    ) -> None:
        self._image = image
        self._container_workspace_path = container_workspace_path
        self._startup_command = startup_command or ["sleep", "infinity"]
        self._client: DockerClient = docker.from_env()  # type: ignore[attr-defined]
        if prepare_image:
            self._ensure_sandbox_image(force_rebuild=force_rebuild)

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

    def provision_environment(self, workspace: WorkspaceBindingModel) -> ExecutionEnvironmentModel:
        env = _host_env_for_container()
        container = self._client.containers.run(
            self._image,
            command=self._startup_command,
            detach=True,
            tty=True,
            name=f"autonode-sandbox-{workspace.session_id}",
            working_dir=self._container_workspace_path,
            environment=env,
            volumes={
                workspace.worktree_host_path: {
                    "bind": self._container_workspace_path,
                    "mode": "rw",
                }
            },
        )

        return ExecutionEnvironmentModel(
            session_id=workspace.session_id,
            sandbox_id=str(container.id),
            worktree_host_path=workspace.worktree_host_path,
            container_workspace_path=self._container_workspace_path,
        )

    def release_environment(self, environment: ExecutionEnvironmentModel) -> None:
        if not environment.sandbox_id or environment.sandbox_id == "host-runtime":
            return

        try:
            container = self._client.containers.get(environment.sandbox_id)
        except docker_errors.NotFound:
            return

        container.remove(force=True)

    def list_active_sandboxes(self) -> list[str]:
        """Return names of containers whose name starts with ``autonode-sandbox-``."""
        prefix = "autonode-sandbox-"
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
        prefix = "autonode-sandbox-"
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
