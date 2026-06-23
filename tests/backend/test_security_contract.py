from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from jose import jwt

from server.core.config import settings
from server.main import app


def test_default_admin_is_not_created_without_explicit_configuration() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/admin/token",
            data={"username": "admin", "password": "admin"},
        )

    assert response.status_code == 401


def test_readiness_checks_database_connection() -> None:
    with TestClient(app) as client:
        response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_player_token_is_bound_to_player_authentication_domain() -> None:
    with TestClient(app) as client:
        username = f"token_player_{uuid4().hex[:8]}"
        register = client.post(
            "/api/v1/auth/register",
            json={"user_name": username, "password": "strong-password-123"},
        )
        assert register.status_code == 200

        login = client.post(
            "/api/v1/auth/token",
            json={"username": username, "password": "strong-password-123"},
        )
        assert login.status_code == 200

    payload = jwt.decode(
        login.json()["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    assert payload["account_type"] == "player"
    assert payload["sub"] == str(register.json()["id"])
