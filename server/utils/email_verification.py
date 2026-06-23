"""
邮箱验证码工具
"""
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from server.models import EmailVerificationCode
from server.utils.system_config import get_email_config


def generate_code(length: int = 6) -> str:
    """生成随机验证码"""
    return ''.join(random.choices(string.digits, k=length))


async def create_verification_code(email: str, purpose: str = "register") -> str:
    """
    创建邮箱验证码
    """
    # 使同一邮箱的旧验证码失效
    await EmailVerificationCode.filter(
        email=email,
        purpose=purpose,
        is_used=False
    ).update(is_used=True)

    config = await get_email_config()
    code = generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=config["email_code_expire_minutes"])

    await EmailVerificationCode.create(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=expires_at
    )

    return code


async def verify_code(email: str, code: str, purpose: str = "register") -> bool:
    """
    验证邮箱验证码
    """
    record = await EmailVerificationCode.filter(
        email=email,
        code=code,
        purpose=purpose,
        is_used=False,
        expires_at__gte=datetime.utcnow()
    ).first()

    if record:
        record.is_used = True
        await record.save()
        return True

    return False


async def send_verification_email(email: str, code: str, purpose: str = "register") -> bool:
    """
    发送验证码邮件
    """
    config = await get_email_config()

    if not config["smtp_user"] or not config["smtp_password"]:
        print("[邮件] SMTP未配置，跳过发送")
        return False

    subject_map = {
        "register": "【仙途】注册验证码",
        "reset_password": "【仙途】重置密码验证码",
    }
    subject = subject_map.get(purpose, "【仙途】验证码")

    expire_minutes = config["email_code_expire_minutes"]
    html_content = f"""
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: 'Microsoft YaHei', sans-serif;">
        <h2 style="color: #1e4a9a; text-align: center;">仙途游戏</h2>
        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p>您好，修仙者！</p>
            <p>您的验证码是：</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; color: #1e4a9a; letter-spacing: 8px;">{code}</span>
            </div>
            <p>此验证码 <strong>{expire_minutes} 分钟</strong>内有效，请勿泄露给他人。</p>
        </div>
        <p style="color: #888; font-size: 12px; text-align: center;">
            如果这不是您的操作，请忽略此邮件。
        </p>
    </div>
    """

    from_name = config["smtp_from_name"]
    from_email = config["smtp_from_email"] or config["smtp_user"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = email

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    smtp_host = config["smtp_host"]
    smtp_port = config["smtp_port"]
    smtp_user = config["smtp_user"]
    smtp_password = config["smtp_password"]

    try:
        if smtp_port == 465:
            # SSL
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(
                    from_email,
                    [email],
                    msg.as_string()
                )
        else:
            # TLS
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(
                    from_email,
                    [email],
                    msg.as_string()
                )
        print(f"[邮件] 验证码已发送到 {email}")
        return True
    except Exception as e:
        print(f"[邮件] 发送失败: {e}")
        return False


async def cleanup_expired_codes() -> int:
    """
    清理过期的验证码
    """
    deleted_count = await EmailVerificationCode.filter(
        expires_at__lt=datetime.utcnow()
    ).delete()
    return deleted_count
