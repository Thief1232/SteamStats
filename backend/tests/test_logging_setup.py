import io
import logging

import pytest

from src import logging_setup

TOUCHED = ("", "uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "httpcore")


@pytest.fixture
def output():
    """Run setup_logging into a buffer and put the logging config back afterwards."""
    saved = {
        name: (
            logging.getLogger(name).handlers[:],
            logging.getLogger(name).filters[:],
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in TOUCHED
    }
    buffer = io.StringIO()
    logging_setup.setup_logging(buffer)
    yield buffer
    for name, (handlers, filters, level, propagate) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers[:], logger.filters[:] = handlers, filters
        logger.setLevel(level)
        logger.propagate = propagate


def access_line(path: str, status: int) -> None:
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "172.18.0.5:41234", "GET", path, "1.1", status
    )


def test_app_lines_carry_time_level_and_source(output):
    logging.getLogger("src.services.steam_client").warning("Steam throttles us")

    line = output.getvalue().strip()
    assert line.endswith("WARNING [src.services.steam_client] Steam throttles us")
    assert line[:20].endswith("Z")  # 2026-11-27T14:03:12Z


def test_uvicorn_access_lines_use_the_same_format(output):
    access_line("/api/users/1", 200)

    assert '[uvicorn.access] 172.18.0.5:41234 - "GET /api/users/1 HTTP/1.1" 200' in (
        output.getvalue()
    )


def test_progress_polling_is_not_logged_unless_it_fails(output):
    access_line("/api/users/1/library/achievements/progress", 200)
    access_line("/api/users/1/library/achievements/progress", 500)

    lines = output.getvalue().strip().splitlines()
    assert len(lines) == 1 and lines[0].endswith(" 500")


def test_httpx_request_urls_are_not_logged(output):
    # httpx logs full URLs at INFO, and Steam Web API URLs carry the API key.
    logging.getLogger("httpx").info("HTTP Request: GET https://api.steampowered.com/?key=secret")

    assert "secret" not in output.getvalue()


def test_calling_twice_does_not_duplicate_lines(output):
    logging_setup.setup_logging(output)
    logging.getLogger("src").warning("once")

    assert output.getvalue().count("once") == 1
