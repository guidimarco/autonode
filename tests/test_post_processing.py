"""Post-processing runner (allowlisted actions)."""

from __future__ import annotations

import pytest

from autonode.application.workflow.post_processing import run_post_processing
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.workflow.models import PostProcessStepModel


def test_run_post_processing_log_noop_echo() -> None:
    rv = ReviewVerdictModel(is_approved=True, feedback="ok", missing_requirements=[])
    state = {"review_verdict": rv, "iteration": 2, "current_node": "reviewer"}
    steps = [
        PostProcessStepModel(action="log", params={"message": "done", "level": "INFO"}),
        PostProcessStepModel(action="noop", params={}),
        PostProcessStepModel(action="echo_state", params={"keys": ["review_verdict"]}),
    ]
    out = run_post_processing(steps, state)
    assert len(out) == 3
    assert out[0]["action"] == "log"
    assert out[1]["action"] == "noop"
    assert out[2]["action"] == "echo_state"
    assert out[2]["values"] == {"review_verdict": rv}


def test_run_post_processing_unknown_action_raises() -> None:
    with pytest.raises(ValueError, match="non consentita"):
        run_post_processing(
            [PostProcessStepModel(action="rm_rf_root", params={})],
            {},
        )
