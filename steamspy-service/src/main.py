import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routers import router
from src.db import connection
from src.logging_setup import setup_logging
from src.services import http

setup_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connection.connect()
    yield
    await http.close_client()
    await connection.disconnect()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(http.UpstreamError)
async def upstream_unavailable(request: Request, exc: http.UpstreamError):
    # Reached only when there is no cached data to fall back on.
    log.warning("503 for %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "SteamSPY is not responding, try again later"},
        headers={"Retry-After": "60"},
    )


app.include_router(router)
