from datetime import datetime
from fastapi import APIRouter
from app.services.redis_service import redis_service
from app.config import redis_settings

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
@router.get("/")
async def get_general_health():
    """Aggregate health check covering API and Database."""
    return {"status": "healthy", "service": "AI Health Checkup & Appointment Coordinator API"}


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


@router.get("/provider")
async def check_provider_status():
    """
    Test and verify Bengaluru Healthcare Provider data service status.
    """
    from app.services.provider_service import provider_service
    from app.providers.bengaluru_provider import BENGALURU_HOSPITALS, BENGALURU_DOCTORS

    hospitals = provider_service.search_hospitals()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "provider": provider_service.provider.provider_name,
        "location": "Bengaluru, Karnataka, India",
        "totalHospitals": len(hospitals),
        "totalDoctors": len(BENGALURU_DOCTORS),
        "supportedLocalities": [
            "Indiranagar", "Whitefield", "Koramangala", "Jayanagar",
            "HSR Layout", "Hebbal", "Bannerghatta Road", "Cunningham Road", "Bellandur"
        ],
        "sampleHospitals": [h["name"] for h in hospitals[:4]],
    }


@router.get("/db")
async def check_db_health():
    """
    Test and verify database health, active engine (PostgreSQL or fallback SQLite), and table stats.
    """
    from app.db.postgres import postgres_service
    from app.db.repository import get_db_connection

    pg_diag = postgres_service.health_check()

    sqlite_stats = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appt_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appointment_slots")
        slot_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appointment_slots WHERE is_available = 1")
        avail_count = cursor.fetchone()[0]
        conn.close()
        sqlite_stats = {
            "connected": True,
            "totalAppointments": appt_count,
            "totalSlots": slot_count,
            "availableSlots": avail_count,
        }
    except Exception as e:
        sqlite_stats = {"connected": False, "error": str(e)}

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "primaryEngine": pg_diag["engine"],
        "postgres": pg_diag,
        "sqliteFallback": sqlite_stats,
    }

