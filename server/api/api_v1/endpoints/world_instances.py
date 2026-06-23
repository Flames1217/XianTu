import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from tortoise.expressions import Q

from server.api.api_v1 import deps
from server.api.api_v1.endpoints.presence import is_online_at
from server.models import (
    CharacterBase,
    PlayerAccount,
    PlayerPresence,
    TravelSession,
    TravelSessionEvent,
    WorldInstance,
    WorldInstanceMap,
)
from server.schemas import schema

router = APIRouter()


def _pick(data: Any, *keys: str) -> Any:
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data:
            return data[key]
    return None


async def latest_character(player_id: int) -> CharacterBase | None:
    character = (
        await CharacterBase.filter(player_id=player_id, is_deleted=False)
        .order_by("-created_at")
        .first()
    )
    if character:
        await character.fetch_related("game_save")
    return character


def snapshot_parts(character: CharacterBase | None) -> dict[str, Any]:
    if not character:
        return {
            "owner_char_id": None,
            "save_version": None,
            "game_time": None,
            "world_info": None,
            "owner_location": None,
            "owner_base_info": None,
            "relationships": None,
        }
    save = character.game_save
    save_data = save.save_data or {}
    world_map = save.world_map or {}
    world_info = _pick(save_data, "world_info", "worldInfo", "世界信息", "世界") or world_map or None
    return {
        "owner_char_id": character.char_id,
        "save_version": save.version,
        "game_time": save.game_time,
        "world_info": world_info,
        "owner_location": _pick(save_data, "location", "owner_location", "玩家位置", "位置"),
        "owner_base_info": character.base_info or {},
        "relationships": _pick(save_data, "relationships", "关系", "社交关系", "社交"),
    }


async def ensure_world_instance(player: PlayerAccount) -> WorldInstance:
    world = await WorldInstance.get_or_none(owner_id=player.id)
    character = await latest_character(player.id)
    owner_char_id = character.char_id if character else None
    if not world:
        world = await WorldInstance.create(
            owner_id=player.id,
            owner_char_id=owner_char_id,
            visibility_mode="public",
        )
    elif world.owner_char_id != owner_char_id:
        world.owner_char_id = owner_char_id
        world.revision += 1
        await world.save(update_fields=["owner_char_id", "revision", "updated_at"])
    await ensure_world_map(world, character)
    return world


async def ensure_world_map(
    world: WorldInstance, character: CharacterBase | None = None
) -> WorldInstanceMap:
    existing = await WorldInstanceMap.get_or_none(
        world_instance_id=world.id, map_id=1
    )
    if character is None:
        character = await latest_character(world.owner_id)
    payload = snapshot_parts(character)["world_info"]
    if not existing:
        return await WorldInstanceMap.create(
            world_instance_id=world.id,
            map_id=1,
            map_key="main",
            payload=payload,
        )
    if payload is not None and existing.revision == 1 and existing.payload != payload:
        existing.payload = payload
        existing.revision += 1
        await existing.save(update_fields=["payload", "revision", "updated_at"])
    return existing


async def world_summary(world: WorldInstance, include_private: bool) -> dict[str, Any]:
    maps = await WorldInstanceMap.filter(world_instance_id=world.id).order_by("map_id")
    return {
        "world_instance_id": world.id,
        "owner_player_id": world.owner_id,
        "owner_char_id": world.owner_char_id,
        "visibility_mode": world.visibility_mode,
        "invite_code": world.invite_code if include_private else None,
        "allow_offline_travel": world.allow_offline_travel,
        "allow_map_overwrite": world.allow_map_overwrite,
        "offline_agent_prompt": world.offline_agent_prompt if include_private else None,
        "revision": world.revision,
        "maps": [
            {"map_id": item.map_id, "map_key": item.map_key, "revision": item.revision}
            for item in maps
        ],
    }


