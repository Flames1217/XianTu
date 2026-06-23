"""
IP限流工具
"""
from datetime import datetime, timedelta
from server.models import IPRateLimitRecord
from server.utils.system_config import get_rate_limit_config


async def check_rate_limit(ip: str, action: str = "register") -> tuple[bool, int]:
    """
    检查IP是否超过限流
    返回: (是否允许, 剩余次数)
    """
    config = await get_rate_limit_config()

    if not config["register_rate_limit_enabled"]:
        return True, config["register_rate_limit_max"]

    window_seconds = config["register_rate_limit_window"]
    max_requests = config["register_rate_limit_max"]

    window_start = datetime.utcnow() - timedelta(seconds=window_seconds)

    # 清理过期记录
    await IPRateLimitRecord.filter(created_at__lt=window_start).delete()

    # 统计当前窗口内的请求数
    count = await IPRateLimitRecord.filter(
        ip_address=ip,
        action=action,
        created_at__gte=window_start
    ).count()

    remaining = max(0, max_requests - count)

    if count >= max_requests:
        return False, 0

    return True, remaining


async def record_request(ip: str, action: str = "register") -> None:
    """
    记录一次请求
    """
    await IPRateLimitRecord.create(ip_address=ip, action=action)


async def get_rate_limit_reset_time(ip: str, action: str = "register") -> datetime | None:
    """
    获取限流重置时间
    """
    config = await get_rate_limit_config()
    window_seconds = config["register_rate_limit_window"]

    # 找到最早的记录
    oldest = await IPRateLimitRecord.filter(
        ip_address=ip,
        action=action
    ).order_by("created_at").first()

    if oldest:
        return oldest.created_at + timedelta(seconds=window_seconds)
    return None
