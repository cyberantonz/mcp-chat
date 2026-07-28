from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from source.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self._engine = create_async_engine(
            settings.database_url.unicode_string(),
            pool_pre_ping=True,
            isolation_level="READ COMMITTED",
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_pool_max_overflow,
            poolclass=AsyncAdaptedQueuePool,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session, session.begin():
            yield session


_database: Database | None = None


def get_database() -> Database:
    global _database  # noqa: PLW0603
    if _database is None:
        _database = Database(Settings())
    return _database
