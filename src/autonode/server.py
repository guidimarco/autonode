from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

from autonode.bootstrap import AppContainer
from autonode.core.logging import LoggerFactory

if TYPE_CHECKING:
    from autonode.bootstrap import AppContainer

log = LoggerFactory.get_logger()


def run_server(container: AppContainer, port: int, host: str, log_level: int) -> None:
    """
    Run the server:
    - FastAPI
    - MCP stdio
    """
    import uvicorn

    from autonode.presentation.api import app
    from autonode.presentation.mcp.server import run_mcp_server
    from autonode.presentation.mcp.stdio_safe import configure_mcp_stdio_logging

    app.state.container = container
    configure_mcp_stdio_logging(level=log_level)

    # --- MCP stdio ---
    mcp_thread = threading.Thread(
        target=run_mcp_server,
        kwargs={"container": container, "log_level": log_level},
        daemon=True,
    )

    # --- Uvicorn for FastAPI ---
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        workers=1,
        reload=False,
    )
    server = uvicorn.Server(config)

    try:
        # --- Start MCP ---
        mcp_thread.start()
        # ^ ^ ^ Start the MCP stdio server in a separate thread
        # to avoid blocking the FastAPI server

        # --- Start FastAPI ---
        server.run()
        log.info("FastAPI server started on http://%s:%d", host, port)

    except KeyboardInterrupt:
        log.info("Keyboard interrupt received! Shutting down...")
    except Exception as e:
        log.error("Error during server execution: %s", e)
    finally:
        log.info("Shutting down...")

        try:
            container.checkpoint_manager.close()
            log.info("Checkpoint manager closed")
        except Exception as e:
            log.error("Error closing checkpoint manager: %s", e)

        import sys

        sys.stdout.flush()
        sys.stderr.flush()

        log.info("Exiting...")
        os._exit(0)
