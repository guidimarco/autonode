"""Core logging contract and registry."""

from __future__ import annotations

from typing import Any, Protocol


class AutonodeLogger(Protocol):
    """Minimal logging contract shared across layers."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class _NullLogger:
    """Safe default logger used before bootstrap."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        return None

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        return None

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        return None

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        return None

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        return None


_logger_instance: AutonodeLogger = _NullLogger()


class LoggerFactory:
    """Global logger registry for internal layers."""

    @staticmethod
    def get_logger() -> AutonodeLogger:
        return _logger_instance

    @staticmethod
    def set_logger(logger: AutonodeLogger) -> None:
        global _logger_instance
        _logger_instance = logger

    @staticmethod
    def reset_to_default() -> None:
        """Restore the pre-bootstrap null logger (e.g. after tests that swap the registry)."""
        global _logger_instance
        _logger_instance = _NullLogger()
