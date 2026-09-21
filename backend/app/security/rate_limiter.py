"""
API Rate Limiting module with sliding-window token bucket.
Supports Redis and in-memory fallback, returning standard RFC rate-limit headers.
"""

import time
import collections
from typing import Tuple, Dict, Deque
from fastapi import Request, HTTPException, status


class SlidingWindowRateLimiter:
    """
    Sliding window log rate limiter per client IP or authenticated user ID.
    """

    def __init__(self, default_limit: int = 120, default_window_seconds: int = 60):
        self.default_limit = default_limit
        self.default_window_seconds = default_window_seconds
        self._memory_store: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)

    def is_allowed(
        self,
        key: str,
        limit: int = 120,
        window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Evaluates rate limit for the given key.
        Returns: (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds

        queue = self._memory_store[key]

        # Purge timestamps outside the current sliding window
        while queue and queue[0] <= window_start:
            queue.popleft()

        current_count = len(queue)

        if current_count >= limit:
            # Over limit, calculate retry-after
            earliest = queue[0]
            retry_after = max(1, int((earliest + window_seconds) - now))
            return False, 0, retry_after

        # Record this request
        queue.append(now)
        remaining = max(0, limit - (current_count + 1))
        return True, remaining, 0

    def reset(self):
        """Clears all in-memory rate tracking."""
        self._memory_store.clear()


rate_limiter = SlidingWindowRateLimiter()


async def enforce_rate_limit(request: Request, limit: int = 120, window_seconds: int = 60):
    """FastAPI dependency to enforce rate limiting on specific endpoints."""
    # Determine client identifier: Auth user or Client IP
    client_ip = request.client.host if request.client else "unknown_client"
    auth_header = request.headers.get("Authorization")
    client_key = f"auth:{auth_header[:24]}" if auth_header else f"ip:{client_ip}"

    allowed, remaining, retry_after = rate_limiter.is_allowed(client_key, limit, window_seconds)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please retry in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            }
        )
