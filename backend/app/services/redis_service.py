import json
import logging
from typing import Dict, Any, List, Optional
import redis
import fakeredis

from app.config import redis_settings

logger = logging.getLogger("redis_service")


class RedisService:
    """
    Decoupled Redis Service Layer for AI Health Checkup & Appointment Coordinator.
    Agents and API routes never communicate directly with Redis.

    Managed Keys:
    - chat:{session_id}                     - Chat session conversation history
    - state:{session_id}                    - LangGraph temporary agent state
    - doctor:{doctor_id}:availability       - Doctor availability and slot cache
    - hospital:{hospital_id}:doctors        - Hospital/department doctor directory cache
    - appointment:{appointment_id}:hold     - Temporary appointment reservation with TTL
    - healthcare:{category}                 - Frequently requested healthcare reference data
    """

    def __init__(self):
        self._mode = "standalone"
        self._client = self._initialize_client()

    def _initialize_client(self):
        """
        Attempts to connect to live Redis.
        If unavailable, gracefully falls back to fakeredis in-memory mock with full TTL support.
        """
        try:
            if redis_settings.url:
                client = redis.from_url(
                    redis_settings.url,
                    socket_timeout=1.0,
                    decode_responses=True,
                )
            else:
                client = redis.Redis(
                    host=redis_settings.host,
                    port=redis_settings.port,
                    db=redis_settings.db,
                    password=redis_settings.password or None,
                    socket_timeout=1.0,
                    decode_responses=True,
                )
            client.ping()
            self._mode = "live"
            logger.info("Connected to live Redis at %s:%s", redis_settings.host, redis_settings.port)
            return client
        except Exception as e:
            logger.warning("Live Redis unreachable (%s). Initializing fakeredis in-memory mock.", str(e))
            self._mode = "in-memory (mock)"
            return fakeredis.FakeRedis(decode_responses=True)

    @property
    def mode(self) -> str:
        return self._mode

    # ----------------------------------------------------------------------
    # 1. Health & Connection Diagnostics
    # ----------------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """Tests Redis connection, ping, mode, and key statistics."""
        try:
            pong = self._client.ping()
            total_keys = len(self._client.keys("*"))
            return {
                "connected": bool(pong),
                "mode": self._mode,
                "ping": "PONG" if pong else "FAIL",
                "host": redis_settings.host if self._mode == "live" else "localhost (in-memory)",
                "port": redis_settings.port if self._mode == "live" else 0,
                "database": redis_settings.db,
                "cachedKeysCount": total_keys,
            }
        except Exception as e:
            return {
                "connected": False,
                "mode": self._mode,
                "error": str(e),
            }

    # ----------------------------------------------------------------------
    # 2. Chat Session Storage & Conversation History (chat:{session_id})
    # ----------------------------------------------------------------------
    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history from chat:{session_id}."""
        key = f"chat:{session_id}"
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return []
        return []

    def save_chat_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Appends message to chat:{session_id} and refreshes TTL."""
        key = f"chat:{session_id}"
        history = self.get_chat_history(session_id)
        history.append(message)
        self._client.set(
            key,
            json.dumps(history),
            ex=redis_settings.session_ttl,
        )

    def clear_chat_history(self, session_id: str) -> None:
        """Clears chat history for session."""
        self._client.delete(f"chat:{session_id}")

    # ----------------------------------------------------------------------
    # 3. LangGraph Temporary Agent State (state:{session_id})
    # ----------------------------------------------------------------------
    def save_agent_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """Stores LangGraph temporary state with TTL."""
        key = f"state:{session_id}"
        # Filter non-serializable fields if any
        clean_state = {k: v for k, v in state.items() if not callable(v)}
        self._client.set(
            key,
            json.dumps(clean_state),
            ex=redis_settings.session_ttl,
        )

    def get_agent_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves LangGraph temporary state."""
        key = f"state:{session_id}"
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    # ----------------------------------------------------------------------
    # 4. Doctor Availability Caching (doctor:{doctor_id}:availability)
    # ----------------------------------------------------------------------
    def get_doctor_availability(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """Fetches cached doctor availability."""
        key = f"doctor:{doctor_id}:availability"
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    def set_doctor_availability(
        self, doctor_id: str, availability_data: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Caches doctor availability with configurable TTL."""
        key = f"doctor:{doctor_id}:availability"
        expire = ttl or redis_settings.cache_ttl
        self._client.set(key, json.dumps(availability_data), ex=expire)

    def invalidate_doctor_availability(self, doctor_id: str) -> None:
        """Invalidates doctor availability cache when an appointment changes."""
        self._client.delete(f"doctor:{doctor_id}:availability")

    # ----------------------------------------------------------------------
    # 5. Hospital / Department Doctors Directory (hospital:{hospital_id}:doctors)
    # ----------------------------------------------------------------------
    def get_hospital_doctors(self, hospital_id: str = "main") -> Optional[List[Dict[str, Any]]]:
        """Fetches cached hospital doctors directory."""
        key = f"hospital:{hospital_id}:doctors"
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    def set_hospital_doctors(
        self, hospital_id: str, doctors: List[Dict[str, Any]], ttl: Optional[int] = None
    ) -> None:
        """Caches hospital doctors directory with TTL."""
        key = f"hospital:{hospital_id}:doctors"
        expire = ttl or redis_settings.cache_ttl
        self._client.set(key, json.dumps(doctors), ex=expire)

    # ----------------------------------------------------------------------
    # 6. Temporary Appointment Hold (appointment:{appointment_id}:hold)
    # ----------------------------------------------------------------------
    def hold_appointment_slot(
        self, appointment_id: str, hold_data: Dict[str, Any], ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Temporarily reserves/holds an appointment slot atomically.
        Automatically expires after TTL (configurable period).
        Returns True if hold was successfully placed, False if already held.
        """
        key = f"appointment:{appointment_id}:hold"
        expire = ttl_seconds or redis_settings.hold_ttl
        # Set with NX=True (set only if not already existing)
        acquired = self._client.set(
            key,
            json.dumps(hold_data),
            ex=expire,
            nx=True,
        )
        return bool(acquired)

    def get_appointment_hold(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """Inspects active temporary hold and remaining TTL."""
        key = f"appointment:{appointment_id}:hold"
        raw = self._client.get(key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            ttl = self._client.ttl(key)
            data["remainingHoldSeconds"] = ttl
            return data
        except Exception:
            return None

    def release_appointment_hold(self, appointment_id: str) -> bool:
        """Releases/cancels temporary hold."""
        key = f"appointment:{appointment_id}:hold"
        return bool(self._client.delete(key))

    # ----------------------------------------------------------------------
    # 7. Frequently Requested Healthcare Data (healthcare:{category})
    # ----------------------------------------------------------------------
    def get_cached_healthcare_data(self, category: str) -> Optional[Any]:
        """Retrieves frequently requested reference data."""
        key = f"healthcare:{category}"
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    def set_cached_healthcare_data(
        self, category: str, data: Any, ttl: Optional[int] = None
    ) -> None:
        """Caches frequently requested reference data with TTL."""
        key = f"healthcare:{category}"
        expire = ttl or redis_settings.cache_ttl
        self._client.set(key, json.dumps(data), ex=expire)


# Global singleton instance
redis_service = RedisService()
