import logging
import os
import sys
import time

FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _UtcFormatter(logging.Formatter):
    converter = time.gmtime


class _SkipProgressPolling(logging.Filter):
    """Drop successful access-log lines for the achievements progress endpoint: the
    frontend polls it several times a second while a refresh runs."""

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn.access args: (client_addr, method, path, http_version, status_code)
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:
            path, status = args[2], args[4]
            if str(path).endswith("/progress") and isinstance(status, int) and status < 400:
                return False
        return True


def setup_logging(stream=None) -> None:
    """One format for the app and uvicorn, written to stdout (where Dokploy shows it):

        2026-11-27T14:03:12Z WARNING [src.services.steam_client] Steam throttles us ...

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
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _SkipProgressPolling) for f in access.filters):
        access.addFilter(_SkipProgressPolling())

    # httpx logs every request URL at INFO, and Steam Web API URLs carry the API key.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
