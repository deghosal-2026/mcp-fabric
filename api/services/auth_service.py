"""Authentication and authorization for MCP Fabric.

Covers agent identity lifecycle (create, rotate, revoke, capability
surface) and admin authentication (login, MFA, sessions, password
reset, bootstrap).

Architectural notes:
  - Two distinct auth domains coexist in this service:
    1. AGENT auth: token-based (fcp_ prefix), used by MCP agents
       connecting to the fabric. Tokens are hashed with bcrypt.
    2. ADMIN auth: JWT + optional TOTP MFA + Redis-backed sessions.
  - Redis is used for admin sessions and password reset tokens.
    When Redis is unavailable, session operations degrade gracefully
    (log warning, return None) — they do NOT crash the service.
  - In testing_mode, Redis is bypassed entirely with in-memory dicts.
  - All datetimes are naive UTC for cross-DB compatibility.
  - Password history (last 10 hashes) prevents password reuse.
  - Account lockout after MAX_LOGIN_ATTEMPTS failed attempts.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.admin import AdminUser
from api.models.agent import AgentClass, AgentClassPack, AgentIdentity
from api.models.capability import Capability
from api.schemas.admin import AdminUserInvite, AdminUserResponse, AdminUserUpdate
from api.schemas.agent import (
    AgentConnectResponse,
    AgentIdentityCreate,
    AgentIdentityResponse,
)
from api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MFASetupResponse,
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
PASSWORD_MIN_LENGTH = 8


def _utcnow() -> datetime:
    """Return the current UTC datetime with tzinfo stripped for cross-DB compatibility.

    WHY: SQLite stores TIMESTAMP without timezone. Stripping tzinfo ensures
    consistent comparison against stored naive-UTC datetimes from the DB.
    """
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
    """Authentication and authorization — agent identity lifecycle and admin auth.

    Depends on:
      - AsyncSession (optional — some methods are stateless JWT operations)
      - Redis (optional — degrades gracefully when unavailable)
      - secret_key from settings for JWT signing

    Used by: API route handlers for login, agent registration, admin management.

    Architecture notes:
      - The db parameter is Optional because some methods (create_token,
        validate_token, hash_password, verify_password) are pure functions
        of their inputs and don't need database access. This avoids forcing
        callers to provide a DB session for token operations.
      - testing_mode replaces Redis with dicts, enabling tests without
        a running Redis instance.
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        secret_key: str | None = None,
        testing_mode: bool = False,
    ):
        self.db = db
        self.secret = secret_key or settings.secret_key
        self.testing_mode = testing_mode
        # In-memory session store used only when testing_mode=True.
        self._test_sessions: dict[str, str] = {}

    # ── Agent Identity Management ──────────────────────────────────────

    def create_token(
        self,
        subject: str,
        token_type: str = "agent",
        agent_class: str | None = None,
        role: str = "agent",
    ) -> str:
        """Create a signed JWT token for the given subject and role.

        WHY: Both agents and admins receive JWTs after authentication.
        The subject is typically the user/agent UUID, and the type/role
        claims determine what the token authorizes.

        Uses HS256 (symmetric HMAC-SHA256) with the configured secret key.
        The token includes standard claims: sub, iat, exp, iss, aud.
        Custom claims: type (agent|admin), role, agent_class.

        RETURN: The encoded JWT string.
        """
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
        return jwt.encode(payload, self.secret, algorithm=ALGORITHM)  # type: ignore[no-any-return]

    def validate_token(self, token: str) -> dict[str, Any]:
        """Validate and decode a JWT token.

        WHY: Middleware and route guards need to verify incoming JWTs.
        Validates signature, expiration, audience, and issuer.

        RAISES: InvalidTokenError if the token is expired, malformed,
        or fails signature verification.
        RETURN: The decoded payload dict.
        """
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
        return payload  # type: ignore[no-any-return]

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt and return the encoded hash.

        WHY: Never store plaintext passwords. bcrypt includes a salt
        and is deliberately slow to resist brute-force attacks.
        The hash is self-contained (includes algorithm, cost, salt, hash).
        """
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a plaintext password against a bcrypt hash.

        WHY: Used during login (admin) and token validation (agent).
        bcrypt.checkpw handles salt extraction from the stored hash.
        """
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def _generate_agent_token(self) -> str:
        """Generate a random agent token with an fcp_ prefix.

        WHY: Agent tokens are bearer tokens sent with every request.
        The fcp_ prefix helps identify the token type in logs and
        makes the token distinguishable from other random strings.

        Uses two uuid4() hex strings concatenated for 64 hex chars
        (256 bits of entropy). The prefix is for identification only;
        security comes from the total entropy.
        """
        token = "fcp_" + uuid4().hex + uuid4().hex
        return token

    async def create_agent_identity(
        self,
        params: AgentIdentityCreate,
    ) -> AgentIdentityResponse:
        """Create a new agent identity with a generated token.

        WHY: Admin user journey — register a new agent with a specific class.

        The token is hashed with bcrypt before storage. Only the hash and
        a 10-character prefix are stored. The raw token is returned ONCE
        in the response and cannot be retrieved later (matching the security
        pattern of "show once, then forget").

        RAISES: ValueError if the agent_class_id does not exist.
        SIDE EFFECTS: Persists AgentIdentity row.
        RETURN: AgentIdentityResponse including the raw token (one-time only).
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(
            select(AgentClass).where(AgentClass.id == params.agent_class_id)
        )
        if result.scalar_one_or_none() is None:
            raise ValueError(f"Agent class {params.agent_class_id} not found")

        raw_token = self._generate_agent_token()
        token_hash = self.hash_password(raw_token)
        # Store only the first 10 chars as a hint for which bcrypt hash to
        # try first during validation. This avoids scanning ALL hashes.
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
        """Rotate the token for an active agent identity.

        WHY: Security best practice — periodic token rotation or
        response to a suspected compromise.

        Generates a new token, bcrypt-hashes it, and updates the identity.
        The new raw token is returned once, same as create.
        The old token immediately becomes invalid.

        RAISES: ValueError if the identity is not found or not active.
        SIDE EFFECTS: Updates token_hash and token_prefix on the identity.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(select(AgentIdentity).where(AgentIdentity.id == identity_id))
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
        """Revoke an agent identity, preventing further token usage.

        WHY: Security response — disable a compromised agent or
        decommission an agent identity.

        Sets status to 'revoked' and records the revocation timestamp.
        The token_prefix-based lookup in validate_agent_token_db will
        skip identities with revoked_at set.

        RAISES: ValueError if the identity is not found.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(select(AgentIdentity).where(AgentIdentity.id == identity_id))
        identity = result.scalar_one_or_none()
        if identity is None:
            raise ValueError(f"Agent identity {identity_id} not found")
        identity.status = "revoked"
        identity.revoked_at = _utcnow()
        await self.db.commit()

    async def list_agent_identities(
        self,
        agent_class_id: UUID,
    ) -> list[AgentIdentityResponse]:
        """List all agent identities for a given agent class.

        WHY: Admin UI — browse agents within a class.
        Note: token field is always None in list responses for security.
        The raw token is only returned on create and rotate.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db for identity management")
        result = await self.db.execute(
            select(AgentIdentity).where(AgentIdentity.agent_class_id == agent_class_id)
        )
        identities = result.scalars().all()
        return [
            AgentIdentityResponse(
                id=ident.id,
                name=ident.name,
                agent_class_id=ident.agent_class_id,
                token_prefix=ident.token_prefix,
                status=ident.status or "active",
                rate_limit_per_min=ident.rate_limit_per_min or 100,
                expires_at=ident.expires_at,
                created_at=ident.created_at,
                token=None,
            )
            for ident in identities
        ]

    async def get_agent_capability_surface(
        self,
        identity_id: UUID,
    ) -> AgentConnectResponse:
        """Return the capability surface for an active agent identity.

        WHY: Agent connect flow — when an agent connects, it receives
        its capability surface (the list of capabilities it can invoke).
        This is computed from the agent class -> packs -> capabilities
        chain: identity belongs to a class, class has packs, packs have
        capabilities.

        This is a moderately expensive operation (multiple queries).
        For high-frequency connect flows, consider caching the capability
        surface per agent class.

        RAISES: ValueError if the identity is not found or not active.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AgentIdentity).where(AgentIdentity.id == identity_id))
        identity = result.scalar_one_or_none()
        if identity is None:
            raise ValueError(f"Agent identity {identity_id} not found")
        if identity.status != "active":
            raise ValueError(f"Agent identity {identity_id} is {identity.status}")

        # Walk the class -> packs -> capabilities chain.
        capabilities: list[str] = []
        class_packs = await self.db.execute(
            select(AgentClassPack).where(AgentClassPack.agent_class_id == identity.agent_class_id)
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
        """Look up an agent identity by token prefix and verify the token hash.

        WHY: Middleware — validates incoming agent bearer tokens.
        Uses the first 10 chars of the token (prefix) to narrow the search
        to a small subset of identities, then bcrypt-verifies against each.

        This two-step approach avoids bcrypt overhead on every single
        identity: we first filter by prefix (fast, indexed), then only
        run bcrypt on the candidates that match the prefix.

        Checks: status=active, not expired, not revoked.
        RETURN: The AgentIdentity if valid, None otherwise.
        """
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
                # Expired tokens and revoked tokens should not validate.
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
    ) -> LoginResponse:
        """Create the first admin user if none exists and return a JWT token.

        WHY: Initial system setup — the first admin is created through
        a special bootstrap endpoint (no existing auth required).
        After the first admin exists, additional admins are invited
        through invite_admin() which requires existing admin credentials.

        RAISES: BootstrapError if an admin user already exists.
        SIDE EFFECTS: Creates AdminUser row, issues JWT token.
        RETURN: TokenResponse with the JWT and expiry info.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        self._enforce_password_policy(password)
        existing = await self.db.execute(select(AdminUser).where(AdminUser.role == "admin"))
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
        return LoginResponse(
            token=token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            user=self._admin_to_response(admin),
            mfa_required=False,
        )

    async def admin_login(self, params: LoginRequest) -> LoginResponse:
        """Authenticate an admin user, enforce lockout, and return a JWT token on success.

        WHY: Admin UI login flow — validates credentials, checks lockout,
        resets failed attempts on success, issues JWT.

        Lockout flow:
          1. Check if account is locked (locked_until > now).
          2. Verify password. On failure, increment failed_attempts.
          3. If failed_attempts >= MAX_LOGIN_ATTEMPTS, set locked_until.
          4. On success, reset failed_attempts and locked_until.

        RAISES:
          - AuthenticationError for invalid credentials or inactive account.
          - AccountLockedError when the account is in a lockout window.
        SIDE EFFECTS: Updates failed_attempts, locked_until, last_login_at.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.username == params.username)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            # Generic error message avoids revealing whether the username exists.
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
            # Commit the failed attempt count and lockout (if triggered).
            await self.db.commit()
            raise AuthenticationError("Invalid username or password")

        # Successful login: reset lockout state and record login timestamp.
        admin.failed_attempts = 0
        admin.locked_until = None
        admin.last_login_at = _utcnow()
        await self.db.commit()

        return LoginResponse(
            token=self.create_token(
                subject=str(admin.id),
                token_type="admin",
                role=admin.role,
            ),
            token_type="bearer",
            expires_in=28800,
            user=self._admin_to_response(admin),
            mfa_required=False,
        )

    def _admin_to_response(self, admin: AdminUser) -> AdminUserResponse:
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=bool(admin.mfa_enabled),
            status=admin.status or "active",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )

    async def mfa_setup(self, admin_id: UUID) -> MFASetupResponse:
        """Generate a TOTP secret, provisioning URI, and recovery codes for MFA setup.

        WHY: Admin user journey — enabling MFA for their account.
        Generates:
          - A random base32 TOTP secret
          - A provisioning URI (for QR code generation in the UI)
          - 8 recovery codes (hashed with SHA-256 for storage)
        The recovery codes are returned in plain text ONCE for the user to save.
        Only the SHA-256 hashes are stored in the database.

        SIDE EFFECTS: Stores recovery code hashes in the admin record.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            raise AuthenticationError("Admin not found")

        import pyotp

        secret = pyotp.random_base32()
        issuer = settings.jwt_issuer or "mcp-fabric"
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=admin.username, issuer_name=issuer)

        # base64-encode the URI so the frontend can render it as an inline image
        # without needing a separate endpoint for the QR code.
        import base64

        qr_code = base64.b64encode(uri.encode()).decode()

        recovery_codes = [secrets.token_hex(6) for _ in range(8)]
        # Store SHA-256 hashes of recovery codes, NOT the plain text.
        # The plain codes are returned once in the setup response.
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
        """Verify a TOTP code during MFA enrollment and persist the secret on success.

        WHY: Admin user journey — confirms the TOTP setup by validating
        a code generated by the authenticator app. Only on success is
        the MFA secret persisted and MFA enabled.

        RETURN: True if the code is valid, False otherwise.
        RAISES: Does NOT raise on invalid code — returns False so the
        caller can distinguish "invalid code" from "admin not found."
        Note: admin-not-found also returns False (no error distinction).
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")

        import pyotp

        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            return False

        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return False

        admin.mfa_secret = secret
        admin.mfa_enabled = True
        await self.db.commit()
        return True

    async def mfa_verify_session(self, admin_id: UUID, code: str) -> bool:
        """Verify a TOTP code during login and confirm the admin's MFA secret exists.

        WHY: Login flow — after password verification, the admin provides
        a TOTP code. This method loads the admin's MFA secret from the DB
        and validates the code. Replaces direct DB queries in the route handler.

        RETURN: True if the code is valid and MFA is configured, False otherwise.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None or not admin.mfa_secret:
            return False
        return self.mfa_verify(admin.mfa_secret, code)

    async def mfa_recover(self, admin_id: UUID, recovery_code: str) -> bool:
        """Consume a recovery code for an admin, bypassing MFA for this session.

        WHY: Login flow — admin who lost their authenticator device can
        use a pre-generated recovery code. Codes are stored as SHA-256
        hashes and consumed on first use (one-time use).

        SIDE EFFECTS: Removes the used recovery code hash from the admin's
        recovery_codes list and commits to DB.

        RETURN: True if the recovery code was valid and consumed, False otherwise.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None or not admin.recovery_codes:
            return False
        code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()
        if code_hash not in admin.recovery_codes:
            return False
        admin.recovery_codes = [c for c in admin.recovery_codes if c != code_hash]
        await self.db.commit()
        return True

    def mfa_verify(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the stored MFA secret without database access.

        WHY: Login flow — after the admin provides their password,
        if MFA is enabled, they provide a TOTP code. This method
        validates the code against the secret (already loaded from DB).
        No database access needed, making it safe for high-frequency calls.
        """
        import pyotp

        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    async def create_admin_session(self, admin_id: UUID) -> str:
        """Create an admin session in Redis (or in-memory for testing).

        WHY: After successful MFA verification, a session is created
        so the admin doesn't need to re-authenticate on every request.
        Session data: admin_id, TTL from settings.

        Redis is used as a fast, distributed session store. When Redis
        is unavailable, the session token is still returned but won't
        be validated — the admin would need to re-login. This is a
        deliberate degrade-don't-fail pattern.

        RETURN: The session token string.
        """
        session_token = uuid4().hex + uuid4().hex
        if self.testing_mode:
            self._test_sessions[session_token] = str(admin_id)
            return session_token
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)  # type: ignore[no-untyped-call]
            await r.setex(
                f"admin:session:{session_token}",
                settings.admin_session_ttl_hours * 3600,
                str(admin_id),
            )
            await r.aclose()
        except Exception:
            # Redis failure is non-fatal: the session won't validate,
            # but we don't crash the login flow.
            from api.telemetry.logging import logger

            logger.exception("auth:redis_session_store_failed")
        return session_token

    async def validate_admin_session(self, session_token: str) -> str | None:
        """Look up an admin session token and return the admin ID, or None if invalid.

        WHY: Middleware — validates session tokens on authenticated requests.
        Checks Redis (or in-memory for testing).

        RETURN: Admin ID string if session is valid, None otherwise
        (expired, invalid, or Redis unavailable).
        """
        if self.testing_mode:
            return self._test_sessions.get(session_token)
        try:
            import redis.asyncio as aioredis

            # decode_responses=True ensures Redis returns strings, not bytes.
            r = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
            admin_id = await r.get(f"admin:session:{session_token}")
            await r.aclose()
            return admin_id  # type: ignore[no-any-return]
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_session_lookup_failed")
            return None

    async def logout_admin_session(self, session_token: str) -> None:
        """Delete an admin session from Redis (or in-memory for testing).

        WHY: Admin logout — invalidates the session token.
        Gracefully handles the case where the session doesn't exist.
        """
        if self.testing_mode:
            self._test_sessions.pop(session_token, None)
            return
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)  # type: ignore[no-untyped-call]
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

        WHY: Admin user journey — change their own password.
        Requires the current password for verification.

        Validates:
          - New password meets policy (length, complexity).
          - Old password is correct.
          - New password hasn't been used in the last 5 changes.

        SIDE EFFECTS: Updates password_hash, appends old hash to history.
        RAISES:
          - AuthenticationError if admin not found or old password wrong.
          - PasswordPolicyError if new password fails policy or was recently used.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        self._enforce_password_policy(new_password)
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            raise AuthenticationError("Admin not found")
        if not self.verify_password(old_password, admin.password_hash):
            raise AuthenticationError("Current password is incorrect")

        # Check the last 5 passwords to prevent reuse.
        history = admin.password_history or []
        for past_hash in history[-5:]:
            if self.verify_password(new_password, past_hash):
                raise PasswordPolicyError("Password has been used recently")

        history.append(admin.password_hash)
        admin.password_hash = self.hash_password(new_password)
        # Keep only the last 10 password hashes in history.
        admin.password_history = history[-10:]
        await self.db.commit()

    async def _store_reset_token(self, admin_id: UUID) -> str:
        """Generate and store a password reset token in Redis (valid for 30 min).

        WHY: "Forgot password" flow — generates a one-time token stored in
        Redis with a 30-minute TTL. The token is sent to the admin's email
        (by the caller) and consumed in complete_password_reset.

        Uses Redis (not the database) so that:
          - Tokens auto-expire via TTL.
          - No DB cleanup is needed.
          - Token storage doesn't require schema changes.

        RETURN: The reset token string.
        """
        token = uuid4().hex + uuid4().hex
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)  # type: ignore[no-untyped-call]
            await r.setex(f"admin:reset:{token}", 1800, str(admin_id))
            await r.aclose()
        except Exception:
            from api.telemetry.logging import logger

            logger.exception("auth:redis_reset_token_store_failed")
        return token

    async def _consume_reset_token(self, token: str) -> UUID | None:
        """Look up and delete a reset token, returning the admin_id if valid.

        WHY: One-time token consumption pattern. The token is deleted
        immediately on read, preventing replay attacks. If Redis is
        unavailable, returns None (expired/invalid behavior).

        RETURN: The admin UUID if the token is valid, None otherwise.
        """
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
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
        """Complete a password reset using a reset token, bypassing old-password check.

        WHY: "Forgot password" flow — the admin has received a reset token
        (via email) and provides a new password. Unlike admin_password_reset,
        this does NOT require the old password.

        The token is one-time-use (consumed by _consume_reset_token).
        Same policy checks as admin_password_reset apply.

        RAISES:
          - AuthenticationError if token is invalid/expired or admin not found.
          - PasswordPolicyError if the new password fails policy or was recently used.
        SIDE EFFECTS: Updates password_hash and history.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        self._enforce_password_policy(new_password)
        admin_id = await self._consume_reset_token(token)
        if admin_id is None:
            raise AuthenticationError("Invalid or expired reset token")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
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
        """Validate password meets minimum length, uppercase, lowercase, and digit requirements.

        WHY: Security policy enforcement — prevents weak passwords.
        Called at password creation and change time.
        The policy requires: 8+ chars, at least one uppercase, one lowercase, one digit.

        RAISES: PasswordPolicyError with a specific message for each failure.
        """
        if len(password) < PASSWORD_MIN_LENGTH:
            raise PasswordPolicyError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        if not any(c.isupper() for c in password):
            raise PasswordPolicyError("Password must contain an uppercase letter")
        if not any(c.islower() for c in password):
            raise PasswordPolicyError("Password must contain a lowercase letter")
        if not any(c.isdigit() for c in password):
            raise PasswordPolicyError("Password must contain a digit")

    # ── Admin User Management ─────────────────────────────────────────

    async def invite_admin(self, params: AdminUserInvite) -> AdminUserResponse:
        """Invite a new admin user.

        WHY: Admin user journey — existing admin invites a new team member.
        Generates a random temporary password (the invited admin would
        reset it on first login via the forgot-password flow).

        RAISES: ValueError if the email is already registered.
        SIDE EFFECTS: Creates AdminUser row with a temporary password.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        username = params.email.split("@")[0]
        result = await self.db.execute(select(AdminUser).where(AdminUser.email == params.email))
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Admin with email {params.email} already exists")
        temp_password = secrets.token_urlsafe(16)
        admin = AdminUser(
            username=username,
            email=params.email,
            password_hash=self.hash_password(temp_password),
            role=params.role,
            team_namespace=params.team_namespace,
            status="active",
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=bool(admin.mfa_enabled),
            status=admin.status or "active",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )

    async def list_admins(self) -> list[AdminUserResponse]:
        """List all admin users, newest first.

        WHY: Admin UI — user management dashboard.
        Note: Password hashes and MFA secrets are NOT included in the response.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))
        admins = result.scalars().all()
        return [
            AdminUserResponse(
                id=a.id,
                username=a.username,
                email=a.email,
                role=a.role,
                team_namespace=a.team_namespace,
                mfa_enabled=bool(a.mfa_enabled),
                status=a.status or "active",
                last_login_at=a.last_login_at,
                created_at=a.created_at,
            )
            for a in admins
        ]

    async def get_admin(self, admin_id: UUID) -> AdminUserResponse | None:
        """Get a single admin user by ID.

        WHY: Admin UI — view/edit a specific admin user's details.
        RETURN: AdminUserResponse or None if not found.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return None
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=bool(admin.mfa_enabled),
            status=admin.status or "active",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )

    async def update_admin(
        self,
        admin_id: UUID,
        params: AdminUserUpdate,
    ) -> AdminUserResponse | None:
        """Update an admin user's role and/or team namespace.

        WHY: Admin UI — super-admin updates another admin's permissions.
        Only role and team_namespace are updatable through this endpoint.
        Password changes go through admin_password_reset or complete_password_reset.

        RETURN: Updated AdminUserResponse or None if not found.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return None
        if params.role is not None:
            admin.role = params.role
        if params.team_namespace is not None:
            admin.team_namespace = params.team_namespace
        await self.db.commit()
        await self.db.refresh(admin)
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=bool(admin.mfa_enabled),
            status=admin.status or "active",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )

    async def deactivate_admin(self, admin_id: UUID) -> AdminUserResponse | None:
        """Deactivate an admin user (set status to 'inactive').

        WHY: Admin user management — disable an admin account without deleting it.
        Inactive admins cannot log in (checked in admin_login).
        This is reversible via unlock_admin.

        RETURN: Updated AdminUserResponse or None if not found.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return None
        admin.status = "inactive"
        await self.db.commit()
        await self.db.refresh(admin)
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=bool(admin.mfa_enabled),
            status=admin.status or "inactive",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )

    async def unlock_admin(self, admin_id: UUID) -> AdminUserResponse | None:
        """Unlock a deactivated or locked admin account.

        WHY: Admin user management — re-enable an account that was
        locked due to failed attempts or deactivated.
        Resets failed_attempts, clears locked_until, sets status to active.

        RETURN: Updated AdminUserResponse or None if not found.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return None
        admin.failed_attempts = 0
        admin.locked_until = None
        if admin.status != "active":
            admin.status = "active"
        await self.db.commit()
        await self.db.refresh(admin)
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=bool(admin.mfa_enabled),
            status=admin.status or "active",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )

    async def reset_admin_mfa(self, admin_id: UUID) -> AdminUserResponse | None:
        """Reset MFA configuration for an admin user.

        WHY: Admin user management — if an admin loses access to their
        authenticator app and recovery codes, a super-admin can reset
        their MFA, allowing them to re-enroll.

        Clears: mfa_secret, mfa_enabled, recovery_codes.
        RETURN: Updated AdminUserResponse or None if not found.
        """
        if self.db is None:
            raise RuntimeError("AuthService requires db")
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == admin_id))
        admin = result.scalar_one_or_none()
        if admin is None:
            return None
        admin.mfa_secret = None
        admin.mfa_enabled = False
        admin.recovery_codes = None
        await self.db.commit()
        await self.db.refresh(admin)
        return AdminUserResponse(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            role=admin.role,
            team_namespace=admin.team_namespace,
            mfa_enabled=False,
            status=admin.status or "active",
            last_login_at=admin.last_login_at,
            created_at=admin.created_at,
        )
