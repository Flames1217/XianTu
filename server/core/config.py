import secrets
from typing import Literal
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    _env_file = Path(__file__).resolve().parents[1] / ".env"
    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "production"] = "development"

    # JWT - 必须通过环境变量配置，开发环境会自动生成随机密钥
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 天

    @model_validator(mode="after")
    def validate_secret_key(self):
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "SECRET_KEY 必须在生产环境中通过环境变量设置！"
                    "使用 `openssl rand -hex 32` 生成一个随机密钥。"
                )
            # 开发环境自动生成随机密钥
            object.__setattr__(self, "SECRET_KEY", secrets.token_hex(32))
        return self

    # Database (required)
    DDCT_DB_URL: str | None = None

    # Deployment
    APP_VERSION: str = "4.7.7"
    ALLOWED_ORIGINS: str = ""
    CREATE_DEFAULT_ADMIN: bool = False
    DEFAULT_ADMIN_USERNAME: str | None = None
    DEFAULT_ADMIN_PASSWORD: str | None = None

settings = Settings()
