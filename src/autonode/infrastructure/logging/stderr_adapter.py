"""Autonode logger adapter backed by Python stdlib logging on stderr only."""

from __future__ import annotations

import logging
import sys
from typing import Any

from autonode.core.logging import AutonodeLogger, LoggerFactory


class StandardErrorAutonodeLogger(AutonodeLogger):
    """Adapter implementing the Core logging contract."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, **kwargs)


def create_stderr_autonode_logger(
    *,
    name: str = "autonode",
    level: int = logging.INFO,
) -> AutonodeLogger:
    """
    Core-facing logger: records propagate to the root logger, which must be
    configured with a stderr-only handler (see ``install_autonode_process_logging``).
    """
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = True
    return StandardErrorAutonodeLogger(logger)


def install_autonode_process_logging(*, level: int = logging.INFO) -> None:
    """Configure root logging to stderr only and register the Core ``LoggerFactory``."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    root.addHandler(handler)
    LoggerFactory.set_logger(create_stderr_autonode_logger(level=level))
