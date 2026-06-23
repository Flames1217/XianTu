from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import app


CATALOG_PATHS = (
    "/api/v1/worlds/",
    "/api/v1/talent_tiers/",
    "/api/v1/origins/",
    "/api/v1/spirit_roots/",
    "/api/v1/talents/",
)


def test_catalog_lists_use_latest_frontend_envelope() -> None:
    with TestClient(app) as client:
        for path in CATALOG_PATHS:
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
            body = response.json()
            assert set(body) == {"items", "total"}, path
            assert isinstance(body["items"], list), path
            assert body["total"] == len(body["items"]), path


def test_catalog_mutations_require_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/origins/",
            json={"name": "未授权出身", "talent_cost": 0, "rarity": 1},
        )

    assert response.status_code == 401
