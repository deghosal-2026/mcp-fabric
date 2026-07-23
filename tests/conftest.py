from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models import Base
from api.models.agent import AgentClass, CapabilityPack
from api.models.capability import Capability
from api.models.server import MCPServer, ServerTool

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def server(db_session: AsyncSession) -> MCPServer:
    """Fixture: create a test MCP server record."""
    srv = MCPServer(
        name="test-server",
        endpoint="https://example.com/mcp",
        owner_team="platform",
        labels=["production"],
    )
    db_session.add(srv)
    await db_session.commit()
    await db_session.refresh(srv)
    return srv


@pytest_asyncio.fixture
async def tool(server: MCPServer, db_session: AsyncSession) -> ServerTool:
    """Fixture: create a test tool record linked to the server."""
    t = ServerTool(
        server_id=server.id,
        tool_name="test_tool",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def capability(db_session: AsyncSession) -> Capability:
    """Fixture: create a test capability record."""
    cap = Capability(name="code:search", domain="code", description="Search code")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)
    return cap


@pytest_asyncio.fixture
async def agent_class(db_session: AsyncSession) -> AgentClass:
    """Fixture: create a test agent class record."""
    ac = AgentClass(name="agent:developer", description="Developer agent")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)
    return ac


@pytest_asyncio.fixture
async def pack(db_session: AsyncSession) -> CapabilityPack:
    """Fixture: create a test capability pack record."""
    p = CapabilityPack(name="test-pack", description="Test pack")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p
