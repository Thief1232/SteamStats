import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI  # noqa: I001
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth_routers import router as auth_router
from src.api.routers import router
from src.db import connection


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connection.connect()
    yield
    await connection.disconnect()


app = FastAPI(lifespan=lifespan)


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
