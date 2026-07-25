"""Async database session management.

Provides an async SQLAlchemy engine and session factory configured
from Settings. Sessions yield on commit=False to allow rollback.

ARCHITECTURE NOTES:
  - The engine and session_factory are module-level singletons created
    at import time. This is safe because they hold no per-request state.
  - The async_sessionmaker is configured with expire_on_commit=False,
    which means objects retrieved within a session remain usable after
    commit. This is important for building API responses after
    committing database changes.
  - pool_pre_ping=True on the engine ensures stale connections are
    detected and replaced before use (important for long-running
    server processes).
  - For production (PostgreSQL), configure connection pool sizing via
    the URL or engine kwargs. SQLite ignores pool settings.

IMPORTANT: This module is the "simple" path used by Alembic migrations
and simple scripts. The lifespan-managed engine in main.py is used at
runtime. get_db() here is a convenience for tests and one-off operations.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import settings

# Module-level async engine singleton. pool_pre_ping verifies connections
# before handing them out, which prevents "stale connection" errors after
# the database restarts or a network blip.
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True, pool_size=20)

# Session factory bound to the engine. expire_on_commit=False allows
# ORM objects to remain usable for serialization after commit().
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """Async generator yielding a single database session.

    WHAT: Creates a new AsyncSession from the module-level factory,
    yields it to the caller (typically a FastAPI dependency or a
    background task context manager), and closes it when the caller
    exits the context manager.

    WHY: This is the canonical way to obtain a database session in
    FastAPI. The `try/finally` guarantees the session is always closed
    even if an exception occurs during request processing, preventing
    connection leaks.

    USAGE:
        async with async_session() as session:
            result = await session.execute(select(...))

    IMPORTANT: This does NOT wrap in a transaction rollback on error —
    the caller is responsible for calling session.commit() or
    session.rollback() as appropriate. If an exception escapes the
    context manager without a rollback, the transaction will be rolled
    back by the session's cleanup logic in __aexit__.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
