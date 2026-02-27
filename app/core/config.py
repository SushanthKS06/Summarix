import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Telegram YouTube Summarizer Bot"
    DEBUG: bool = False

    # External APIs (no defaults — must be set in .env)
    GROQ_API_KEY: str
    TELEGRAM_TOKEN: str

    # Databases
    REDIS_URL: str = "redis://redis:6379/0"
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/botdb"
    
    # Task Queue
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    @field_validator("POSTGRES_URL", mode="before")
    @classmethod
    def auto_correct_postgres_url(cls, v: str) -> str:
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
