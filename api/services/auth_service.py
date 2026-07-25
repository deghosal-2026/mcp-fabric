"""Authentication and authorization for MCP Fabric.

Covers agent identity lifecycle (create, rotate, revoke, capability
surface) and admin authentication (login, MFA, sessions, password
reset, bootstrap).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.admin import AdminUser
from api.models.agent import AgentClass, AgentClassPack, AgentIdentity
from api.models.capability import Capability
from api.schemas.agent import (
    AgentConnectResponse,
    AgentIdentityCreate,
    AgentIdentityResponse,
)
from api.schemas.auth import (
    LoginRequest,
    MFASetupResponse,
    TokenResponse,
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
PASSWORD_MIN_LENGTH = 8


def _utcnow() -> datetime:
    """Return the current UTC datetime with tzinfo stripped."""
    return datetime.now(UTC).replace(tzinfo=None)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid, expired, or fails signature verification."""


class AuthenticationError(Exception):
    """Base exception for authentication failures (invalid credentials, account issues)."""


class AccountLockedError(AuthenticationError):
    """Raised when an admin account is temporarily locked due to too many failed attempts."""


class PasswordPolicyError(AuthenticationError):
    """Raised when a password fails to meet minimum complexity requirements."""


class MFARequiredError(AuthenticationError):
    """Raised when MFA verification is required but not yet completed."""


class BootstrapError(AuthenticationError):
    """Raised when first-admin bootstrap is attempted but an admin already exists."""


