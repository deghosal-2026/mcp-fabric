"""FastAPI dependency injection utilities.

Provides reusable dependencies for API version negotiation,
request ID tracking, tenant scope extraction, and auth.
"""

import re
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def get_api_version(request: Request) -> str:
    """Extract API version from Accept header (defaults to v1)."""
    accept = request.headers.get("Accept", "")
    match = re.search(r"application/vnd\.fabric\.(v\d+)\+json", accept)
    if match:
        return match.group(1)
    return "v1"


def get_request_id(request: Request) -> str:
    """Return or generate a unique request ID, preferring Fabric-Request-Id header."""
    if not hasattr(request.state, "request_id"):
        request.state.request_id = request.headers.get("Fabric-Request-Id", str(uuid4()))
    return request.state.request_id


def get_tenant_scope(request: Request) -> str | None:
    """Extract tenant namespace from request state (set by auth middleware)."""
    return getattr(request.state, "tenant_namespace", None)


def _get_security() -> HTTPBearer:
    """Return the shared HTTPBearer instance (wrapped for Depends injection)."""
    return security


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials | None = Depends(_get_security),
) -> dict:
    """Authenticate and return the current agent from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "message": "Missing authorization header",
            },
        )
    return {"token": credentials.credentials}


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_get_security),
) -> dict:
    """Authenticate and return the current admin from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "message": "Missing authorization header",
            },
        )
    return {"token": credentials.credentials}
