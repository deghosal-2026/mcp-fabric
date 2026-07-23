"""Async database session management.

Provides an async SQLAlchemy engine and session factory configured
from Settings. Sessions yield on commit=False to allow rollback.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
