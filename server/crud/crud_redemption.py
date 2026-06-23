import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from tortoise.transactions import atomic
from tortoise.exceptions import DoesNotExist, IntegrityError

from server.models import RedemptionCode, PlayerAccount, AdminAccount
from server.schemas.schema import RedemptionCodeCreate

@atomic()
async def create_code(code_data: RedemptionCodeCreate) -> Tuple[Optional[RedemptionCode], str]:
    """
    创生一枚新的仙缘信物，可设定其使用次数。
    """
    try:
        # 检查使用者是否存在
        if code_data.used_by_user_id:
            await PlayerAccount.get(id=code_data.used_by_user_id)

        new_code = await RedemptionCode.create(
            code=code_data.code,
            type=code_data.type,
            payload=code_data.payload,
            max_uses=code_data.max_uses,
            used_by_user_id=code_data.used_by_user_id
        )
        return new_code, "仙缘信物创生成功"
    except IntegrityError:
        return None, f"此信物 ({code_data.code}) 已存在，无法重复创生。"
    except DoesNotExist:
        return None, "指定的用户不存在"
    except Exception as e:
        return None, f"创生仙缘信物失败: {e}"


async def get_code_by_string(code_str: str) -> Tuple[Optional[RedemptionCode], str]:
    """
    根据信物字符串查验其法理。
    """
    try:
        code = await RedemptionCode.get_or_none(code=code_str)
        if not code:
            return None, "未找到此仙缘信物"
        return code, "仙缘信物查验完毕"
    except Exception as e:
        return None, f"查验仙缘信物失败: {e}"


async def get_code_by_id(code_id: int) -> Optional[RedemptionCode]:
    """
    根据ID获取兑换码
    """
    try:
        return await RedemptionCode.get_or_none(id=code_id)
    except Exception:
        return None


@atomic()
async def use_code(code_str: str, user_id: int) -> Tuple[Optional[RedemptionCode], str]:
    """
    消耗一次仙缘信物，并记录使用者。
    此法门将以原子操作确保次数准确无误，并返回更新后的信物状态。
    """
    try:
        user = await PlayerAccount.get_or_none(id=user_id)
        if not user:
            return None, "天命无此人，无法使用信物"

        code_obj = await RedemptionCode.get_or_none(code=code_str)
        if not code_obj:
            return None, "信物不存在"

        if code_obj.max_uses != -1 and code_obj.times_used >= code_obj.max_uses:
            return None, "仙缘已尽，此信物已无法使用"

        code_obj.times_used += 1
        code_obj.used_at = datetime.utcnow()
        code_obj.used_by = user
        await code_obj.save()

        return code_obj, "仙缘信物使用成功"
    except DoesNotExist:
        return None, "信物或用户不存在"
    except Exception as e:
        return None, f"消耗仙缘信物失败: {e}"

async def get_creation_data_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    通过兑换码获取角色创建数据
    根据兑换码类型，返回对应的游戏内容
    """
    code_obj, _ = await get_code_by_string(code)

    if not code_obj:
        return None

    code_type = code_obj.type
    creation_data = {}
    
    # 根据兑换码类型，从数据库获取对应的内容
    if code_type == 'world':
        # 获取随机或指定的世界
        from server.models import World
        worlds = await World.all().limit(1)
        if worlds:
            world = worlds[0]
            creation_data['world_backgrounds'] = [{
                'id': world.id,
                'name': world.name,
                'description': world.description,
                'era': world.era
            }]
            
    elif code_type == 'talent_tier':
        # 获取高级天资
        from server.models import TalentTier
        talent_tiers = await TalentTier.filter(rarity__gte=4).limit(3)
        creation_data['talent_tiers'] = [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'total_points': t.total_points,
                'rarity': t.rarity,
                'color': t.color
            } for t in talent_tiers
        ]
        
    elif code_type == 'origin':
        # 获取稀有出身
        from server.models import Origin
        origins = await Origin.filter(rarity__gte=3).limit(5)
        creation_data['origins'] = [
            {
                'id': o.id,
                'name': o.name,
                'description': o.description,
                'rarity': o.rarity,
                'talent_cost': o.talent_cost
            } for o in origins
        ]
        
    elif code_type == 'spirit_root':
        # 获取高级灵根
        from server.models import SpiritRoot
        spirit_roots = await SpiritRoot.filter(base_multiplier__gte=1.5).limit(3)
        creation_data['spirit_roots'] = [
            {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'base_multiplier': s.base_multiplier,
                'talent_cost': s.talent_cost
            } for s in spirit_roots
        ]
        
    elif code_type == 'talent':
        # 获取稀有天赋
        from server.models import Talent
        talents = await Talent.filter(rarity__gte=4).limit(10)
        creation_data['talents'] = [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'effects': t.effects,
                'rarity': t.rarity,
                'talent_cost': t.talent_cost
            } for t in talents
        ]
    
    # 如果有自定义payload，则合并
    if code_obj.payload and isinstance(code_obj.payload, dict):
        creation_data.update(code_obj.payload)
    
    return creation_data if creation_data else None


async def get_all_codes(skip: int = 0, limit: int = 50) -> List[RedemptionCode]:
    """
    获取所有兑换码（管理员用）
    """
    try:
        return await RedemptionCode.all().order_by('-created_at').offset(skip).limit(limit)
    except Exception:
        return []

@atomic()
async def create_admin_redemption_code(
    code_type: str,
    payload: Optional[Dict[str, Any]] = None,
    max_uses: int = 1,
    admin_id: Optional[int] = None
) -> Tuple[Optional[RedemptionCode], str]:
    """
    (管理员用) 创建新的兑换码
    兑换码本身只是一个凭证，使用时根据类型提供对应的游戏内容
    """
    try:
        admin_obj = None
        if admin_id:
            admin_obj = await AdminAccount.get_or_none(id=admin_id)
            if not admin_obj:
                return None, "指定的管理员不存在"

        # 生成随机码
        code = str(uuid.uuid4()).replace('-', '').upper()[:12]
        
        # 创建兑换码记录
        new_code = await RedemptionCode.create(
            code=code,
            type=code_type,
            payload=payload or {},  # payload可选，用于存储额外配置
            max_uses=max_uses,
            creator=admin_obj
        )
        
        return new_code, "仙缘信物创生成功"
        
    except IntegrityError:
        # 如果生成的码碰撞了（极小概率），重试
        return await create_admin_redemption_code(code_type, payload, max_uses, admin_id)
    except Exception as e:
        return None, f"创建兑换码失败: {e}"