from api.services.auth_service import AuthService, InvalidTokenError


def test_create_and_validate_token():
    svc = AuthService(secret_key="test-secret")
    token = svc.create_token(subject="agent-1", agent_class="agent:developer")
    payload = svc.validate_token(token)
    assert payload["sub"] == "agent-1"
    assert payload["agent_class"] == "agent:developer"
    assert payload["type"] == "agent"
    assert payload["role"] == "agent"


def test_invalid_token_raises():
    svc = AuthService(secret_key="test-secret")
    import pytest

    with pytest.raises(InvalidTokenError):
        svc.validate_token("invalid-token")


def test_password_hashing():
    svc = AuthService(secret_key="test-secret")
    hashed = svc.hash_password("my-password")
    assert hashed != "my-password"
    assert svc.verify_password("my-password", hashed)
    assert not svc.verify_password("wrong", hashed)


def test_admin_token():
    svc = AuthService(secret_key="test-secret")
    token = svc.create_token(subject="admin-1", token_type="admin", role="admin")
    payload = svc.validate_token(token)
    assert payload["type"] == "admin"
    assert payload["role"] == "admin"
