from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from server.api.api_v1 import deps
from server.models import PlayerAccount, PlayerPresence
from server.schemas import schema

router = APIRouter()
ONLINE_THRESHOLD = timedelta(seconds=90)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_online_at(last_heartbeat_at: datetime | None, now: datetime | None = None) -> bool:
    if last_heartbeat_at is None:
        return False
    current = now or utc_now()
    return last_heartbeat_at >= current - ONLINE_THRESHOLD


async def get_presence(player_id: int) -> PlayerPresence | None:
    return await PlayerPresence.get_or_none(player_id=player_id)


@router.post("/heartbeat", response_model=schema.PresenceHeartbeatResponse)
async def heartbeat(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    now = utc_now()
    presence, _ = await PlayerPresence.get_or_create(player_id=current_user.id)
    presence.last_heartbeat_at = now
    await presence.save(update_fields=["last_heartbeat_at", "updated_at"])
    return {
        "user_name": current_user.user_name,
        "server_time": now,
        "last_heartbeat_at": presence.last_heartbeat_at,
    }


@router.get("/me", response_model=schema.PresenceStatusResponse)
async def my_presence(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    now = utc_now()
    presence = await get_presence(current_user.id)
    last_heartbeat = presence.last_heartbeat_at if presence else None
    return {
        "user_name": current_user.user_name,
        "is_online": is_online_at(last_heartbeat, now),
        "last_heartbeat_at": last_heartbeat,
        "server_time": now,
    }


@router.get("/status/{username}", response_model=schema.PresenceStatusResponse)
async def presence_status(
    username: str,
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    del current_user
    player = await PlayerAccount.get_or_none(user_name=username)
    if not player:
        raise HTTPException(status_code=404, detail="用户不存在")
    now = utc_now()
    presence = await get_presence(player.id)
    last_heartbeat = presence.last_heartbeat_at if presence else None
    return {
        "user_name": player.user_name,
        "is_online": is_online_at(last_heartbeat, now),
        "last_heartbeat_at": last_heartbeat,
        "server_time": now,
    }
