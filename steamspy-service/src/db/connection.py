import os
from collections.abc import AsyncGenerator

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def database_url() -> str:
    # URL.create escapes special characters in the password.
    return URL.create(
        "postgresql+asyncpg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    ).render_as_string(hide_password=False)


async def connect() -> None:
    global engine, session_factory
    engine = create_async_engine(database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def disconnect() -> None:
    if engine is not None:
        await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
