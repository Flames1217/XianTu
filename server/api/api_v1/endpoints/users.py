from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from server.schemas import schema
from server.crud import crud_user
from server.api.api_v1 import deps
from server.models import AdminAccount, CharacterBase

router = APIRouter()


@router.get('/', response_model=List[dict], tags=["用户管理"])
async def get_all_users(current_admin: AdminAccount = Depends(deps.get_admin_or_super_admin)):
    """
    获取所有用户列表（管理员权限）
    """
    players = await crud_user.get_all_players()
    result = []
    for player in players:
        # 计算角色数量
        character_count = await CharacterBase.filter(player_id=player.id, is_deleted=False).count()
        
        player_data = {
            "id": player.id,
            "user_name": player.user_name,
            "created_at": player.created_at,
            "is_banned": player.is_banned,
            "character_count": character_count
        }
        result.append(player_data)
    
    return result

@router.get("/me", response_model=schema.PlayerAccount, tags=["用户"])
async def read_users_me(current_user: schema.PlayerAccount = Depends(deps.get_current_active_user)):
    """
    获取当前用户信息
    """
    return current_user

@router.get("/query", response_model=schema.PlayerAccount, tags=["用户"])
async def query_user(
    user_id: Optional[int] = None,
    username: Optional[str] = None
):
    """
    根据用户ID或道号（用户名）查询用户信息。至少提供一个查询参数。
    """
    if not user_id and not username:
        raise HTTPException(status_code=400, detail="请提供 user_id 或 username 进行查询")

    db_user = None
    if user_id:
        db_user = await crud_user.get_player_by_id(user_id)
    elif username:
        db_user = await crud_user.get_player_by_username(user_name=username)

    if db_user is None:
        raise HTTPException(status_code=404, detail="未找到指定用户")
    
    return db_user

@router.get('/{user_id}', response_model=schema.PlayerAccount, tags=["用户管理"])
async def get_user_by_id(
    user_id: int,
    current_admin: AdminAccount = Depends(deps.get_admin_or_super_admin)
):
    """
    根据用户ID获取用户信息（管理员权限）
    """
    user = await crud_user.get_player_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.put('/{user_id}', response_model=schema.PlayerAccount, tags=["用户管理"])
async def update_user(
    user_id: int,
    user_data: dict,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user)
):
    """
    更新用户信息（超级管理员权限）
    """
    # 转换 dict 为 PlayerAccountUpdate
    update_data = schema.PlayerAccountUpdate(
        user_name=user_data.get('user_name'),
        password=user_data.get('password')
    )
    
    # 处理 is_banned 字段
    player = await crud_user.get_player_by_id(user_id)
    if not player:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    updated_user = await crud_user.update_player(user_id, update_data)
    
    # 处理封禁状态更新
    if 'is_banned' in user_data:
        from server.models import PlayerAccount
        await PlayerAccount.filter(id=user_id).update(is_banned=user_data['is_banned'])
        updated_user = await PlayerAccount.get(id=user_id)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="用户不存在或更新失败")
    return updated_user

@router.delete('/{user_id}', response_model=dict, tags=["用户管理"])
async def delete_user(
    user_id: int,
    current_admin: AdminAccount = Depends(deps.get_super_admin_user)
):
    """
    删除用户（超级管理员权限）
    """
    success = await crud_user.delete_player(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在或删除失败")
    return {"message": "用户删除成功"}