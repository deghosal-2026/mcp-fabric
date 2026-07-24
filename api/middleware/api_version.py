"""Negotiates API version from the Accept / Accept-Version header or query parameter.

Defaults to version "1" when no version is specified.  Returns 406 Not
Acceptable for unsupported versions so callers get immediate feedback.
The negotiated version is set on request.state and echoed in the
Fabric-API-Version response header.
"""

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

SUPPORTED_API_VERSIONS = {"1"}


class APIVersionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        version = _parse_version(request)
        if version and version not in SUPPORTED_API_VERSIONS:
            return JSONResponse(
                status_code=406,
                content={
                    "error": "unsupported_api_version",
                    "message": f"API version '{version}' is not supported",
                    "supported_versions": sorted(SUPPORTED_API_VERSIONS),
                },
            )
        if version is None:
            version = "1"
        request.state.api_version = version
        response = await call_next(request)
        response.headers.setdefault("Fabric-API-Version", version)
        return response


VERSION_PATTERN = re.compile(r"version=([\w\.]+)")
VENDOR_PATTERN = re.compile(r"application/vnd\.fabric\.v?(\d+)\+json")


def _parse_version(request: Request) -> str | None:
    accept = request.headers.get("Accept", "")
    accept += "," + request.headers.get("Accept-Version", "")
    accept += "," + (request.query_params.get("api_version") or "")
    if match := VENDOR_PATTERN.search(accept):
        return match.group(1)
    if match := VERSION_PATTERN.search(accept):
        return match.group(1)
    return None
