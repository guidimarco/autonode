from __future__ import annotations

import os
from typing import TYPE_CHECKING

from autonode.bootstrap import AppContainer
from autonode.core.logging import LoggerFactory

if TYPE_CHECKING:
    from autonode.bootstrap import AppContainer

log = LoggerFactory.get_logger()


def run_server(container: AppContainer, port: int, host: str, log_level: int) -> None:
    """
    Run the FastAPI app (uvicorn). Logging must be configured by the entrypoint
    (e.g. ``install_autonode_process_logging`` in ``__main__``).
    """
    import uvicorn

    from autonode.presentation.api import app

    app.state.container = container

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
        log.info("Starting FastAPI on http://%s:%d", host, port)
        server.run()

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
