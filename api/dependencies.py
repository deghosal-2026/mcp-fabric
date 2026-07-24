from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.mcp import MCPClient
from api.services.registry_service import RegistryService


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    engine = request.app.state.db_engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


async def get_registry_service(
    db: AsyncSession = Depends(get_db_session),
) -> RegistryService:
    client = MCPClient()
    return RegistryService(db=db, mcp_client=client)
