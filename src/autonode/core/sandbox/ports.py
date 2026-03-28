"""
Core sandbox ports.
"""

import logging
from abc import ABC, abstractmethod

from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel


class SandboxProviderPort(ABC):
    """Abstract runtime sandbox provider."""

    @abstractmethod
    def provision_environment(
        self,
        workspace: WorkspaceBindingModel,
        *,
        session_python_logger: logging.Logger,
    ) -> ExecutionEnvironmentModel:
        """Provision/resolve runtime and return a session execution environment."""

    @abstractmethod
    def release_environment(self, environment: ExecutionEnvironmentModel) -> None:
        """Release runtime resources associated with a session environment."""

    @abstractmethod
    def remove_session_sandbox(self, session_id: str) -> None:
        """Remove session sandbox."""

    @abstractmethod
    def remove_all_session_sandboxes(self) -> None:
        """Remove all session sandboxes."""
