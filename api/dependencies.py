"""FastAPI dependency injection functions for route handlers.

This module provides async generator functions and factory functions
that FastAPI's dependency injection system calls to resolve route
handler parameters. Each function creates a fresh instance scoped to
the current request.

ARCHITECTURE NOTES:
  - FastAPI dependencies are resolved per-request. Each call to
    get_db_session() creates a new session, commits/rolls back when
    the route handler finishes, and closes it.
  - Service dependencies (get_registry_service, etc.) compose on top
    of get_db_session using FastAPI's Depends() — FastAPI automatically
    injects the db session from the parent dependency into the child.
  - The lifecycle is: request → middleware → dependency resolution →
    route handler → response → dependency cleanup (yield resumes).
  - Depends() is called once per route per request, so every route
    handler gets its own clean service instance.

WHY DEPENDENCY INJECTION:
  - Testability: services can be mocked by overriding dependencies
    during tests.
  - Separation of concerns: route handlers don't create or manage
    service lifecycle.
  - Scope control: each request gets a fresh session, preventing
    cross-request state leaks.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.mcp import MCPClient
from api.services.approval_service import ApprovalService
from api.services.auth_service import AuthService
from api.services.capability_service import CapabilityService
from api.services.pack_service import PackService
from api.services.policy_service import PolicyService
from api.services.registry_service import RegistryService
from api.services.resource_service import ResourceService


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Create and yield an async SQLAlchemy session from the app's engine.

    WHAT: Reads the db_engine from the FastAPI application state (set
    during lifespan startup), creates a new async_sessionmaker, opens
    a session, yields it to the route handler, and closes it when the
    handler completes.

    WHY: Unlike api/database.py's module-level factory, this dependency
    uses the engine created and instrumented in main.py's lifespan.
    This ensures that OpenTelemetry instrumentation attached in the
    lifespan is active on every session.

    IMPORTANT: expiring_on_commit=False — ORM objects remain usable
    after the session commits, which is needed when building response
    schemas that reference related objects.
    """
    engine = request.app.state.db_engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


async def get_registry_service(
    db: AsyncSession = Depends(get_db_session),
) -> RegistryService:
    """Dependency: creates a RegistryService with an MCPClient.

    WHAT: Instantiates RegistryService with the database session and a
    new MCPClient. The MCPClient is created fresh per request because
    it holds transient connection state (SSE streams for MCP servers).

    WHY: RegistryService is the core orchestrator — it manages MCP
    server registrations, capability lookups, and tool routing.
    """
    client = MCPClient()
    return RegistryService(db=db, mcp_client=client)


async def get_policy_service(
    db: AsyncSession = Depends(get_db_session),
) -> PolicyService:
    """Dependency: creates a PolicyService.

    WHAT: Instantiates PolicyService with the database session.

    WHY: PolicyService manages OPA Rego policy lifecycle — CRUD for
    policies, evaluation requests against OPA. It does not need
    MCPClient since policy evaluation is a separate domain.
    """
    return PolicyService(db=db)


async def get_approval_service(
    db: AsyncSession = Depends(get_db_session),
) -> ApprovalService:
    """Dependency: creates an ApprovalService.

    WHAT: Instantiates ApprovalService with the database session.

    WHY: ApprovalService manages the human-in-the-loop approval
    workflow — creating approval requests, checking status, and
    processing approvals/rejections. It works with the approval
    database table only.
    """
    return ApprovalService(db=db)


async def get_pack_service(
    db: AsyncSession = Depends(get_db_session),
) -> PackService:
    """Dependency: creates a PackService.

    WHAT: Instantiates PackService with the database session.

    WHY: PackService manages tool packs — bundles of related MCP
    capabilities that can be installed, versioned, and shared as a
    unit. Packs reference capabilities but have their own CRUD cycle.
    """
    return PackService(db=db)


async def get_auth_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuthService:
    """Dependency: creates an AuthService.

    WHAT: Instantiates AuthService with the database session.

    WHY: AuthService handles JWT token issuance (login), validation,
    and admin session management. It uses the database for storing
    admin session records and API key hashes.
    """
    return AuthService(db=db)


async def get_capability_service(
    db: AsyncSession = Depends(get_db_session),
) -> CapabilityService:
    """Dependency: creates a CapabilityService.

    WHAT: Instantiates CapabilityService with the database session.

    WHY: CapabilityService manages capability definitions, mappings,
    alias resolution, deprecation lifecycle, and the schema-digest
    mapping review workflow (get_stale_mappings / review_mapping).
    This dependency is shared across admin.py and capabilities.py
    route handlers, providing a single injection point for testing.
    """
    return CapabilityService(db=db)


async def get_resource_service(
    db: AsyncSession = Depends(get_db_session),
) -> ResourceService:
    return ResourceService(db=db)
