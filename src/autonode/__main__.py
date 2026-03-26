from __future__ import annotations

import logging
import os

from autonode.bootstrap import bootstrap_app
from autonode.infrastructure.logging.stderr_adapter import install_autonode_process_logging
from autonode.server import run_server


def main() -> None:
    """
    Entry point.
    """
    log_level = getattr(logging, os.environ.get("AUTONODE_LOG_LEVEL", "INFO").upper(), logging.INFO)
    install_autonode_process_logging(level=log_level)
    # ^ ^ ^ Configure the logger to stderr only
    container = bootstrap_app()

    port = int(os.environ.get("AUTONODE_PORT", "8000"))
    host = os.environ.get("AUTONODE_HOST", "0.0.0.0")

    run_server(container, port, host, log_level)


if __name__ == "__main__":
    main()
