from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/config")
async def prompt_config():
    return {
        "prompts": {},
        "version": "1.0.0",
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }
