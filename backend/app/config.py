import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class RedisSettings(BaseModel):
    host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: str = os.getenv("REDIS_PASSWORD", "")
    url: str = os.getenv("REDIS_URL", "")

    # Configurable TTLs in seconds
    hold_ttl: int = int(os.getenv("REDIS_HOLD_TTL_SECONDS", "600"))         # 10 minutes
    session_ttl: int = int(os.getenv("REDIS_SESSION_TTL_SECONDS", "86400"))  # 24 hours
    cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "3600"))      # 1 hour


redis_settings = RedisSettings()
