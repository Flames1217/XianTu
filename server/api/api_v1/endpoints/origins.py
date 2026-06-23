"""出身相关的API端点 (已重构为异步)"""
from fastapi import APIRouter, Depends, HTTPException
from server.schemas.schema import Origin, OriginCreate, OriginUpdate
from server.crud import crud_origins
from server.utils.db_retry import db_retry
from server.api.api_v1 import deps
from server.models import AdminAccount

router = APIRouter()

@router.post("/", response_model=Origin, tags=["核心规则"])
@db_retry(max_retries=3, delay=1.0)
async def create_origin_endpoint(
    origin: OriginCreate,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user),
):
    """创建新出身"""
    new_origin, message = await crud_origins.create_origin(origin)
    if not new_origin:
        raise HTTPException(status_code=409, detail=message)
    return new_origin

@router.get("/", tags=["核心规则"])
@db_retry(max_retries=3, delay=1.0)
async def get_origins_endpoint():
    """获取所有出身"""
    origins = await crud_origins.get_origins()
    return {"items": origins, "total": len(origins)}

@router.get("/{origin_id}", response_model=Origin, tags=["核心规则"])
async def get_origin_endpoint(origin_id: int):
    """根据ID获取出身"""
    db_origin = await crud_origins.get_origin(origin_id)
    if not db_origin:
        raise HTTPException(status_code=404, detail="出身不存在")
    return db_origin

@router.put("/{origin_id}", response_model=Origin, tags=["核心规则"])
async def update_origin_endpoint(
    origin_id: int,
    origin: OriginUpdate,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user),
):
    """更新出身"""
    updated_origin, message = await crud_origins.update_origin(origin_id, origin)
    if not updated_origin:
        status_code = 404 if "未找到" in message else 409
        raise HTTPException(status_code=status_code, detail=message)
    return updated_origin

@router.delete("/{origin_id}", response_model=dict, tags=["核心规则"])
async def delete_origin_endpoint(
    origin_id: int,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user),
):
    """删除出身"""
    success = await crud_origins.delete_origin(origin_id)
    if not success:
        raise HTTPException(status_code=404, detail="出身不存在或删除失败")
    return {"message": "出身删除成功"}
