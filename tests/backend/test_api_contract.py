from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import app


EXPECTED_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/v1/version"),
    ("GET", "/api/v1/auth/security-settings"),
    ("POST", "/api/v1/auth/send-email-code"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/token"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/characters/create"),
    ("GET", "/api/v1/characters/{char_id}"),
    ("PUT", "/api/v1/characters/{char_id}/save"),
    ("GET", "/api/v1/worlds/"),
    ("GET", "/api/v1/talent_tiers/"),
    ("GET", "/api/v1/origins/"),
    ("GET", "/api/v1/spirit_roots/"),
    ("GET", "/api/v1/talents/"),
    ("GET", "/api/v1/workshop/items"),
    ("GET", "/api/v1/workshop/my-items"),
    ("POST", "/api/v1/workshop/items"),
    ("POST", "/api/v1/workshop/items/{item_id}/download"),
    ("DELETE", "/api/v1/workshop/items/{item_id}"),
    ("POST", "/api/v1/presence/heartbeat"),
    ("GET", "/api/v1/presence/me"),
    ("GET", "/api/v1/presence/status/{username}"),
    ("GET", "/api/v1/travel/profile"),
    ("POST", "/api/v1/travel/signin"),
    ("GET", "/api/v1/travel/active"),
    ("GET", "/api/v1/travel/status/{session_id}"),
    ("POST", "/api/v1/travel/start"),
    ("POST", "/api/v1/travel/end"),
    ("GET", "/api/v1/travel/logs/{session_id}"),
    ("GET", "/api/v1/travel/snapshot/{session_id}"),
    ("POST", "/api/v1/travel/note"),
    ("GET", "/api/v1/worlds/instance/me"),
    ("POST", "/api/v1/worlds/instance/me/visibility"),
    ("POST", "/api/v1/worlds/instance/me/policy"),
    ("POST", "/api/v1/worlds/instance/me/offline-prompt"),
    ("POST", "/api/v1/worlds/instance/me/invite-code/regenerate"),
    ("GET", "/api/v1/worlds/instance/list"),
    ("GET", "/api/v1/worlds/instance/{world_instance_id}/map/{map_id}/graph"),
    ("POST", "/api/v1/worlds/instance/{world_instance_id}/action"),
    ("GET", "/api/v1/invasion/reports/me"),
    ("GET", "/api/v1/prompts/config"),
}


def test_latest_frontend_api_routes_are_available() -> None:
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    actual_routes = {
        (method.upper(), path)
        for path, operations in openapi["paths"].items()
        for method in operations
    }

    missing = EXPECTED_ROUTES - actual_routes

    assert not missing, f"最新版前端依赖的后端路由缺失: {sorted(missing)}"


def test_public_version_has_release_fallback() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json()["version"] == "4.7.7"
