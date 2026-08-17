"""In-memory per-user rate limiter.

Tracks request timestamps per user ID and enforces:
  - Per-minute limit (sliding window)
  - Per-day limit (rolling 24 h)

No external dependencies (Redis etc.) — resets on server restart, which is
acceptable for the free-tier deployment.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status


class _Bucket:
    """Thread-safe sliding-window counter."""

    def __init__(self):
        self._lock = Lock()
        self._minute_timestamps: list[float] = []
        self._day_timestamps: list[float] = []

    def record(self, now: float) -> dict:
        with self._lock:
            self._minute_timestamps.append(now)
            self._day_timestamps.append(now)
            self._prune(now)
            return {
                "remaining_minute": max(0, _RATE_LIMIT_PER_MINUTE - len(self._minute_timestamps)),
                "remaining_day": max(0, _RATE_LIMIT_PER_DAY - len(self._day_timestamps)),
            }

    def is_limited(self, now: float) -> bool:
        with self._lock:
            self._prune(now)
            if len(self._minute_timestamps) >= _RATE_LIMIT_PER_MINUTE:
                return True
            if len(self._day_timestamps) >= _RATE_LIMIT_PER_DAY:
                return True
            return False

    def _prune(self, now: float) -> None:
        cutoff_min = now - 60
        cutoff_day = now - 86400
        self._minute_timestamps = [t for t in self._minute_timestamps if t > cutoff_min]
        self._day_timestamps = [t for t in self._day_timestamps if t > cutoff_day]


# Configurable limits
_RATE_LIMIT_PER_MINUTE = 10
_RATE_LIMIT_PER_DAY = 50

_buckets: dict[str, _Bucket] = defaultdict(_Bucket)


def check_rate_limit(user_id: str) -> dict:
    """Check and record a request for the given user.

    Returns remaining counts.  Raises 429 if either limit is exceeded.
    """
    now = time.time()
    bucket = _buckets[user_id]

    if bucket.is_limited(now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Max 10 requests/min or 50 requests/day.",
        )

    remaining = bucket.record(now)
    return remaining


def get_rate_limit_headers(user_id: str) -> dict[str, str]:
    """Return headers showing remaining quota (call AFTER check_rate_limit)."""
    now = time.time()
    bucket = _buckets[user_id]
    with bucket._lock:
        bucket._prune(now)
        rem_min = max(0, _RATE_LIMIT_PER_MINUTE - len(bucket._minute_timestamps))
        rem_day = max(0, _RATE_LIMIT_PER_DAY - len(bucket._day_timestamps))
    return {
        "X-RateLimit-Limit-Minute": str(_RATE_LIMIT_PER_MINUTE),
        "X-RateLimit-Remaining-Minute": str(rem_min),
        "X-RateLimit-Limit-Day": str(_RATE_LIMIT_PER_DAY),
        "X-RateLimit-Remaining-Day": str(rem_day),
    }
