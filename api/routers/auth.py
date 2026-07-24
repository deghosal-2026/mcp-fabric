from fastapi import APIRouter, HTTPException

from api.schemas.auth import LoginRequest, TokenResponse
from api.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
) -> TokenResponse:
    svc = AuthService()
    if body.username == "admin" and svc.verify_password(
        body.password,
        svc.hash_password("admin"),
    ):
        token = svc.create_token(
            subject="admin",
            token_type="admin",
            role="admin",
        )
        return TokenResponse(token=token)
    raise HTTPException(
        status_code=401,
        detail={"error": "invalid_credentials", "message": "Invalid username or password"},
    )


@router.post("/connect")
async def connect_agent(
    body: LoginRequest,
) -> TokenResponse:
    svc = AuthService()
    token = svc.create_token(
        subject=body.username,
        token_type="agent",
        agent_class=body.username,
        role="agent",
    )
    return TokenResponse(token=token)
