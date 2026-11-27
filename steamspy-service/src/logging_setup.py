import logging
import os
import sys
import time

FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _UtcFormatter(logging.Formatter):
    converter = time.gmtime


def setup_logging(stream=None) -> None:
    """One format for the app and uvicorn, written to stdout (where Dokploy shows it):

        2026-11-27T14:03:12Z WARNING [src.services.stats] serving cached top games: ...

    Level from LOG_LEVEL (default INFO). `stream` is for tests.
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(_UtcFormatter(FORMAT, DATE_FORMAT))

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    # uvicorn sets up its own handlers before importing the app; route its loggers
    # through the root handler instead so every line looks the same.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    # httpx would log every outgoing request at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
