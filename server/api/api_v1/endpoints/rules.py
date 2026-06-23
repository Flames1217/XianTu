from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from server.crud import crud_rule
from server.schemas import schema

router = APIRouter()

# 注意：origins 和 talents 的CRUD操作已移至独立的端点文件
# /origins/ 和 /talents/ 提供完整的CRUD功能
# 这里只保留 spirit-roots 和 settings 端点以避免重复


@router.get("/rules/settings", response_model=Dict[str, Any], tags=["核心规则"])
async def get_settings_api():
    """
    获取所有核心设定
    """
    return await crud_rule.get_core_settings()