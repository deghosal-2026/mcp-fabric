from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from api.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8


class InvalidTokenError(Exception):
    pass


class AuthService:
    def __init__(self, secret_key: str | None = None):
        self.secret = secret_key or settings.secret_key

    def create_token(
        self,
        subject: str,
        token_type: str = "agent",
        agent_class: str | None = None,
        role: str = "agent",
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "type": token_type,
            "role": role,
            "iat": now,
            "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }
        if agent_class:
            payload["agent_class"] = agent_class
        return jwt.encode(payload, self.secret, algorithm=ALGORITHM)

    def validate_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[ALGORITHM],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
            )
        except JWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        return payload

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
