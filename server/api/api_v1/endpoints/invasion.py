from fastapi import APIRouter, Depends

from server.api.api_v1 import deps
from server.models import InvasionReport, PlayerAccount
from server.schemas import schema

router = APIRouter()


@router.get("/reports/me", response_model=list[schema.InvasionReportOut])
async def my_invasion_reports(
    current_user: PlayerAccount = Depends(deps.get_current_active_user),
):
    reports = (
        await InvasionReport.filter(world_instance__owner_id=current_user.id)
        .order_by("-created_at")
        .limit(50)
    )
    return [
        {
            "id": report.id,
            "world_instance_id": report.world_instance_id,
            "created_at": report.created_at,
            "unread": report.unread,
            "summary": report.summary,
        }
        for report in reports
    ]
