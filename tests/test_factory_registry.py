"""Graph factory registry."""

from unittest.mock import MagicMock

import pytest

from autonode.application.workflow.factories import registry as reg
from autonode.core.workflow import WorkflowModel


def test_register_and_resolve_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    fake: dict[str, reg.GraphFactoryFn] = {}
    monkeypatch.setattr(reg, "FACTORY_REGISTRY", fake)

    @reg.register_factory("test_echo")
    def build(ctx: reg.FactoryContext) -> str:
        return ctx.workflow.factory

    assert reg.get_registered_factory("test_echo") is build
    ctx = reg.FactoryContext(
        workflow=WorkflowModel(version=2, factory="ignored"),
        agent_factory=MagicMock(),
        tool_registry=MagicMock(),
        vcs_provider=MagicMock(),
    )
    assert build(ctx) == "ignored"


def test_duplicate_factory_registration_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    fake: dict[str, reg.GraphFactoryFn] = {}
    monkeypatch.setattr(reg, "FACTORY_REGISTRY", fake)

    @reg.register_factory("dup")
    def _a(ctx: reg.FactoryContext) -> None:
        return None

    with pytest.raises(ValueError, match="Duplicate factory registration"):

        @reg.register_factory("dup")
        def _b(ctx: reg.FactoryContext) -> None:
            return None


def test_missing_factory_keyerror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reg, "FACTORY_REGISTRY", {})
    with pytest.raises(KeyError, match="No graph factory registered"):
        reg.get_registered_factory("nope")
