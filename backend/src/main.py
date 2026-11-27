import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.auth_routers import router as auth_router
from src.api.routers import router
from src.db import connection
from src.logging_setup import setup_logging
from src.services import steam_client

setup_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connection.connect()
    yield
    await steam_client.close_client()
    await connection.disconnect()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(steam_client.SteamApiError)
async def steam_unavailable(request: Request, exc: steam_client.SteamApiError):
    # Steam failed and there was no cached data to fall back on, or a rate limit cut
    # an achievements refresh short (what was fetched before it is saved).
    log.warning("503 for %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Steam is not responding, try again later"},
        headers={"Retry-After": "60"},
    )


# Everything is normally served from one origin through Caddy, so CORS is off unless
# CORS_ORIGINS lists origins (comma-separated), e.g. a Vite dev server opened directly.
cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)
app.include_router(auth_router)
