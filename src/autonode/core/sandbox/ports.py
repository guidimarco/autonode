"""
Core sandbox ports.
"""

from abc import ABC, abstractmethod

from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel


class SandboxProviderPort(ABC):
    """Abstract runtime sandbox provider."""

    @abstractmethod
    def provision_environment(self, workspace: WorkspaceBindingModel) -> ExecutionEnvironmentModel:
        """Provision/resolve runtime and return a session execution environment."""

    @abstractmethod
    def release_environment(self, environment: ExecutionEnvironmentModel) -> None:
        """Release runtime resources associated with a session environment."""
