"""Log assistant textual reasoning to session.log with prefix ``[AGENT_THOUGHT]``."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage


def _textual_content_from_ai_message(content: Any) -> str:
    """Normalize AIMessage.content (str or multimodal blocks) to plain text."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(str(block["text"]))
                elif "text" in block:
                    parts.append(str(block["text"]))
        return "\n".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def log_agent_thought_for_message(
    session_python_logger: logging.Logger | None,
    message: BaseMessage,
) -> None:
    """Write non-empty AIMessage text to the session logger, one log line per content line."""
    if session_python_logger is None:
        return
    if not isinstance(message, AIMessage):
        return
    text = _textual_content_from_ai_message(message.content)
    if not text:
        return
    for line in text.splitlines():
        session_python_logger.info("[AGENT_THOUGHT] %s", line)
