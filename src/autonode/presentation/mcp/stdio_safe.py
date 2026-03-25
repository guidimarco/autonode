"""
Keep MCP stdio transport healthy: logging and OS fd 1 must not emit non-protocol bytes on stdout.

Python's ``sys.stdout = sys.stderr`` alone does not stop native code or subprocesses that write
to file descriptor 1. During workflow execution we temporarily ``dup2`` stderr onto fd 1, then
restore the original stdout fd so the MCP client can read JSON-RPC again after the tool returns.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager

from autonode.infrastructure.logging.stderr_adapter import install_autonode_process_logging


def configure_mcp_stdio_logging(*, level: int = logging.INFO) -> None:
    """Bootstrap stderr-only logging and ``LoggerFactory`` (MCP keeps JSON-RPC on stdout)."""
    install_autonode_process_logging(level=level)


@contextmanager
def isolate_process_stdout_to_stderr() -> Iterator[None]:
    """
    While active, OS fd 1 (stdout) is redirected to the same sink as stderr.

    Restores the previous stdout fd on exit so the MCP runtime can write responses to the client.
    """
    stdout_fd = 1
    try:
        stderr_fd = sys.stderr.fileno()
    except OSError:
        yield
        return

    try:
        saved_stdout_fd = os.dup(stdout_fd)
    except OSError:
        yield
        return

    old_sys_stdout = sys.stdout
    try:
        os.dup2(stderr_fd, stdout_fd)
        sys.stdout = sys.stderr
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except OSError:
            pass
        try:
            os.dup2(saved_stdout_fd, stdout_fd)
        finally:
            os.close(saved_stdout_fd)
        sys.stdout = old_sys_stdout
