import asyncio
import logging
from functools import wraps
from typing import Callable, Any
from tortoise.exceptions import OperationalError, DBConnectionError

logger = logging.getLogger(__name__)

def db_retry(max_retries: int = 3, delay: float = 1.0):
    """
    数据库操作重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, DBConnectionError, OSError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # 检查是否是连接相关的错误
                    if any(keyword in error_msg for keyword in [
                        'connection', 'timeout', '信号灯超时', 'lost connection',
                        'server has gone away', 'connection lost'
                    ]):
                        if attempt < max_retries:
                            wait_time = delay * (2 ** attempt)  # 指数退避
                            logger.warning(
                                f"数据库连接失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                                f"，{wait_time}秒后重试..."
                            )
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # 非连接错误或已达最大重试次数，直接抛出
                    raise e
                except Exception as e:
                    # 其他异常直接抛出，不重试
                    raise e
            
            # 如果所有重试都失败了
            logger.error(f"数据库操作失败，已重试 {max_retries} 次: {last_exception}")
            raise last_exception
        
        return wrapper
    return decorator