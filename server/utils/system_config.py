"""
系统配置服务层

配置优先级：数据库 > 环境变量 > 默认值

将可动态调整的配置存储在数据库中，支持后台管理界面修改。
这些配置不需要重启服务即可生效。
环境变量作为初始值，首次读取时如果数据库没有会使用环境变量的值。
"""

import os
from typing import Any
from server.models import SystemConfig


# 默认配置值
DEFAULT_CONFIGS = {
    # Cloudflare Turnstile 人机验证
    "turnstile_enabled": True,
    "turnstile_site_key": None,  # 前端用的公钥
    "turnstile_secret_key": None,  # 后端用的私钥
    "turnstile_verify_url": "https://challenges.cloudflare.com/turnstile/v0/siteverify",

    # 邮箱验证
    "email_verification_enabled": False,
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_user": None,
    "smtp_password": None,
    "smtp_from_email": None,
    "smtp_from_name": "仙途游戏",
    "email_code_expire_minutes": 10,

    # IP 限流
    "register_rate_limit_enabled": True,
    "register_rate_limit_max": 5,
    "register_rate_limit_window": 3600,
}

# 环境变量映射（小写配置键 -> 大写环境变量名）
ENV_VAR_MAPPING = {
    "turnstile_enabled": "TURNSTILE_ENABLED",
    "turnstile_site_key": "TURNSTILE_SITE_KEY",
    "turnstile_secret_key": "TURNSTILE_SECRET_KEY",
    "turnstile_verify_url": "TURNSTILE_VERIFY_URL",
    "email_verification_enabled": "EMAIL_VERIFICATION_ENABLED",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_user": "SMTP_USER",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_from_email": "SMTP_FROM_EMAIL",
    "smtp_from_name": "SMTP_FROM_NAME",
    "email_code_expire_minutes": "EMAIL_CODE_EXPIRE_MINUTES",
    "register_rate_limit_enabled": "REGISTER_RATE_LIMIT_ENABLED",
    "register_rate_limit_max": "REGISTER_RATE_LIMIT_MAX",
    "register_rate_limit_window": "REGISTER_RATE_LIMIT_WINDOW",
}


def _parse_env_value(key: str, env_value: str) -> Any:
    """根据配置键的默认值类型解析环境变量值"""
    default = DEFAULT_CONFIGS.get(key)

    # 布尔类型
    if isinstance(default, bool):
        return env_value.lower() in ("true", "1", "yes", "on")

    # 整数类型
    if isinstance(default, int):
        try:
            return int(env_value)
        except ValueError:
            return default

    # 字符串类型
    return env_value


def _get_env_value(key: str) -> Any | None:
    """获取环境变量的值"""
    env_name = ENV_VAR_MAPPING.get(key)
    if not env_name:
        return None

    env_value = os.environ.get(env_name)
    if env_value is None:
        return None

    return _parse_env_value(key, env_value)


def _get_fallback_value(key: str) -> Any:
    """获取回退值：环境变量 > 默认值"""
    env_value = _get_env_value(key)
    if env_value is not None:
        return env_value
    return DEFAULT_CONFIGS.get(key)


async def get_config(key: str, default: Any = None) -> Any:
    """
    获取单个配置值
    优先级：数据库 > 环境变量 > 默认值
    """
    config = await SystemConfig.filter(key=key).first()
    if config:
        return _decode_config_value(config.value)

    # 数据库没有，尝试环境变量
    env_value = _get_env_value(key)
    if env_value is not None:
        return env_value

    # 最后使用默认值
    return DEFAULT_CONFIGS.get(key, default)


async def get_configs(*keys: str) -> dict[str, Any]:
    """批量获取多个配置值"""
    result = {}
    configs = await SystemConfig.filter(key__in=keys).all()

    # 从数据库获取的值
    db_values = {c.key: _decode_config_value(c.value) for c in configs}

    # 合并：数据库 > 环境变量 > 默认值
    for key in keys:
        if key in db_values:
            result[key] = db_values[key]
        else:
            result[key] = _get_fallback_value(key)

    return result


async def set_config(key: str, value: Any) -> None:
    """设置单个配置值"""
    value = _encode_config_value(value)
    await SystemConfig.update_or_create(
        key=key,
        defaults={"value": value}
    )


async def set_configs(configs: dict[str, Any]) -> None:
    """批量设置多个配置值"""
    for key, value in configs.items():
        await set_config(key, value)


async def get_all_configs() -> dict[str, Any]:
    """获取所有配置（合并默认值、环境变量和数据库值）"""
    # 先用默认值
    result = DEFAULT_CONFIGS.copy()

    # 环境变量覆盖
    for key in DEFAULT_CONFIGS:
        env_value = _get_env_value(key)
        if env_value is not None:
            result[key] = env_value

    # 数据库值覆盖
    db_configs = await SystemConfig.all()
    for config in db_configs:
        result[config.key] = _decode_config_value(config.value)

    return result


async def init_default_configs() -> None:
    """
    初始化默认配置到数据库
    仅在配置不存在时创建，使用环境变量或默认值
    """
    for key in DEFAULT_CONFIGS:
        existing = await SystemConfig.filter(key=key).first()
        if not existing:
            value = _encode_config_value(_get_fallback_value(key))
            await SystemConfig.create(key=key, value=value)


def _encode_config_value(value: Any) -> Any:
    """确保 JSONField 可存储标量类型"""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {"__type__": "scalar", "value": value}
    return value


def _decode_config_value(value: Any) -> Any:
    """还原标量包装值"""
    if isinstance(value, dict) and value.get("__type__") == "scalar":
        return value.get("value")
    return value


# 便捷函数：获取特定类别的配置
async def get_turnstile_config() -> dict[str, Any]:
    """获取 Turnstile 相关配置"""
    return await get_configs(
        "turnstile_enabled",
        "turnstile_site_key",
        "turnstile_secret_key",
        "turnstile_verify_url",
    )


async def get_email_config() -> dict[str, Any]:
    """获取邮箱验证相关配置"""
    return await get_configs(
        "email_verification_enabled",
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "smtp_from_email",
        "smtp_from_name",
        "email_code_expire_minutes",
    )


async def get_rate_limit_config() -> dict[str, Any]:
    """获取限流相关配置"""
    return await get_configs(
        "register_rate_limit_enabled",
        "register_rate_limit_max",
        "register_rate_limit_window",
    )
