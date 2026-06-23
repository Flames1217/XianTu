from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from server.main import app


def unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def register_and_login(client: TestClient, username: str) -> dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"user_name": username, "password": "correct-horse-battery-staple"},
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": "correct-horse-battery-staple"},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_presence_and_travel_flow_matches_latest_frontend_contract() -> None:
    with TestClient(app) as client:
        owner_username = unique_name("online_owner")
        visitor_username = unique_name("online_visitor")
        owner_headers = register_and_login(client, owner_username)
        visitor_headers = register_and_login(client, visitor_username)

        heartbeat = client.post(
            "/api/v1/presence/heartbeat", headers=owner_headers, json={}
        )
        assert heartbeat.status_code == 200
        assert heartbeat.json()["user_name"] == owner_username
        assert heartbeat.json()["last_heartbeat_at"]

        owner_presence = client.get("/api/v1/presence/me", headers=owner_headers)
        assert owner_presence.status_code == 200
        assert owner_presence.json()["is_online"] is True

        owner_world = client.get(
            "/api/v1/worlds/instance/me", headers=owner_headers
        )
        assert owner_world.status_code == 200
        assert owner_world.json()["owner_player_id"] > 0
        assert owner_world.json()["visibility_mode"] == "public"

        policy = client.post(
            "/api/v1/worlds/instance/me/policy",
            headers=owner_headers,
            json={"allow_offline_travel": True},
        )
        assert policy.status_code == 200
        assert policy.json()["allow_offline_travel"] is True

        sign_in = client.post(
            "/api/v1/travel/signin", headers=visitor_headers, json={}
        )
        assert sign_in.status_code == 200
        assert sign_in.json()["signed_in"] is True
        assert sign_in.json()["travel_points"] > 0

        worlds = client.get(
            "/api/v1/worlds/instance/list?skip=0&limit=20",
            headers=visitor_headers,
        )
        assert worlds.status_code == 200
        assert any(
            world["owner_username"] == owner_username for world in worlds.json()
        )

        started = client.post(
            "/api/v1/travel/start",
            headers=visitor_headers,
            json={"target_username": owner_username},
        )
        assert started.status_code == 200, started.text
        session_id = started.json()["session_id"]
        assert started.json()["travel_points_left"] >= 0

        active = client.get("/api/v1/travel/active", headers=visitor_headers)
        assert active.status_code == 200
        assert active.json()["session_id"] == session_id

        ended = client.post(
            "/api/v1/travel/end",
            headers=visitor_headers,
            json={"session_id": session_id},
        )
        assert ended.status_code == 200
        assert ended.json()["success"] is True


def test_character_create_accepts_latest_frontend_base_info_shape() -> None:
    with TestClient(app) as client:
        headers = register_and_login(client, unique_name("character_contract"))
        response = client.post(
            "/api/v1/characters/create",
            headers=headers,
            json={
                "char_id": f"char-contract-{uuid4().hex[:8]}",
                "base_info": {
                    "名字": "云游子",
                    "性别": "男",
                    "世界": {"id": 1, "name": "朝天大陆"},
                    "天资": {"id": 2, "name": "天骄"},
                    "出生": {"id": 3, "name": "散修"},
                    "灵根": {"id": 4, "name": "火灵根"},
                    "天赋": [{"id": 5, "name": "剑心"}],
                    "后天六司": {
                        "根骨": 0,
                        "灵性": 0,
                        "悟性": 0,
                        "气运": 0,
                        "魅力": 0,
                        "心性": 0,
                    },
                },
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["base_info"]["天赋"][0]["name"] == "剑心"
