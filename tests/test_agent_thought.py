"""Session logging of assistant reasoning (``[AGENT_THOUGHT]``)."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage

from autonode.infrastructure.logging.agent_thought import log_agent_thought_for_message


def test_log_agent_thought_skips_non_ai_and_empty() -> None:
    captured: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record.getMessage())

    py = logging.getLogger("test.agent_thought")
    py.handlers.clear()
    py.setLevel(logging.INFO)
    py.addHandler(_Capture())

    log_agent_thought_for_message(py, HumanMessage(content="x"))
    assert captured == []

    log_agent_thought_for_message(py, AIMessage(content=""))
    assert captured == []


def test_log_agent_thought_writes_prefixed_lines() -> None:
    captured: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record.getMessage())

    py = logging.getLogger("test.agent_thought.lines")
    py.handlers.clear()
    py.setLevel(logging.INFO)
    py.addHandler(_Capture())

    log_agent_thought_for_message(py, AIMessage(content="line one\nline two"))
    assert captured == [
        "[AGENT_THOUGHT] line one",
        "[AGENT_THOUGHT] line two",
    ]