@router.get("/me", response_model=schema.WorldInstanceSummary)
async def get_my_world(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await ensure_world_instance(current_user)
    return await world_summary(world, include_private=True)


@router.post("/me/visibility", response_model=schema.WorldInstanceSummary)
async def update_visibility(
    payload: schema.WorldVisibilityUpdate,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await ensure_world_instance(current_user)
    world.visibility_mode = payload.visibility_mode
    if payload.visibility_mode != "public" and not world.invite_code:
        world.invite_code = secrets.token_urlsafe(12)
    world.revision += 1
    await world.save()
    return await world_summary(world, include_private=True)


@router.post("/me/policy", response_model=schema.WorldInstanceSummary)
async def update_policy(
    payload: schema.WorldPolicyUpdate,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await ensure_world_instance(current_user)
    world.allow_offline_travel = payload.allow_offline_travel
    world.revision += 1
    await world.save()
    return await world_summary(world, include_private=True)


@router.post("/me/offline-prompt", response_model=schema.WorldInstanceSummary)
async def update_offline_prompt(
    payload: schema.WorldOfflinePromptUpdate,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await ensure_world_instance(current_user)
    world.offline_agent_prompt = payload.offline_agent_prompt.strip() or None
    world.revision += 1
    await world.save()
    return await world_summary(world, include_private=True)


@router.post("/me/invite-code/regenerate", response_model=schema.WorldInstanceSummary)
async def regenerate_invite_code(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await ensure_world_instance(current_user)
    if world.visibility_mode == "public":
        world.invite_code = None
    else:
        world.invite_code = secrets.token_urlsafe(12)
    world.revision += 1
    await world.save()
    return await world_summary(world, include_private=True)


@router.get("/list", response_model=list[schema.TravelableWorld])
async def list_worlds(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    visibility: str | None = Query(default=None, max_length=16),
    search: str | None = Query(default=None, max_length=50),
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    query = WorldInstance.all().prefetch_related("owner")
    if visibility:
        if visibility not in {"public", "hidden", "locked"}:
            raise HTTPException(status_code=422, detail="无效的可见性筛选")
        query = query.filter(visibility_mode=visibility)
    if search and search.strip():
        query = query.filter(Q(owner__user_name__icontains=search.strip()))
    worlds = await query.order_by("-created_at").offset(skip).limit(limit)
    presence_rows = await PlayerPresence.filter(
        player_id__in=[world.owner_id for world in worlds]
    )
    presence_by_player = {row.player_id: row for row in presence_rows}
    result = []
    for world in worlds:
        presence = presence_by_player.get(world.owner_id)
        result.append(
            {
                "world_instance_id": world.id,
                "owner_player_id": world.owner_id,
                "owner_username": world.owner.user_name,
                "owner_char_id": world.owner_char_id,
                "visibility_mode": world.visibility_mode,
                "allow_offline_travel": world.allow_offline_travel,
                "allow_map_overwrite": world.allow_map_overwrite,
                "owner_online": is_online_at(
                    presence.last_heartbeat_at if presence else None
                ),
                "owner_last_heartbeat_at": (
                    presence.last_heartbeat_at if presence else None
                ),
                "revision": world.revision,
                "created_at": world.created_at,
            }
        )
    return result


async def _authorize_world_access(
    world: WorldInstance, user: PlayerAccount, session_id: int | None
) -> TravelSession | None:
    if world.owner_id == user.id:
        return None
    if not session_id:
        raise HTTPException(status_code=403, detail="需要有效穿越会话")
    session = await TravelSession.get_or_none(
        id=session_id,
        visitor_id=user.id,
        target_world_instance_id=world.id,
        state="active",
    )
    if not session:
        raise HTTPException(status_code=404, detail="穿越会话不存在或无权访问")
    return session


@router.get("/{world_instance_id}/map/{map_id}/graph", response_model=schema.MapGraphResponse)
async def get_map_graph(
    world_instance_id: int,
    map_id: int,
    session_id: int | None = Query(default=None, gt=0),
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await WorldInstance.get_or_none(id=world_instance_id)
    if not world:
        raise HTTPException(status_code=404, detail="世界实例不存在")
    session = await _authorize_world_access(world, current_user, session_id)
    character = await latest_character(world.owner_id)
    map_row = await ensure_world_map(world, character)
    if map_id != map_row.map_id:
        raise HTTPException(status_code=404, detail="地图不存在")
    parts = snapshot_parts(character)
    return {
        "map_id": map_row.map_id,
        "map_key": map_row.map_key,
        "viewer_poi_id": session.current_poi_id if session else None,
        "world_info": map_row.payload or parts["world_info"],
        "owner_base_info": parts["owner_base_info"],
        "owner_location": parts["owner_location"],
        "relationships": parts["relationships"],
    }


@router.post("/{world_instance_id}/action", response_model=schema.WorldActionResponse)
async def world_action(
    world_instance_id: int,
    payload: schema.WorldActionRequest,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    world = await WorldInstance.get_or_none(id=world_instance_id)
    if not world:
        raise HTTPException(status_code=404, detail="世界实例不存在")
    session = await _authorize_world_access(world, current_user, payload.session_id)
    if payload.action_type == "move":
        if not session:
            raise HTTPException(status_code=400, detail="世界主人无需穿越移动会话")
        to_poi_id = payload.intent.get("to_poi_id")
        if not isinstance(to_poi_id, int) or to_poi_id <= 0:
            raise HTTPException(status_code=422, detail="to_poi_id 必须为正整数")
        session.current_poi_id = to_poi_id
        await session.save(update_fields=["current_poi_id"])
        await TravelSessionEvent.create(
            session_id=session.id,
            actor_id=current_user.id,
            event_type="move",
            map_id=session.current_map_id,
            poi_id=to_poi_id,
            payload={"intent": payload.intent},
        )
        return {
            "success": True,
            "message": "移动成功",
            "new_map_id": session.current_map_id,
            "new_poi_id": to_poi_id,
        }

    if world.owner_id != current_user.id and not world.allow_map_overwrite:
        raise HTTPException(status_code=403, detail="世界主人未允许地图覆盖")
    locations = payload.intent.get("locations")
    if not isinstance(locations, list) or len(locations) > 5000:
        raise HTTPException(status_code=422, detail="locations 必须为合法数组")
    map_id = payload.intent.get("map_id") or (session.current_map_id if session else 1)
    if not isinstance(map_id, int) or map_id <= 0:
        raise HTTPException(status_code=422, detail="map_id 必须为正整数")
    map_row, _ = await WorldInstanceMap.get_or_create(
        world_instance_id=world.id,
        map_id=map_id,
        defaults={"map_key": f"map-{map_id}"},
    )
    existing = map_row.payload if isinstance(map_row.payload, dict) else {}
    map_row.payload = {**existing, "locations": locations}
    map_row.revision += 1
    await map_row.save()
    world.revision += 1
    await world.save(update_fields=["revision", "updated_at"])
    if session:
        await TravelSessionEvent.create(
            session_id=session.id,
            actor_id=current_user.id,
            event_type="map_overwrite",
            map_id=map_id,
            poi_id=session.current_poi_id,
            payload={"location_count": len(locations)},
        )
    return {
        "success": True,
        "message": "地图已更新",
        "new_map_id": map_id,
        "new_poi_id": session.current_poi_id if session else None,
    }
