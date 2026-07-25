from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.mcp import MCPClient
from api.services.approval_service import ApprovalService
from api.services.auth_service import AuthService
from api.services.pack_service import PackService
from api.services.policy_service import PolicyService
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


async def get_policy_service(
    db: AsyncSession = Depends(get_db_session),
) -> PolicyService:
    return PolicyService(db=db)


async def get_approval_service(
    db: AsyncSession = Depends(get_db_session),
) -> ApprovalService:
    return ApprovalService(db=db)


async def get_pack_service(
    db: AsyncSession = Depends(get_db_session),
) -> PackService:
    return PackService(db=db)


async def get_auth_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuthService:
    return AuthService(db=db)
