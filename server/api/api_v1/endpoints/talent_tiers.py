from fastapi import APIRouter, Depends, HTTPException, status

from server.models import TalentTier, AdminAccount
from server.schemas import schema
from server.api.api_v1 import deps
from server.utils.db_retry import db_retry

router = APIRouter()

@router.get("/")
@db_retry(max_retries=3, delay=1.0)
async def get_talent_tiers():
    """
    获取所有天资等级
    """
    talent_tiers = await TalentTier.all().order_by('rarity')
    return {"items": talent_tiers, "total": len(talent_tiers)}

@router.get("/{tier_id}", response_model=schema.TalentTier)
@db_retry(max_retries=3, delay=1.0)
async def get_talent_tier(tier_id: int):
    """
    根据ID获取天资等级
    """
    talent_tier = await TalentTier.get_or_none(id=tier_id)
    if not talent_tier:
        raise HTTPException(status_code=404, detail="天资等级不存在")
    return talent_tier

@router.post("/", response_model=schema.TalentTier, status_code=status.HTTP_201_CREATED)
async def create_talent_tier(
    tier_data: dict,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user)
):
    """
    创建新的天资等级（仅超级管理员）
    """
    new_tier = await TalentTier.create(**tier_data)
    return new_tier

@router.put("/{tier_id}", response_model=schema.TalentTier)
async def update_talent_tier(
    tier_id: int,
    tier_data: dict,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user)
):
    """
    更新天资等级（仅超级管理员）
    """
    tier = await TalentTier.get_or_none(id=tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="天资等级不存在")
    
    await tier.update_from_dict(tier_data)
    await tier.save()
    return tier

@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_talent_tier(
    tier_id: int,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user)
):
    """
    删除天资等级（仅超级管理员）
    """
    tier = await TalentTier.get_or_none(id=tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="天资等级不存在")
    
    await tier.delete()
    return {}
