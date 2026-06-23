from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from server.core import security
from server.core.config import settings
from server.crud import crud_user
from server.schemas import schema
from server.api.api_v1 import deps
from server.models import PlayerAccount
from server.utils.turnstile import verify_turnstile
from server.utils.rate_limit import check_rate_limit, record_request
from server.utils.email_verification import (
    create_verification_code,
    verify_code,
    send_verification_email,
)
from server.utils.system_config import (
    get_config,
    get_turnstile_config,
    get_rate_limit_config,
)

router = APIRouter()


def _get_client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


async def _require_turnstile(request: Request, token: str | None) -> None:
    """Turnstile验证（如果启用）"""
    config = await get_turnstile_config()

    if not config["turnstile_enabled"]:
        return

    if not config["turnstile_secret_key"]:
        if settings.ENVIRONMENT == "development":
            return
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Turnstile 未配置（缺少 turnstile_secret_key）",
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 Turnstile 验证令牌，请先完成 Cloudflare 人机验证",
        )

    try:
        ok, codes = await verify_turnstile(token=token, remote_ip=_get_client_ip(request))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Turnstile 验证服务不可用，请稍后重试",
        ) from e

    if ok:
        return

    detail = "Turnstile 验证失败"
    if settings.ENVIRONMENT == "development" and codes:
        detail = f"{detail}: {', '.join(codes)}"

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def _check_rate_limit(request: Request) -> None:
    """IP限流检查"""
    config = await get_rate_limit_config()

    if not config["register_rate_limit_enabled"]:
        return

    ip = _get_client_ip(request) or "unknown"
    allowed, remaining = await check_rate_limit(ip, "register")

    if not allowed:
        window_minutes = config["register_rate_limit_window"] // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"注册请求过于频繁，请{window_minutes}分钟后再试",
        )


@router.get("/test_no_deps", tags=["测试"])
async def test_no_dependencies():
    """测试没有依赖项的端点"""
    return {"message": "在auth router中，没有依赖项", "status": "ok"}


@router.get("/security-settings", response_model=schema.SecuritySettingsResponse)
async def get_security_settings():
    """
    获取当前安全设置（公开接口）
    前端根据这个决定显示哪种验证方式
    """
    turnstile_config = await get_turnstile_config()
    rate_limit_config = await get_rate_limit_config()
    email_enabled = await get_config("email_verification_enabled")

    return {
        "turnstile_enabled": turnstile_config["turnstile_enabled"],
        "turnstile_site_key": turnstile_config["turnstile_site_key"],
        "email_verification_enabled": email_enabled,
        "rate_limit_enabled": rate_limit_config["register_rate_limit_enabled"],
        "rate_limit_max": rate_limit_config["register_rate_limit_max"],
        "rate_limit_window": rate_limit_config["register_rate_limit_window"],
    }


@router.post("/send-email-code", response_model=schema.SendEmailCodeResponse)
async def send_email_code(request: Request, data: schema.SendEmailCodeRequest):
    """
    发送邮箱验证码
    """
    email_enabled = await get_config("email_verification_enabled")
    if not email_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱验证未启用",
        )

    # IP限流检查
    await _check_rate_limit(request)

    # 验证邮箱格式
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式不正确",
        )

    # 创建验证码
    code = await create_verification_code(data.email, data.purpose)

    # 发送邮件
    success = await send_verification_email(data.email, code, data.purpose)

    if success:
        # 记录请求（用于限流）
        ip = _get_client_ip(request) or "unknown"
        await record_request(ip, "send_email_code")
        return {"success": True, "message": "验证码已发送，请查收邮件"}
    else:
        return {"success": False, "message": "验证码发送失败，请稍后重试"}


@router.post("/token", response_model=schema.Token)
async def login_for_access_token(request: Request, login_data: schema.LoginRequest):
    """
    **修者登录**

    用道号和凭证换取访问令牌。
    """
    await _require_turnstile(request, login_data.turnstile_token)
    player = await crud_user.authenticate_player(
        user_name=login_data.username, password=login_data.password
    )
    if not player:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="道号或凭证错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(
        data={"sub": str(player.id), "account_type": "player"}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=schema.PlayerAccount)
async def register_player(request: Request, player_in: schema.PlayerAccountCreateFull):
    """
    **接引新修者**

    创建新的修者账号。
    支持三种验证方式（按优先级）：
    1. Turnstile验证（如果启用且提供了token）
    2. 邮箱验证码（如果启用且提供了email和code）
    3. 无验证（如果都未启用）
    """
    # IP限流检查
    await _check_rate_limit(request)

    # 获取配置
    turnstile_config = await get_turnstile_config()
    email_enabled = await get_config("email_verification_enabled")
    turnstile_enabled = turnstile_config["turnstile_enabled"]

    # 验证逻辑
    verified = False

    # 1. 尝试Turnstile验证
    if turnstile_enabled and player_in.turnstile_token:
        await _require_turnstile(request, player_in.turnstile_token)
        verified = True

    # 2. 尝试邮箱验证
    if not verified and email_enabled:
        if player_in.email and player_in.email_code:
            code_valid = await verify_code(player_in.email, player_in.email_code, "register")
            if not code_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱验证码错误或已过期",
                )
            verified = True
        elif turnstile_enabled:
            # 如果Turnstile也启用但没提供token，需要验证
            pass
        else:
            # 邮箱验证启用但没提供
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供邮箱验证码",
            )

    # 3. 如果两种验证都启用，至少要通过一种
    if not verified and (turnstile_enabled or email_enabled):
        if turnstile_enabled and email_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请完成Turnstile验证或邮箱验证",
            )
        elif turnstile_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请完成Turnstile验证",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供邮箱验证码",
            )

    # 创建账号
    player_create_data = schema.PlayerAccountCreate(
        user_name=player_in.user_name,
        password=player_in.password
    )

    new_player, message = await crud_user.create_player(player_data=player_create_data)
    if not new_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # 记录成功注册（用于限流统计）
    ip = _get_client_ip(request) or "unknown"
    await record_request(ip, "register")

    return new_player


@router.get("/me", response_model=schema.PlayerAccount)
async def read_current_user(
    current_user: PlayerAccount = Depends(deps.get_current_user),
):
    """
    **获取当前修者信息**

    需要有效的访问令牌。
    """
    return current_user
