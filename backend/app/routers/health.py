from datetime import datetime
from fastapi import APIRouter
from app.services.redis_service import redis_service
from app.config import redis_settings

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/redis")
async def check_redis_health():
    """
    Test and verify Redis connectivity, mode, and key statistics.
    """
    diag = redis_service.health_check()
    is_healthy = diag.get("connected", False)

    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI Health Coordinator - Redis Layer",
        "redis": diag,
        "ttlConfigurations": {
            "appointmentHoldSeconds": redis_settings.hold_ttl,
            "sessionTtlSeconds": redis_settings.session_ttl,
            "cacheTtlSeconds": redis_settings.cache_ttl,
        },
    }