class AuthService:
    """Authentication and authorization — agent identity lifecycle and admin auth."""

    def __init__(
        self,
        db: AsyncSession | None = None,
        secret_key: str | None = None,
        testing_mode: bool = False,
    ):
        self.db = db
        self.secret = secret_key or settings.secret_key
        self.testing_mode = testing_mode
        self._test_sessions: dict[str, str] = {}

    # ── Agent Identity Management ──────────────────────────────────────

    def create_token(
        self,
        subject: str,
        token_type: str = "agent",
        agent_class: str | None = None,
        role: str = "agent",
    ) -> str:
        """Create a signed JWT token for the given subject and role."""
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
        """Validate and decode a JWT token. Raises InvalidTokenError on failure."""
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
        """Hash a plaintext password using bcrypt and return the encoded hash."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def _generate_agent_token(self) -> str:
        """Generate a random agent token with an fcp_ prefix."""
        token = "fcp_" + uuid4().hex + uuid4().hex
        return token

    async def create_agent_identity(
        self,
        params: AgentIdentityCreate,
    ) -> AgentIdentityResponse:
        """Create a new agent identity with a generated token and return the raw token once."""
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(
            select(AgentClass).where(AgentClass.id == params.agent_class_id)
        )
        if result.scalar_one_or_none() is None:
            raise ValueError(f"Agent class {params.agent_class_id} not found")

        raw_token = self._generate_agent_token()
        token_hash = self.hash_password(raw_token)
        token_prefix = raw_token[:10]

        identity = AgentIdentity(
            name=params.name,
            agent_class_id=params.agent_class_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            status="active",
            rate_limit_per_min=params.rate_limit_per_min,
            expires_at=params.expires_at,
        )
        self.db.add(identity)
        await self.db.commit()
        await self.db.refresh(identity)

        return AgentIdentityResponse(
            id=identity.id,
            name=identity.name,
            agent_class_id=identity.agent_class_id,
            token_prefix=identity.token_prefix,
            status=identity.status or "active",
            rate_limit_per_min=identity.rate_limit_per_min or 100,
            expires_at=identity.expires_at,
            created_at=identity.created_at,
            token=raw_token,
        )

    async def rotate_agent_token(self, identity_id: UUID) -> AgentIdentityResponse:
        """Rotate the token for an active agent identity and return the new raw token."""
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(
            select(AgentIdentity).where(AgentIdentity.id == identity_id)
        )
        identity = result.scalar_one_or_none()
        if identity is None:
            raise ValueError(f"Agent identity {identity_id} not found")
        if identity.status != "active":
            raise ValueError(f"Agent identity {identity_id} is not active")

        raw_token = self._generate_agent_token()
        new_hash = self.hash_password(raw_token)

        identity.token_hash = new_hash
        identity.token_prefix = raw_token[:10]
        await self.db.commit()
        await self.db.refresh(identity)

        return AgentIdentityResponse(
            id=identity.id,
            name=identity.name,
            agent_class_id=identity.agent_class_id,
            token_prefix=identity.token_prefix,
            status=identity.status or "active",
            rate_limit_per_min=identity.rate_limit_per_min or 100,
            expires_at=identity.expires_at,
            created_at=identity.created_at,
            token=raw_token,
        )

    async def revoke_agent_token(self, identity_id: UUID) -> None:
        """Revoke an agent identity, preventing further token usage."""
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(
            select(AgentIdentity).where(AgentIdentity.id == identity_id)
        )
        identity = result.scalar_one_or_none()
        if identity is None:
            raise ValueError(f"Agent identity {identity_id} not found")
        identity.status = "revoked"
        identity.revoked_at = _utcnow()
        await self.db.commit()

    async def get_agent_capability_surface(
        self,
        identity_id: UUID,
    ) -> AgentConnectResponse:
        """Return the capability surface for an active agent identity."""

        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(
            select(AgentIdentity).where(AgentIdentity.id == identity_id)
        )
        identity = result.scalar_one_or_none()
        if identity is None:
            raise ValueError(f"Agent identity {identity_id} not found")
        if identity.status != "active":
            raise ValueError(f"Agent identity {identity_id} is {identity.status}")

        capabilities: list[str] = []
        class_packs = await self.db.execute(
            select(AgentClassPack).where(
                AgentClassPack.agent_class_id == identity.agent_class_id
            )
        )
        from api.models.agent import PackAssignment

        for acp in class_packs.scalars().all():
            assignments = await self.db.execute(
                select(PackAssignment).where(PackAssignment.pack_id == acp.pack_id)
            )
            for pa in assignments.scalars().all():
                cap = await self.db.get(Capability, pa.capability_id)
                if cap and cap.name not in capabilities:
                    capabilities.append(cap.name)

        return AgentConnectResponse(
            agent_id=identity.id,
            agent_class=identity.agent_class.name,
            capability_surface=capabilities,
        )

    async def validate_agent_token_db(self, raw_token: str) -> AgentIdentity | None:
        """Look up an agent identity by token prefix and verify the token hash."""

        if self.db is None:
            raise RuntimeError("AuthService requires db")
        prefix = raw_token[:10]
        result = await self.db.execute(
            select(AgentIdentity).where(
                AgentIdentity.token_prefix == prefix,
                AgentIdentity.status == "active",
            )
        )
        for identity in result.scalars().all():
            if identity.token_hash and self.verify_password(raw_token, identity.token_hash):
                if identity.expires_at and identity.expires_at < _utcnow():
                    continue
                if identity.revoked_at:
                    continue
                return identity
        return None

    # ── Admin Authentication ──────────────────────────────────────────

    async def first_admin_bootstrap(
        self,
        username: str,
        email: str,
        password: str,
    ) -> TokenResponse:
        """Create the first admin user if none exists and return a JWT token."""
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        self._enforce_password_policy(password)
        existing = await self.db.execute(
            select(AdminUser).where(AdminUser.role == "admin")
        )
        if existing.scalar_one_or_none() is not None:
            raise BootstrapError("An admin user already exists")

        admin = AdminUser(
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            role="admin",
            status="active",
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)

        token = self.create_token(
            subject=str(admin.id),
            token_type="admin",
            role="admin",
        )
        return TokenResponse(
            token=token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        )

    async def admin_login(self, params: LoginRequest) -> TokenResponse:
        """Authenticate an admin user, enforce lockout, and return a JWT token on success."""
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.username == params.username)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            raise AuthenticationError("Invalid username or password")
        if admin.status != "active":
            raise AuthenticationError("Account is not active")

        if admin.locked_until and admin.locked_until > _utcnow():
            raise AccountLockedError("Account is temporarily locked")

        if not self.verify_password(params.password, admin.password_hash):
            attempts = (admin.failed_attempts or 0) + 1
            admin.failed_attempts = attempts
            if attempts >= MAX_LOGIN_ATTEMPTS:
                admin.locked_until = _utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            await self.db.commit()
            raise AuthenticationError("Invalid username or password")

        admin.failed_attempts = 0
        admin.locked_until = None
        admin.last_login_at = _utcnow()
        await self.db.commit()

        return TokenResponse(
            token=self.create_token(
                subject=str(admin.id),
                token_type="admin",
                role=admin.role,
            ),
            token_type="bearer",
            expires_in=28800,
        )

    async def mfa_setup(self, admin_id: UUID) -> MFASetupResponse:
        """Generate a TOTP secret, provisioning URI, and recovery codes for MFA setup."""
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            raise AuthenticationError("Admin not found")

        import pyotp

        secret = pyotp.random_base32()
        issuer = settings.jwt_issuer or "mcp-fabric"
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=admin.username, issuer_name=issuer
        )

        import base64

        qr_code = base64.b64encode(uri.encode()).decode()

        recovery_codes = [secrets.token_hex(6) for _ in range(8)]
        recovery_hashes = [hashlib.sha256(c.encode()).hexdigest() for c in recovery_codes]
        admin.recovery_codes = recovery_hashes
        await self.db.commit()

        return MFASetupResponse(
            secret=secret,
            qr_code=qr_code,
            recovery_codes=recovery_codes,
            setup_token=uuid4().hex,
        )

    async def mfa_verify_setup(self, admin_id: UUID, secret: str, code: str) -> bool:
        """Verify a TOTP code during MFA enrollment and persist the secret on success."""
        if self.db is None:
            raise RuntimeError("AuthService requires db")

        import pyotp

        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            return False

        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            return False

        admin.mfa_secret = secret
        admin.mfa_enabled = True
        await self.db.commit()
        return True

    def mfa_verify(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the stored MFA secret without database access."""
        import pyotp

        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    async def create_admin_session(self, admin_id: UUID) -> str:
        """Create an admin session in Redis (or in-memory for testing).

        Returns the session token.
        """
        session_token = uuid4().hex + uuid4().hex
        if self.testing_mode:
            self._test_sessions[session_token] = str(admin_id)
            return session_token
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)
            await r.setex(
                f"admin:session:{session_token}",
                settings.admin_session_ttl_hours * 3600,
                str(admin_id),
            )
            await r.aclose()
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_session_store_failed")
        return session_token

    async def validate_admin_session(self, session_token: str) -> str | None:
        """Look up an admin session token and return the admin ID, or None if invalid."""
        if self.testing_mode:
            return self._test_sessions.get(session_token)
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            admin_id = await r.get(f"admin:session:{session_token}")
            await r.aclose()
            return admin_id
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_session_lookup_failed")
            return None

    async def logout_admin_session(self, session_token: str) -> None:
        """Delete an admin session from Redis (or in-memory for testing)."""
        if self.testing_mode:
            self._test_sessions.pop(session_token, None)
            return
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)
            await r.delete(f"admin:session:{session_token}")
            await r.aclose()
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_session_delete_failed")

    async def admin_password_reset(
        self,
        admin_id: UUID,
        old_password: str,
        new_password: str,
    ) -> None:
        """Reset an admin password after verifying the old password.

        Enforces policy and history checks.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        self._enforce_password_policy(new_password)
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            raise AuthenticationError("Admin not found")
        if not self.verify_password(old_password, admin.password_hash):
            raise AuthenticationError("Current password is incorrect")

        history = admin.password_history or []
        for past_hash in history[-5:]:
            if self.verify_password(new_password, past_hash):
                raise PasswordPolicyError("Password has been used recently")

        history.append(admin.password_hash)
        admin.password_hash = self.hash_password(new_password)
        admin.password_history = history[-10:]
        await self.db.commit()

    async def _store_reset_token(self, admin_id: UUID) -> str:
        """Generate and store a password reset token in Redis (valid for 30 min)."""
        token = uuid4().hex + uuid4().hex
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)
            await r.setex(f"admin:reset:{token}", 1800, str(admin_id))
            await r.aclose()
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_reset_token_store_failed")
        return token

    async def _consume_reset_token(self, token: str) -> UUID | None:
        """Look up and delete a reset token, returning the admin_id if valid."""
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            admin_id = await r.get(f"admin:reset:{token}")
            if admin_id:
                await r.delete(f"admin:reset:{token}")
            await r.aclose()
            return UUID(admin_id) if admin_id else None
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_reset_token_consume_failed")
            return None

    async def complete_password_reset(self, token: str, new_password: str) -> None:
        """Complete a password reset using a reset token, bypassing old-password check."""
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        self._enforce_password_policy(new_password)
        admin_id = await self._consume_reset_token(token)
        if admin_id is None:
            raise AuthenticationError("Invalid or expired reset token")
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            raise AuthenticationError("Admin not found")

        history = admin.password_history or []
        for past_hash in history[-5:]:
            if self.verify_password(new_password, past_hash):
                raise PasswordPolicyError("Password has been used recently")

        history.append(admin.password_hash)
        admin.password_hash = self.hash_password(new_password)
        admin.password_history = history[-10:]
        await self.db.commit()

    def _enforce_password_policy(self, password: str) -> None:
        """Validate password meets minimum length, uppercase, lowercase, and digit requirements."""
        if len(password) < PASSWORD_MIN_LENGTH:
            raise PasswordPolicyError(
                f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
            )
        if not any(c.isupper() for c in password):
            raise PasswordPolicyError("Password must contain an uppercase letter")
        if not any(c.islower() for c in password):
            raise PasswordPolicyError("Password must contain a lowercase letter")
        if not any(c.isdigit() for c in password):
            raise PasswordPolicyError("Password must contain a digit")
