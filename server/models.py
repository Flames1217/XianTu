from tortoise import fields
from tortoise.models import Model
from datetime import datetime

# --- 核心账户模型 (无大改动) ---

class PlayerAccount(Model):
    id = fields.IntField(pk=True)
    user_name = fields.CharField(max_length=50, unique=True, description="玩家道号")
    password = fields.CharField(max_length=255, description="哈希后的凭证")
    created_at = fields.DatetimeField(auto_now_add=True, description="创角时间")
    is_banned = fields.BooleanField(default=False, description="是否被封禁")

    class Meta:
        table = "player_accounts"

class AdminAccount(Model):
    id = fields.IntField(pk=True)
    user_name = fields.CharField(max_length=50, unique=True, description="仙官道号")
    password = fields.CharField(max_length=255, description="哈希后的凭证")
    role = fields.CharField(max_length=20, default="admin", description="仙官品阶 (admin, super_admin)")
    created_at = fields.DatetimeField(auto_now_add=True, description="授印时间")

    class Meta:
        table = "admin_accounts"

# --- 游戏设定模型 (静态数据) ---

class World(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True, description="世界名称")
    description = fields.TextField(null=True, description="世界描述")
    era = fields.CharField(max_length=100, null=True, description="时代背景")
    core_rules = fields.JSONField(null=True, description="核心规则")
    creator = fields.ForeignKeyField("models.AdminAccount", related_name="created_worlds", null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "worlds"

class TalentTier(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, description="天资等级名称")
    description = fields.TextField(null=True, description="描述")
    total_points = fields.IntField(description="总可分配点数")
    rarity = fields.IntField(description="稀有度，数值越小越稀有")
    color = fields.CharField(max_length=20, default="#FFFFFF", description="代表颜色")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    class Meta:
        table = "talent_tiers"
        
class Origin(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, description="出身名称")
    description = fields.TextField(null=True, description="描述")
    attribute_modifiers = fields.JSONField(null=True, description="属性修正")
    rarity = fields.IntField(default=3, description="稀有度")
    talent_cost = fields.IntField(default=0, description="天赋点花费")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    
    class Meta:
        table = "core_origins"

class SpiritRoot(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, description="描述")
    base_multiplier = fields.FloatField(description="修炼速度基础倍率")
    talent_cost = fields.IntField(default=0, description="天赋点花费")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    class Meta:
        table = "core_spirit_roots"

class Talent(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True, description="描述")
    effects = fields.JSONField(null=True, description="具体效果")
    rarity = fields.IntField(default=2, description="稀有度")
    talent_cost = fields.IntField(default=1, description="天赋点花费")
    tier = fields.ForeignKeyField("models.TalentTier", related_name="talents", null=True, description="所属天资等级")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    
    class Meta:
        table = "core_talents"

# --- NPC 核心模型 ---
class NpcCharacter(Model):
    id = fields.IntField(pk=True)
    npc_id = fields.CharField(max_length=100, unique=True, description="NPC唯一标识符")
    name = fields.CharField(max_length=100, description="NPC名字")
    
    # 存储NPC的静态基础信息模板
    base_info_template = fields.JSONField(description="角色基础信息模板")
    # 存储NPC的默认存档信息模板
    save_info_template = fields.JSONField(description="角色存档信息模板")
    # 存储NPC的默认AI行为模板
    ai_behavior_template = fields.JSONField(description="AI行为模板")
    
    world = fields.ForeignKeyField("models.World", related_name="npcs", null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "npc_characters"


# --- 玩家角色核心模型 (V3 重构) ---

class CharacterBase(Model):
    """
    角色基础信息 (静态数据)
    这是角色被创建时就已确定的、几乎不会改变的信息。
    """
    id = fields.IntField(pk=True)
    char_id = fields.CharField(max_length=100, unique=True, description="角色唯一ID, e.g., char_1001")
    player = fields.ForeignKeyField("models.PlayerAccount", related_name="characters")
    
    # 角色基础信息的结构化存储
    base_info = fields.JSONField(description="角色基础信息, 对应前端 CharacterBaseInfo")
    
    # 关联的动态存档数据 (一对一)
    game_save = fields.OneToOneField("models.GameSave", related_name="character_base", on_delete=fields.CASCADE)

    is_deleted = fields.BooleanField(default=False, description="是否已删除")
    created_at = fields.DatetimeField(auto_now_add=True)

    @property
    def is_accessible(self) -> bool:
        """角色是否可访问（账号未被封且角色未删除）"""
        return not self.player.is_banned and not self.is_deleted
    
    class Meta:
        table = "character_bases"


class GameSave(Model):
    """
    角色游戏存档 (动态数据)
    这是角色在游戏世界中冒险的实时记录，会频繁发生变化。
    专为联机模式设计，每个角色只有一个存档实例。
    """
    id = fields.IntField(pk=True)
    
    # 存档核心数据，直接映射前端的 SaveSlot 结构
    save_name = fields.CharField(max_length=100, default="云端存档", description="存档名")
    saved_at = fields.DatetimeField(auto_now=True, description="保存时间")
    game_time = fields.CharField(max_length=100, null=True, description="游戏内时间")
    
    world_map = fields.JSONField(null=True, description="世界地图数据")
    save_data = fields.JSONField(null=True, description="核心存档数据 (玩家状态、背包、NPC关系等)")
    
    # 云端同步信息
    last_sync = fields.DatetimeField(auto_now=True, description="最后同步时间")
    version = fields.IntField(default=1, description="数据版本号，用于冲突检测")
    is_dirty = fields.BooleanField(default=False, description="是否有未同步到客户端的数据")

    class Meta:
        table = "game_saves"

# --- 其他辅助模型 (封禁、兑换码等，可按需保留或修改) ---

class PlayerBanRecord(Model):
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField("models.PlayerAccount", related_name="ban_records")
    admin = fields.ForeignKeyField("models.AdminAccount", related_name="ban_actions", null=True)
    reason = fields.TextField(description="封号原因")
    ban_start_time = fields.DatetimeField(auto_now_add=True)
    ban_end_time = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "player_ban_records"

class RedemptionCode(Model):
    id = fields.IntField(pk=True)
    code = fields.CharField(max_length=50, unique=True)
    type = fields.CharField(max_length=50, null=True, description="兑换码类型 (world, talent, etc.)")
    payload = fields.JSONField(null=True)
    max_uses = fields.IntField(default=1)
    times_used = fields.IntField(default=0)
    expires_at = fields.DatetimeField(null=True)
    creator = fields.ForeignKeyField("models.AdminAccount", related_name="created_codes", null=True)
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    class Meta:
        table = "redemption_codes"

class SystemConfig(Model):
   key = fields.CharField(max_length=100, pk=True, description="配置键")
   value = fields.JSONField(description="配置值")

   class Meta:
       table = "system_config"


# --- 创意工坊 ---

class WorkshopItem(Model):
    """
    玩家之间分享的内容载体：
    - settings: 设置备份（dad_game_settings）
    - prompts: 提示词包（promptStorage.exportAll）
    - saves: 存档导出（SavePanel / CharacterManagement 导出格式）
    - start_config: 开局配置（预留）
    """
    id = fields.IntField(pk=True)

    type = fields.CharField(max_length=32, description="内容类型")
    title = fields.CharField(max_length=120, description="标题")
    description = fields.TextField(null=True, description="说明")
    tags = fields.JSONField(null=True, description="标签数组")

    # 核心内容，直接存储导出的 JSON
    payload = fields.JSONField(description="导出的内容")
    game_version = fields.CharField(max_length=32, null=True, description="内容对应的游戏版本")
    data_version = fields.CharField(max_length=32, null=True, description="内容格式版本（预留）")

    author = fields.ForeignKeyField("models.PlayerAccount", related_name="workshop_items", description="作者")

    downloads = fields.IntField(default=0, description="下载次数")
    likes = fields.IntField(default=0, description="点赞数（预留）")

    is_public = fields.BooleanField(default=True, description="是否公开")
    is_deleted = fields.BooleanField(default=False, description="是否删除（软删除）")

    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "workshop_items"


# --- 邮箱验证码 ---

class EmailVerificationCode(Model):
    """邮箱验证码"""
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, description="邮箱地址")
    code = fields.CharField(max_length=10, description="验证码")
    purpose = fields.CharField(max_length=32, default="register", description="用途：register/reset_password")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    expires_at = fields.DatetimeField(description="过期时间")
    is_used = fields.BooleanField(default=False, description="是否已使用")

    class Meta:
        table = "email_verification_codes"


# --- IP限流记录 ---

class IPRateLimitRecord(Model):
    """IP限流记录"""
    id = fields.IntField(pk=True)
    ip_address = fields.CharField(max_length=64, description="IP地址")
    action = fields.CharField(max_length=32, default="register", description="操作类型")
    created_at = fields.DatetimeField(auto_now_add=True, description="记录时间")

    class Meta:
        table = "ip_rate_limit_records"


# --- Online presence and cross-world travel ---

class PlayerPresence(Model):
    id = fields.IntField(pk=True)
    player = fields.OneToOneField(
        "models.PlayerAccount", related_name="presence", on_delete=fields.CASCADE
    )
    last_heartbeat_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "player_presence"


class TravelProfile(Model):
    id = fields.IntField(pk=True)
    player = fields.OneToOneField(
        "models.PlayerAccount", related_name="travel_profile", on_delete=fields.CASCADE
    )
    travel_points = fields.IntField(default=0)
    last_signin_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "travel_profiles"


class WorldInstance(Model):
    id = fields.IntField(pk=True)
    owner = fields.OneToOneField(
        "models.PlayerAccount", related_name="world_instance", on_delete=fields.CASCADE
    )
    owner_char_id = fields.CharField(max_length=100, null=True)
    visibility_mode = fields.CharField(max_length=16, default="public")
    invite_code = fields.CharField(max_length=32, null=True, unique=True)
    allow_offline_travel = fields.BooleanField(default=False)
    allow_map_overwrite = fields.BooleanField(default=False)
    offline_agent_prompt = fields.TextField(null=True)
    revision = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "world_instances"


class WorldInstanceMap(Model):
    id = fields.IntField(pk=True)
    world_instance = fields.ForeignKeyField(
        "models.WorldInstance", related_name="maps", on_delete=fields.CASCADE
    )
    map_id = fields.IntField(default=1)
    map_key = fields.CharField(max_length=100, default="main")
    revision = fields.IntField(default=1)
    payload = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "world_instance_maps"
        unique_together = (("world_instance", "map_id"),)


class TravelSession(Model):
    id = fields.IntField(pk=True)
    visitor = fields.ForeignKeyField(
        "models.PlayerAccount", related_name="travel_sessions", on_delete=fields.CASCADE
    )
    target_world_instance = fields.ForeignKeyField(
        "models.WorldInstance", related_name="travel_sessions", on_delete=fields.CASCADE
    )
    active_slot = fields.CharField(max_length=80, null=True, unique=True)
    state = fields.CharField(max_length=16, default="active")
    end_reason = fields.CharField(max_length=32, null=True)
    entry_map_id = fields.IntField(default=1)
    entry_poi_id = fields.IntField(default=1)
    current_map_id = fields.IntField(default=1)
    current_poi_id = fields.IntField(default=1)
    return_anchor = fields.JSONField(default=dict)
    started_at = fields.DatetimeField(auto_now_add=True)
    ended_at = fields.DatetimeField(null=True)

    class Meta:
        table = "travel_sessions"


class TravelSessionEvent(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField(
        "models.TravelSession", related_name="events", on_delete=fields.CASCADE
    )
    actor = fields.ForeignKeyField(
        "models.PlayerAccount",
        related_name="travel_events",
        null=True,
        on_delete=fields.SET_NULL,
    )
    event_type = fields.CharField(max_length=40)
    map_id = fields.IntField(null=True)
    poi_id = fields.IntField(null=True)
    payload = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "travel_session_events"


class InvasionReport(Model):
    id = fields.IntField(pk=True)
    world_instance = fields.ForeignKeyField(
        "models.WorldInstance", related_name="invasion_reports", on_delete=fields.CASCADE
    )
    session = fields.ForeignKeyField(
        "models.TravelSession",
        related_name="invasion_reports",
        null=True,
        on_delete=fields.SET_NULL,
    )
    unread = fields.BooleanField(default=True)
    summary = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "invasion_reports"
