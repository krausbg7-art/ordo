from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    ENV: str = "dev"
    SECRET_KEY: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_SECONDS: int = 60 * 60 * 24 * 14
    COOKIE_NAME: str = "ordo_session"
    COOKIE_SECURE: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://ordo:ordo@localhost:5432/ordo"
    REDIS_URL: str = "redis://localhost:6379/0"

    # S3 / MinIO
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "ordo-files"
    S3_REGION: str = "us-east-1"

    MAX_UPLOAD_MB: int = 50

    # AI gateway
    MOONSHOT_API_KEY: str = ""
    MOONSHOT_BASE_URL: str = "https://api.moonshot.ai/v1"
    KIMI_MODEL: str = "kimi-k2.6"

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen3.7-plus"
    QWEN_VL_MODEL: str = "qwen3-vl-plus"

    SELFHOST_BASE_URL: str = ""
    SELFHOST_MODEL: str = ""

    AI_ROUTING: str = "config/ai_routing.yaml"
    DATA_RESIDENCY: str = "ru"  # ru | dev

    GOOGLE_CALENDAR_ENABLED: bool = False

    RATE_LIMIT_UPLOAD: str = "20/minute"
    RATE_LIMIT_AI: str = "30/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
