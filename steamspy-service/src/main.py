from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from src.api.routers import router
from src.db import connection


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connection.connect()
    yield
    await connection.disconnect()


app = FastAPI(lifespan=lifespan)
app.include_router(router)