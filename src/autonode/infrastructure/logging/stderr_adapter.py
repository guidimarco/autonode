"""Autonode logger adapter: stderr + file globale per errori di sistema."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from autonode.core.logging import AutonodeLogger, LoggerFactory
from autonode.core.sandbox.session_paths import REPOS_ROOT


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
    """
    Configura logging su stderr, file globale ``{REPOS_ROOT}/autonode/autonode.log``
    (WARNING+), e registra il Core ``LoggerFactory``.
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stderr_h = logging.StreamHandler(stream=sys.stderr)
    stderr_h.setLevel(level)
    stderr_h.setFormatter(fmt)
    root.addHandler(stderr_h)

    app_dir = Path(REPOS_ROOT) / "autonode"
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
        global_h = logging.FileHandler(app_dir / "autonode.log", encoding="utf-8")
        global_h.setLevel(logging.WARNING)
        global_h.setFormatter(fmt)
        root.addHandler(global_h)
    except OSError:
        pass

    LoggerFactory.set_logger(create_stderr_autonode_logger(level=level))
