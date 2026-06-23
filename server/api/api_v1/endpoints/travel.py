import secrets
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from server.api.api_v1 import deps
from server.api.api_v1.endpoints.presence import is_online_at
from server.api.api_v1.endpoints.world_instances import latest_character, snapshot_parts
from server.models import (
    InvasionReport,
    PlayerAccount,
    PlayerPresence,
    TravelProfile,
    TravelSession,
    TravelSessionEvent,
    WorldInstance,
)
from server.schemas import schema

router = APIRouter()
DAILY_SIGNIN_POINTS = 3
TRAVEL_COST = 1


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def _profile(player_id: int) -> TravelProfile:
    profile, _ = await TravelProfile.get_or_create(player_id=player_id)
    return profile


def _profile_response(profile: TravelProfile, message: str) -> dict[str, Any]:
    return {
        "travel_points": profile.travel_points,
        "signed_in": profile.last_signin_date == _today(),
        "message": message,
    }


def _session_response(
    session: TravelSession,
    points: int,
    world: WorldInstance,
    owner_character_info: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "target_world_instance_id": session.target_world_instance_id,
        "entry_map_id": session.entry_map_id,
        "entry_poi_id": session.entry_poi_id,
        "return_anchor": session.return_anchor or {},
        "travel_points_left": points,
        "owner_offline_agent_prompt": world.offline_agent_prompt,
        "owner_character_info": owner_character_info,
    }


def _owner_character_info(base_info: Any) -> dict[str, Any] | None:
    if not isinstance(base_info, dict):
        return None
    return {
        "name": base_info.get("name") or base_info.get("名字"),
        "cultivation_level": (
            base_info.get("cultivation_level") or base_info.get("境界")
        ),
        "sect": base_info.get("sect") or base_info.get("门派"),
        "personality": base_info.get("personality") or base_info.get("性格"),
    }


async def _owned_session(
    session_id: int,
    current_user: PlayerAccount,
    allow_world_owner: bool = False,
) -> TravelSession:
    session = await TravelSession.get_or_none(id=session_id).prefetch_related(
        "target_world_instance"
    )
    if not session:
        raise HTTPException(status_code=404, detail="穿越会话不存在")
    owns_session = session.visitor_id == current_user.id
    owns_world = (
        allow_world_owner
        and session.target_world_instance.owner_id == current_user.id
    )
    if not owns_session and not owns_world:
        raise HTTPException(status_code=404, detail="穿越会话不存在或无权访问")
    return session


