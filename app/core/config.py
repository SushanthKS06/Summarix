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

    @field_validator("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def auto_correct_redis_url(cls, v: str) -> str:
        if not v:
            return v
        
        import re
        
        # Upstash specifically requires rediss:// but gives redis:// in some interfaces
        if "upstash.io" in v and v.startswith("redis://"):
            v = v.replace("redis://", "rediss://", 1)
            
        # Radically remove ANY ssl connection parameter that causes issues with async redis
        # or mismatched schemes in celery.
        # This regex removes ?ssl_cert_reqs=..., &ssl_cert_reqs=..., etc.
        v = re.sub(r'[?&]ssl_[a-zA-Z0-9_]+=[^&]*', '', v)
        
        # If we had parameters but removed them all, the string might end with '?'
        if v.endswith('?'):
            v = v[:-1]
            
        # Clean up any doubled '?' or '&' just in case
        v = v.replace("?&", "?").replace("&&", "&")
        
        # Celery will still complain if the URL has ssl_ in it somewhere and scheme is redis://
        if v.startswith("redis://") and ("ssl" in v.lower() or "rediss_cert" in v.lower()):
            v = v.replace("redis://", "rediss://", 1)
            
        return v

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
