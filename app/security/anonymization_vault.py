"""
Secure Ephemeral Mapping Vault for the Data Anonymization Gateway.
Maintains session-scoped, bi-directional mappings between surrogate tokens
and real patient identifiers with TTL automatic expiration.
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple


class VaultSession:
    def __init__(self, session_id: str, ttl_seconds: int = 1800):
        self.session_id = session_id
        self.ttl_seconds = ttl_seconds
        self.created_at = time.time()
        self.last_accessed = self.created_at
        # surrogate -> original plaintext
        self.surrogate_to_real: Dict[str, str] = {}
        # normalized lowercase original -> surrogate
        self.real_to_surrogate: Dict[str, str] = {}
        # counters per entity category for numbered tokens
        self.counters: Dict[str, int] = {}

    def is_expired(self) -> bool:
        return (time.time() - self.last_accessed) > self.ttl_seconds

    def touch(self):
        self.last_accessed = time.time()

    def add(self, surrogate: str, original: str):
        self.touch()
        self.surrogate_to_real[surrogate] = original
        self.real_to_surrogate[original.strip().lower()] = surrogate

    def get_real(self, surrogate: str) -> Optional[str]:
        self.touch()
        return self.surrogate_to_real.get(surrogate)

    def get_surrogate(self, original: str) -> Optional[str]:
        self.touch()
        return self.real_to_surrogate.get(original.strip().lower())

    def next_token_index(self, entity_type: str) -> int:
        idx = self.counters.get(entity_type, 0) + 1
        self.counters[entity_type] = idx
        return idx


class AnonymizationVault:
    """
    Thread-safe ephemeral vault.
    Guarantees that sensitive mapping tables are stored locally in secure memory
    and never transmitted to any external LLM service.
    """

    def __init__(self, default_ttl_seconds: int = 1800):
        self._lock = threading.Lock()
        self._sessions: Dict[str, VaultSession] = {}
        self.default_ttl = default_ttl_seconds

    def get_or_create_session(self, session_id: str) -> VaultSession:
        with self._lock:
            self._cleanup_expired()
            if session_id not in self._sessions:
                self._sessions[session_id] = VaultSession(session_id, self.default_ttl)
            return self._sessions[session_id]

    def store_mapping(self, session_id: str, surrogate: str, original: str):
        session = self.get_or_create_session(session_id)
        with self._lock:
            session.add(surrogate, original)

    def get_mappings_for_session(self, session_id: str) -> Dict[str, str]:
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                if not session.is_expired():
                    session.touch()
                    return dict(session.surrogate_to_real)
                else:
                    del self._sessions[session_id]
            return {}

    def purge_session(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def purge_all(self):
        with self._lock:
            self._sessions.clear()

    def active_session_count(self) -> int:
        with self._lock:
            self._cleanup_expired()
            return len(self._sessions)

    def _cleanup_expired(self):
        expired_keys = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired_keys:
            del self._sessions[sid]


anonymization_vault = AnonymizationVault()
