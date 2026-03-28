"""
Translation of container path to host path for bind mount to the Docker daemon.

When Autonode runs in a container, ``/src/...`` exists in the container mount but the
Docker daemon resolves the binds on the host filesystem: ``HOST_PROJECTS_ROOT`` is needed for
``REPOS_ROOT`` (e.g. ``/src/autonode_docker/{session_id}/workspace``). I path under
``DATA_ROOT`` (``/data/...``) are not mounted in the sandbox; if you need to resolve a data path
on the host, use ``HOST_DATA_ROOT`` (default typically: ``/home/.../autonode_data``).
"""

from __future__ import annotations

import os
from pathlib import Path

import autonode.core.sandbox.session_paths as session_paths


def host_bind_path_for_container_path(container_path: str) -> str:
    """
    If ``HOST_PROJECTS_ROOT`` is set, map a path under ``REPOS_ROOT`` to the host equivalent.
    If ``HOST_DATA_ROOT`` is set, map path under ``DATA_ROOT``.
    Otherwise return ``container_path`` (e.g. direct execution on the host).
    """
    p = Path(container_path).resolve()

    host_projects = os.environ.get("HOST_PROJECTS_ROOT", "").strip()
    if host_projects:
        root = Path(session_paths.REPOS_ROOT).resolve()
        try:
            rel = p.relative_to(root)
            return str(Path(host_projects) / rel)
        except ValueError:
            pass

    host_data = os.environ.get("HOST_DATA_ROOT", "").strip()
    if host_data:
        data_root = Path(session_paths.DATA_ROOT).resolve()
        try:
            rel = p.relative_to(data_root)
            return str(Path(host_data) / rel)
        except ValueError:
            pass

    return container_path
