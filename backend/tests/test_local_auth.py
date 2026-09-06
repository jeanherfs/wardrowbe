import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.config import get_settings
from app.services.local_auth_service import LocalAuthService


class TestLocalAuthService:
    def test_hash_is_not_plaintext_and_verifies(self):
        password = "temporary-password-123"
        password_hash = LocalAuthService.hash_password(password)

        assert password_hash != password
        assert LocalAuthService.verify_password(password, password_hash) is True
        assert LocalAuthService.verify_password("wrong-password", password_hash) is False


class TestLocalAuthEndpoints:
    @pytest.fixture(autouse=True)
    def local_auth_enabled(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "local_auth_enabled", True)
        monkeypatch.setattr(settings, "local_auth_bootstrap_token", "test-bootstrap-token")

    @pytest.mark.asyncio
    async def test_disabled_local_login_is_not_available(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(get_settings(), "local_auth_enabled", False)

        response = await client.post(
            "/api/v1/auth/local-login",
            json={"email": "user@example.com", "password": "password"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_bootstrap_creates_user_and_login_returns_token(self, client: AsyncClient):
        email = f"local-{uuid4()}@example.com"
        bootstrap = await client.post(
            "/api/v1/auth/local-bootstrap",
            headers={"X-Local-Bootstrap-Token": "test-bootstrap-token"},
            json={
                "email": email,
                "display_name": "Local User",
                "password": "temporary-password-123",
            },
        )

        assert bootstrap.status_code == 201
        assert bootstrap.json()["email"] == email
        assert "password" not in bootstrap.json()

        login = await client.post(
            "/api/v1/auth/local-login",
            json={"email": email, "password": "temporary-password-123"},
        )

        assert login.status_code == 200
        assert login.json()["email"] == email
        assert login.json()["access_token"]

    @pytest.mark.asyncio
    async def test_invalid_password_has_uniform_401_response(self, client: AsyncClient):
        email = f"local-invalid-{uuid4()}@example.com"
        await client.post(
            "/api/v1/auth/local-bootstrap",
            headers={"X-Local-Bootstrap-Token": "test-bootstrap-token"},
            json={
                "email": email,
                "display_name": "Local User",
                "password": "temporary-password-123",
            },
        )

        valid = await client.post(
            "/api/v1/auth/local-login",
            json={"email": email, "password": "temporary-password-123"},
        )
        invalid = await client.post(
            "/api/v1/auth/local-login",
            json={"email": email, "password": "wrong-password"},
        )
        unknown = await client.post(
            "/api/v1/auth/local-login",
            json={"email": "unknown@example.com", "password": "wrong-password"},
        )

        assert valid.status_code == 200
        assert invalid.status_code == unknown.status_code == 401
        assert invalid.json()["detail"] == unknown.json()["detail"]

    @pytest.mark.asyncio
    async def test_bootstrap_refuses_existing_user_without_reset(self, client: AsyncClient):
        email = f"existing-{uuid4()}@example.com"
        payload = {
            "email": email,
            "display_name": "Existing User",
            "password": "temporary-password-123",
        }
        headers = {"X-Local-Bootstrap-Token": "test-bootstrap-token"}
        first = await client.post("/api/v1/auth/local-bootstrap", headers=headers, json=payload)
        second = await client.post("/api/v1/auth/local-bootstrap", headers=headers, json=payload)

        assert first.status_code == 201
        assert second.status_code == 409
