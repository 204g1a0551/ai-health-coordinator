import json
import logging
from typing import Dict, Any, List, Optional, Tuple
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

    # ----------------------------------------------------------------------
    # 8. Generic Cache Methods
    # ----------------------------------------------------------------------
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Retrieves generic cached data by key."""
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    def set_cached_data(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        """Stores generic cached data with TTL."""
        expire = ttl_seconds or redis_settings.cache_ttl
        self._client.set(key, json.dumps(data), ex=expire)

    # ----------------------------------------------------------------------
    # 9. Concurrency & Slot Locking (slot:lock:{doctor_id}:{date}:{time})
    # ----------------------------------------------------------------------
    def _format_slot_lock_key(self, doctor_id: str, date: str, time: str) -> str:
        clean_date = date.replace(" ", "_").replace(",", "").lower()
        clean_time = time.replace(" ", "_").lower()
        return f"slot:lock:{doctor_id}:{clean_date}:{clean_time}"

    def acquire_slot_lock(
        self, doctor_id: str, date: str, time: str, session_id: str, ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Acquires an atomic lock on a specific doctor slot.
        Prevents two users from simultaneously booking the same slot.
        Returns True if acquired, False if already held by another session.
        """
        key = self._format_slot_lock_key(doctor_id, date, time)
        expire = ttl_seconds or redis_settings.slot_lock_ttl
        acquired = self._client.set(
            key,
            json.dumps({"sessionId": session_id, "lockedAt": str(expire)}),
            ex=expire,
            nx=True,
        )
        return bool(acquired)

    def release_slot_lock(self, doctor_id: str, date: str, time: str, session_id: str) -> bool:
        """Releases the slot lock if held by this session."""
        key = self._format_slot_lock_key(doctor_id, date, time)
        raw = self._client.get(key)
        if raw:
            try:
                data = json.loads(raw)
                if data.get("sessionId") == session_id:
                    return bool(self._client.delete(key))
            except Exception:
                return bool(self._client.delete(key))
        return False

    def is_slot_locked(self, doctor_id: str, date: str, time: str) -> Optional[str]:
        """Returns the holder's session_id if the slot is currently locked, else None."""
        key = self._format_slot_lock_key(doctor_id, date, time)
        raw = self._client.get(key)
        if raw:
            try:
                data = json.loads(raw)
                return data.get("sessionId")
            except Exception:
                return "unknown"
        return None

    # ----------------------------------------------------------------------
    # 10. Real-Time Slot Availability Caching (Short configurable TTL)
    # ----------------------------------------------------------------------
    def get_slot_availability(self, doctor_id: str, date: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Retrieves cached slot availability with short TTL."""
        key = f"doctor:{doctor_id}:availability:{date or 'all'}"
        raw = self._client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    def set_slot_availability(
        self, doctor_id: str, date: Optional[str], slots: List[Dict[str, Any]], ttl_seconds: Optional[int] = None
    ) -> None:
        """Caches slot availability for a short configurable period (e.g. 60s)."""
        key = f"doctor:{doctor_id}:availability:{date or 'all'}"
        expire = ttl_seconds or redis_settings.availability_cache_ttl
        self._client.set(key, json.dumps(slots), ex=expire)

    def invalidate_all_doctor_availability(self, doctor_id: str) -> None:
        """Invalidates all cached availability entries for a doctor."""
        keys = self._client.keys(f"doctor:{doctor_id}:*")
        for k in keys:
            self._client.delete(k)
        keys_bengaluru = self._client.keys(f"bengaluru:slots:{doctor_id}:*")
        for k in keys_bengaluru:
            self._client.delete(k)
        keys_healthcare = self._client.keys("healthcare:bengaluru:slots:*")
        for k in keys_healthcare:
            self._client.delete(k)

    # ----------------------------------------------------------------------
    # 11. Auth Rate Limiting (ratelimit:login:{key})
    # ----------------------------------------------------------------------
    def check_login_rate_limit(self, identifier: str, max_attempts: int = 5) -> Tuple[bool, int]:
        """
        Checks if the given identifier (email or IP) is rate-limited.
        Returns (is_allowed, remaining_attempts).
        """
        key = f"ratelimit:login:{identifier.strip().lower()}"
        raw = self._client.get(key)
        if raw is None:
            return True, max_attempts
        try:
            attempts = int(raw)
            if attempts >= max_attempts:
                return False, 0
            return True, max_attempts - attempts
        except Exception:
            return True, max_attempts

    def record_failed_login(self, identifier: str, window_seconds: int = 300) -> int:
        """
        Increments failed login counter and sets TTL window.
        Returns the new attempt count.
        """
        key = f"ratelimit:login:{identifier.strip().lower()}"
        attempts = self._client.incr(key)
        if attempts == 1:
            self._client.expire(key, window_seconds)
        return int(attempts)

    def clear_login_rate_limit(self, identifier: str) -> None:
        """Clears the rate limit counter upon successful authentication."""
        key = f"ratelimit:login:{identifier.strip().lower()}"
        self._client.delete(key)


# Global singleton instance
redis_service = RedisService()


