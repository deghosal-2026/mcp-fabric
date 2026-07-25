"""Tests for AuthService: agent identity lifecycle, admin auth, MFA, sessions."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.admin import AdminUser
from api.models.agent import AgentIdentity
from api.schemas.agent import AgentIdentityCreate
from api.schemas.auth import LoginRequest
from api.services.auth_service import (
    AccountLockedError,
    AuthenticationError,
    AuthService,
    BootstrapError,
    InvalidTokenError,
    PasswordPolicyError,
)


class TestTokenBasics:
    def test_create_and_validate_token(self):
        svc = AuthService(testing_mode=True)
        token = svc.create_token(subject="test-agent", agent_class="agent:developer")
        payload = svc.validate_token(token)
        assert payload["sub"] == "test-agent"
        assert payload["agent_class"] == "agent:developer"

    def test_invalid_token_raises(self):
        svc = AuthService(testing_mode=True)
        with pytest.raises(InvalidTokenError):
            svc.validate_token("not-a-valid-token")

    def test_password_hashing(self):
        svc = AuthService()
        hashed = svc.hash_password("secure123")
        assert hashed != "secure123"
        assert svc.verify_password("secure123", hashed) is True
        assert svc.verify_password("wrong", hashed) is False

    def test_admin_token(self):
        svc = AuthService(testing_mode=True)
        token = svc.create_token(subject="admin-1", token_type="admin", role="admin")
        payload = svc.validate_token(token)
        assert payload["type"] == "admin"
        assert payload["role"] == "admin"


class TestAgentIdentityLifecycle:
    async def test_create_agent_identity(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(
                name="deploy-bot",
                agent_class_id=agent_class.id,
            )
        )
        assert identity.name == "deploy-bot"
        assert identity.agent_class_id == agent_class.id
        assert identity.token is not None
        assert identity.token.startswith("fcp_")
        assert identity.status == "active"

    async def test_create_identity_invalid_class(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        with pytest.raises(ValueError, match="Agent class"):
            await svc.create_agent_identity(AgentIdentityCreate(name="bot", agent_class_id=uuid4()))

    async def test_rotate_agent_token(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="rotate-me", agent_class_id=agent_class.id)
        )
        old_token = identity.token
        rotated = await svc.rotate_agent_token(identity.id)
        assert rotated.token != old_token
        assert rotated.token_prefix != identity.token_prefix

    async def test_rotate_rejects_revoked(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="rotate-revoked", agent_class_id=agent_class.id)
        )
        await svc.revoke_agent_token(identity.id)
        with pytest.raises(ValueError, match="not active"):
            await svc.rotate_agent_token(identity.id)

    async def test_revoke_agent_token(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="revoke-me", agent_class_id=agent_class.id)
        )
        await svc.revoke_agent_token(identity.id)
        result = await db_session.execute(
            select(AgentIdentity).where(AgentIdentity.id == identity.id)
        )
        ident = result.scalar_one()
        assert ident.status == "revoked"

    async def test_validate_agent_token_db(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="validate-me", agent_class_id=agent_class.id)
        )
        assert identity.token is not None
        found = await svc.validate_agent_token_db(identity.token)
        assert found is not None
        assert found.id == identity.id

    async def test_validate_agent_token_db_invalid(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        result = await svc.validate_agent_token_db("fcp_fake_token_that_does_not_exist")
        assert result is None

    async def test_validate_agent_token_db_expired(self, db_session: AsyncSession, agent_class):
        from datetime import UTC, datetime, timedelta

        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(
                name="expired-agent",
                agent_class_id=agent_class.id,
                expires_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        assert identity.token is not None
        found = await svc.validate_agent_token_db(identity.token)
        assert found is None


class TestAgentCapabilitySurface:
    async def test_capability_surface(self, db_session: AsyncSession, agent_class, capability):
        from api.models.agent import AgentClassPack, CapabilityPack, PackAssignment

        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="surf-test", agent_class_id=agent_class.id)
        )
        pack = CapabilityPack(name="test-pack")
        db_session.add(pack)
        await db_session.commit()
        await db_session.refresh(pack)
        db_session.add(PackAssignment(pack_id=pack.id, capability_id=capability.id))
        db_session.add(AgentClassPack(agent_class_id=agent_class.id, pack_id=pack.id))
        await db_session.commit()

        result = await svc.get_agent_capability_surface(identity.id)
        assert capability.name in result.capability_surface

    async def test_capability_surface_empty(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="surf-empty", agent_class_id=agent_class.id)
        )
        result = await svc.get_agent_capability_surface(identity.id)
        assert result.capability_surface == []

    async def test_capability_surface_not_found(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        with pytest.raises(ValueError, match="Agent identity"):
            await svc.get_agent_capability_surface(uuid4())

    async def test_capability_surface_revoked(self, db_session: AsyncSession, agent_class):
        svc = AuthService(db=db_session)
        identity = await svc.create_agent_identity(
            AgentIdentityCreate(name="surf-revoked", agent_class_id=agent_class.id)
        )
        await svc.revoke_agent_token(identity.id)
        with pytest.raises(ValueError, match="revoked"):
            await svc.get_agent_capability_surface(identity.id)


class TestFirstAdminBootstrap:
    async def test_bootstrap_creates_first_admin(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        result = await svc.first_admin_bootstrap(
            username="root", email="root@fabric.io", password="SecurePass1"
        )
        assert result.token is not None
        assert result.token_type == "bearer"

    async def test_bootstrap_rejects_duplicate(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="root", email="root@fabric.io", password="SecurePass1"
        )
        with pytest.raises(BootstrapError):
            await svc.first_admin_bootstrap(
                username="root2", email="root2@fabric.io", password="SecurePass2"
            )

    async def test_bootstrap_rejects_weak_password(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        with pytest.raises(PasswordPolicyError):
            await svc.first_admin_bootstrap(
                username="root", email="root@fabric.io", password="weak"
            )


class TestAdminLogin:
    async def test_admin_login_success(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await svc.admin_login(LoginRequest(username="admin", password="SecurePass1"))
        assert result.token is not None

    async def test_admin_login_wrong_password(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        with pytest.raises(AuthenticationError):
            await svc.admin_login(LoginRequest(username="admin", password="wrong"))

    async def test_admin_login_account_locked(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        for _ in range(5):
            with pytest.raises(AuthenticationError):
                await svc.admin_login(LoginRequest(username="admin", password="wrong"))
        with pytest.raises(AccountLockedError):
            await svc.admin_login(LoginRequest(username="admin", password="SecurePass1"))

    async def test_admin_login_not_found(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        with pytest.raises(AuthenticationError):
            await svc.admin_login(LoginRequest(username="ghost", password="anything"))


class TestAdminPasswordReset:
    async def test_password_reset_success(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()
        await svc.admin_password_reset(
            admin.id, old_password="SecurePass1", new_password="NewPass123"
        )
        login = await svc.admin_login(LoginRequest(username="admin", password="NewPass123"))
        assert login.token is not None

    async def test_password_reset_wrong_old(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()
        with pytest.raises(AuthenticationError, match="Current password"):
            await svc.admin_password_reset(
                admin.id, old_password="wrong", new_password="NewPass123"
            )

    async def test_password_reset_rejects_reuse(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()
        # First change to force SecurePass1 into history
        await svc.admin_password_reset(
            admin.id, old_password="SecurePass1", new_password="NewPass456"
        )
        # Now try to reuse SecurePass1
        with pytest.raises(PasswordPolicyError, match="recently"):
            await svc.admin_password_reset(
                admin.id, old_password="NewPass456", new_password="SecurePass1"
            )

    async def test_password_reset_enforces_policy(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()
        with pytest.raises(PasswordPolicyError):
            await svc.admin_password_reset(
                admin.id, old_password="SecurePass1", new_password="weak"
            )


class TestPasswordPolicy:
    def test_password_too_short(self):
        svc = AuthService()
        with pytest.raises(PasswordPolicyError):
            svc._enforce_password_policy("Aa1")

    def test_password_no_uppercase(self):
        svc = AuthService()
        with pytest.raises(PasswordPolicyError):
            svc._enforce_password_policy("securepass1")

    def test_password_no_digit(self):
        svc = AuthService()
        with pytest.raises(PasswordPolicyError):
            svc._enforce_password_policy("SecurePass")


class TestAdminSessions:
    async def test_create_and_validate_session(self):
        svc = AuthService(testing_mode=True)
        admin_id = uuid4()
        token = await svc.create_admin_session(admin_id)
        assert token is not None
        found = await svc.validate_admin_session(token)
        assert found == str(admin_id)

    async def test_invalid_session_returns_none(self):
        svc = AuthService(testing_mode=True)
        result = await svc.validate_admin_session("invalid-token")
        assert result is None

    async def test_logout_session(self):
        svc = AuthService(testing_mode=True)
        admin_id = uuid4()
        token = await svc.create_admin_session(admin_id)
        await svc.logout_admin_session(token)
        found = await svc.validate_admin_session(token)
        assert found is None


class TestMFASetup:
    async def test_mfa_setup_returns_secret_and_codes(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()

        setup = await svc.mfa_setup(admin.id)
        assert setup.secret
        assert setup.qr_code
        assert len(setup.recovery_codes) == 8

        # Secret should NOT be persisted yet
        await db_session.refresh(admin)
        assert admin.mfa_secret is None
        assert admin.mfa_enabled is False

    async def test_mfa_verify_setup_persists_on_success(self, db_session: AsyncSession):
        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()

        import pyotp

        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()

        ok = await svc.mfa_verify_setup(admin.id, secret, code)
        assert ok is True

        await db_session.refresh(admin)
        assert admin.mfa_secret == secret
        assert admin.mfa_enabled is True

    async def test_mfa_verify_setup_rejects_wrong_code(self, db_session: AsyncSession):
        import pyotp

        svc = AuthService(db=db_session)
        await svc.first_admin_bootstrap(
            username="admin", email="admin@fabric.io", password="SecurePass1"
        )
        result = await db_session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one()

        secret = pyotp.random_base32()
        ok = await svc.mfa_verify_setup(admin.id, secret, "000000")
        assert ok is False

    async def test_mfa_verify(self):
        import pyotp

        svc = AuthService()
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        assert svc.mfa_verify(secret, code) is True
        assert svc.mfa_verify(secret, "000000") is False