@router.get("/profile", response_model=schema.TravelProfileResponse)
async def get_profile(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    profile = await _profile(current_user.id)
    message = "今日已签到" if profile.last_signin_date == _today() else "今日未签到"
    return _profile_response(profile, message)


@router.post("/signin", response_model=schema.TravelProfileResponse)
async def signin(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    today = _today()
    async with in_transaction() as connection:
        profile = (
            await TravelProfile.filter(player_id=current_user.id)
            .using_db(connection)
            .select_for_update()
            .first()
        )
        if not profile:
            profile = await TravelProfile.create(
                player_id=current_user.id, using_db=connection
            )
        if profile.last_signin_date == today:
            return _profile_response(profile, "今日已签到")
        profile.last_signin_date = today
        profile.travel_points += DAILY_SIGNIN_POINTS
        await profile.save(using_db=connection)
    return _profile_response(profile, f"签到成功，获得 {DAILY_SIGNIN_POINTS} 点穿越点")


@router.get("/active", response_model=schema.TravelStartResponse | None)
async def get_active_session(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    session = (
        await TravelSession.filter(visitor_id=current_user.id, state="active")
        .prefetch_related("target_world_instance")
        .order_by("-started_at")
        .first()
    )
    if not session:
        return None
    profile = await _profile(current_user.id)
    world = session.target_world_instance
    info = _owner_character_info(
        snapshot_parts(await latest_character(world.owner_id))["owner_base_info"]
    )
    return _session_response(session, profile.travel_points, world, info)


@router.get("/status/{session_id}", response_model=schema.TravelSessionStatusResponse)
async def get_session_status(
    session_id: int,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    session = await _owned_session(session_id, current_user, allow_world_owner=True)
    return {
        "session_id": session.id,
        "state": session.state,
        "end_reason": session.end_reason,
        "target_world_instance_id": session.target_world_instance_id,
        "entry_map_id": session.entry_map_id,
        "entry_poi_id": session.entry_poi_id,
    }


@router.post("/start", response_model=schema.TravelStartResponse)
async def start_travel(
    payload: schema.TravelStartRequest,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    owner = await PlayerAccount.get_or_none(user_name=payload.target_username.strip())
    if not owner:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    if owner.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能穿越到自己的世界")
    world = await WorldInstance.get_or_none(owner_id=owner.id)
    if not world:
        raise HTTPException(status_code=404, detail="目标用户尚未创建世界实例")
    if world.visibility_mode not in {"public", "hidden", "locked"}:
        raise HTTPException(status_code=403, detail="目标世界不可访问")
    if world.visibility_mode != "public":
        supplied_code = (payload.invite_code or "").strip()
        if not world.invite_code or not secrets.compare_digest(
            supplied_code, world.invite_code
        ):
            raise HTTPException(status_code=403, detail="邀请码无效")
    presence = await PlayerPresence.get_or_none(player_id=owner.id)
    owner_online = is_online_at(presence.last_heartbeat_at if presence else None)
    if not owner_online and not world.allow_offline_travel:
        raise HTTPException(status_code=403, detail="世界主人离线且未允许离线穿越")

    parts = snapshot_parts(await latest_character(owner.id))
    try:
        async with in_transaction() as connection:
            active = (
                await TravelSession.filter(visitor_id=current_user.id, state="active")
                .using_db(connection)
                .select_for_update()
                .first()
            )
            if active:
                raise HTTPException(status_code=409, detail="已有进行中的穿越会话")
            profile = (
                await TravelProfile.filter(player_id=current_user.id)
                .using_db(connection)
                .select_for_update()
                .first()
            )
            if not profile or profile.travel_points < TRAVEL_COST:
                raise HTTPException(status_code=400, detail="穿越点不足")
            profile.travel_points -= TRAVEL_COST
            await profile.save(using_db=connection)
            session = await TravelSession.create(
                visitor_id=current_user.id,
                target_world_instance_id=world.id,
                active_slot=f"visitor:{current_user.id}",
                entry_map_id=1,
                entry_poi_id=1,
                current_map_id=1,
                current_poi_id=1,
                return_anchor={"visitor_player_id": current_user.id},
                using_db=connection,
            )
            await TravelSessionEvent.create(
                session_id=session.id,
                actor_id=current_user.id,
                event_type="travel_started",
                map_id=1,
                poi_id=1,
                payload={"owner_online": owner_online},
                using_db=connection,
            )
            await InvasionReport.create(
                world_instance_id=world.id,
                session_id=session.id,
                summary={
                    "session_id": session.id,
                    "visitor_player_id": current_user.id,
                    "visitor_username": current_user.user_name,
                    "state": "active",
                },
                using_db=connection,
            )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="已有进行中的穿越会话")
    return _session_response(
        session,
        profile.travel_points,
        world,
        _owner_character_info(parts["owner_base_info"]),
    )


@router.post("/end", response_model=schema.OperationResponse)
async def end_travel(
    payload: schema.TravelEndRequest,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    async with in_transaction() as connection:
        session = (
            await TravelSession.filter(
                id=payload.session_id, visitor_id=current_user.id
            )
            .using_db(connection)
            .select_for_update()
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="穿越会话不存在或无权访问")
        if session.state != "active":
            return {"success": True, "message": "会话已结束"}
        session.state = "ended"
        session.end_reason = "normal"
        session.ended_at = datetime.now(timezone.utc)
        session.active_slot = None
        await session.save(using_db=connection)
        await TravelSessionEvent.create(
            session_id=session.id,
            actor_id=current_user.id,
            event_type="travel_ended",
            map_id=session.current_map_id,
            poi_id=session.current_poi_id,
            payload={"reason": "normal"},
            using_db=connection,
        )
        report = (
            await InvasionReport.filter(session_id=session.id)
            .using_db(connection)
            .first()
        )
        if report:
            report.summary = {
                **(report.summary or {}),
                "state": "ended",
                "end_reason": "normal",
            }
            await report.save(using_db=connection)
    return {"success": True, "message": "会话已结束"}


@router.get("/logs/{session_id}", response_model=schema.TravelSessionLogsResponse)
async def get_logs(
    session_id: int,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    session = await _owned_session(session_id, current_user, allow_world_owner=True)
    events = await TravelSessionEvent.filter(session_id=session.id).order_by(
        "created_at", "id"
    )
    return {
        "session_id": session.id,
        "state": session.state,
        "end_reason": session.end_reason,
        "target_world_instance_id": session.target_world_instance_id,
        "entry_map_id": session.entry_map_id,
        "entry_poi_id": session.entry_poi_id,
        "events": [
            {
                "created_at": event.created_at,
                "event_type": event.event_type,
                "map_id": event.map_id,
                "poi_id": event.poi_id,
                "payload": event.payload,
            }
            for event in events
        ],
    }


@router.get("/snapshot/{session_id}", response_model=schema.TravelWorldSnapshotResponse)
async def get_snapshot(
    session_id: int,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    session = await _owned_session(session_id, current_user)
    world = await WorldInstance.get(id=session.target_world_instance_id).prefetch_related(
        "owner"
    )
    parts = snapshot_parts(await latest_character(world.owner_id))
    return {
        "session_id": session.id,
        "target_world_instance_id": world.id,
        "owner_player_id": world.owner_id,
        "owner_username": world.owner.user_name,
        **parts,
    }


@router.post("/note", response_model=schema.OperationResponse)
async def append_note(
    payload: schema.TravelNoteRequest,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    session = await _owned_session(payload.session_id, current_user)
    if session.state != "active":
        raise HTTPException(status_code=409, detail="穿越会话已结束")
    note = payload.note.strip()
    if not note:
        raise HTTPException(status_code=422, detail="笔记不能为空")
    await TravelSessionEvent.create(
        session_id=session.id,
        actor_id=current_user.id,
        event_type="note",
        map_id=session.current_map_id,
        poi_id=session.current_poi_id,
        payload={"note": note, "meta": payload.meta},
    )
    return {"success": True, "message": "笔记已记录"}
