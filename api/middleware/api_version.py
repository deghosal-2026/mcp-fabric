"""Negotiates API version from the Accept / Accept-Version header or query parameter.

Defaults to version "1" when no version is specified.  Returns 406 Not
Acceptable for unsupported versions so callers get immediate feedback.
The negotiated version is set on request.state and echoed in the
Fabric-API-Version response header.

REQUEST PROCESSING ORDER:
  1. Parse version from (in priority order):
     a. Vendor MIME type in Accept header: application/vnd.fabric.v1+json
     b. version= parameter in Accept or Accept-Version header
     c. api_version query parameter
  2. If version is not supported (not in SUPPORTED_API_VERSIONS), return 406
     immediately WITHOUT calling the next middleware/router.
  3. If no version is found, default to "1".
  4. Set request.state.api_version for downstream handlers.
  5. Call the next middleware/router.
  6. Set Fabric-API-Version response header (only if not already set by
     a route handler — setdefault ensures route-level overrides win).

HEADERS READ:
  - Accept: standard HTTP Accept header, checked for vendor MIME types
  - Accept-Version: non-standard header for explicit version requests

HEADERS WRITTEN:
  - Fabric-API-Version: echoes the negotiated version to the client

STATE SET ON REQUEST:
  - request.state.api_version (str): the resolved API version

FAILURE BEHAVIOR:
  - Returns 406 with body { "error": "unsupported_api_version", ... }
    listing supported versions. This is immediate — no further processing.
"""

import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

# Set of API version strings that the service supports.
# To add a new version, add it here and create the corresponding
# route prefix /v{version}/... The routes themselves are versioned
# via the router prefix (e.g., /v1/...), NOT by this middleware alone.
SUPPORTED_API_VERSIONS = {"1"}


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware: negotiate the API version from client request headers.

    WHAT: Intercepts every request to determine which API version the
    client wants to use. The version can be specified via:
      - Vendor MIME type: Accept: application/vnd.fabric.v2+json
      - Header parameter: Accept-Version: version=2
      - Query parameter: ?api_version=2

    WHY: Allows the API to evolve without breaking existing clients.
    Older clients continue to receive v1 responses while newer clients
    opt-in to v2. This middleware ensures the version is negotiated
    before any route handler logic runs.

    HOW: Uses regex patterns to extract the version from the Accept
    header (vendor MIME pattern first, then version= pattern), checks
    the query param as a fallback, and validates the version against
    SUPPORTED_API_VERSIONS before passing it downstream.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        version = _parse_version(request)
        if version and version not in SUPPORTED_API_VERSIONS:
            # Fail-fast: reject unsupported versions before any processing.
            # The response includes the list of supported versions so the
            # client can programmatically discover available versions.
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
        # setdefault so route handlers can override if needed
        response.headers.setdefault("Fabric-API-Version", version)
        return response


# Regex pattern to match "version=X.Y.Z" in Accept or Accept-Version headers.
# Captures the version string (alphanumeric, dots, underscores).
VERSION_PATTERN = re.compile(r"version=([\w\.]+)")

# Regex pattern to match vendor-specific MIME types like:
#   application/vnd.fabric.v1+json
#   application/vnd.fabric.v2+json
# Captures the numeric version (e.g., "1", "2").
VENDOR_PATTERN = re.compile(r"application/vnd\.fabric\.v?(\d+)\+json")


def _parse_version(request: Request) -> str | None:
    """Extract the requested API version from headers or query params.

    WHAT: Concatenates Accept header, Accept-Version header, and the
    api_version query parameter (separated by commas) and searches for
    a version pattern.

    WHY: Three sources give clients flexibility:
      - Vendor MIME types (Accept) are the REST-standard way to version
      - Accept-Version is a simpler non-standard header for non-browser clients
      - Query param is useful for debugging and testing

    RETURN: The version string (e.g., "1", "2") or None if no version
    was specified. None triggers the default version "1".

    PRIORITY: Vendor MIME pattern takes priority over version= pattern.
    The query parameter is the lowest priority since it is the least
    standard approach.
    """
    accept = request.headers.get("Accept", "")
    accept += "," + request.headers.get("Accept-Version", "")
    accept += "," + (request.query_params.get("api_version") or "")
    if match := VENDOR_PATTERN.search(accept):
        return match.group(1)
    if match := VERSION_PATTERN.search(accept):
        return match.group(1)
    return None
