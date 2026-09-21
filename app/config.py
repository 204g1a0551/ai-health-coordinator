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
    availability_cache_ttl: int = int(os.getenv("AVAILABILITY_CACHE_TTL_SECONDS", "60"))  # 60 seconds near-real-time availability cache
    slot_lock_ttl: int = int(os.getenv("SLOT_LOCK_TTL_SECONDS", "300"))      # 5 minutes slot reservation lock


class PostgresSettings(BaseModel):
    host: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    db: str = os.getenv("POSTGRES_DB", "health_system")
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    url: str = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL", "")


class AuthSettings(BaseModel):
    jwt_secret: str = os.getenv("JWT_SECRET", "super-secret-healthcare-jwt-key-change-in-prod-2026")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    login_rate_limit_attempts: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    login_rate_limit_window: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW", "300"))  # 5 minutes


redis_settings = RedisSettings()
postgres_settings = PostgresSettings()
auth_settings = AuthSettings()
