"""Post-processing runner (allowlisted actions)."""

from __future__ import annotations

import pytest

from autonode.application.post_processing import run_post_processing
from autonode.core.workflow.models import PostProcessStepConfig


def test_run_post_processing_log_noop_echo() -> None:
    state = {"verdict": "approved", "iteration": 2, "current_node": "reviewer"}
    steps = [
        PostProcessStepConfig(action="log", params={"message": "done", "level": "INFO"}),
        PostProcessStepConfig(action="noop", params={}),
        PostProcessStepConfig(action="echo_state", params={"keys": ["verdict"]}),
    ]
    out = run_post_processing(steps, state)
    assert len(out) == 3
    assert out[0]["action"] == "log"
    assert out[1]["action"] == "noop"
    assert out[2]["action"] == "echo_state"
    assert out[2]["values"] == {"verdict": "approved"}


def test_run_post_processing_unknown_action_raises() -> None:
    with pytest.raises(ValueError, match="non consentita"):
        run_post_processing(
            [PostProcessStepConfig(action="rm_rf_root", params={})],
            {},
        )
