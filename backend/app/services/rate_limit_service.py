from __future__ import annotations

import redis

from app.config import get_settings

settings = get_settings()
_redis = redis.from_url(settings.redis_url, decode_responses=True)

# 5 failed attempts per account per 15 minutes — generous enough that a
# legitimate user mistyping their password a couple of times never gets
# blocked, tight enough to make a credential-stuffing/brute-force pass on a
# single known account impractical. Keyed by email, not IP: this app's
# accounts are a small known set (HR/DG/employees), not a public signup
# surface, so protecting each account directly is the relevant threat model.
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60


def _key(identifier: str) -> str:
    return f"login_attempts:{identifier.strip().lower()}"


def is_rate_limited(identifier: str) -> bool:
    count = _redis.get(_key(identifier))
    return count is not None and int(count) >= MAX_ATTEMPTS


def register_failed_attempt(identifier: str) -> None:
    key = _key(identifier)
    count = _redis.incr(key)
    if count == 1:
        _redis.expire(key, WINDOW_SECONDS)


def clear_attempts(identifier: str) -> None:
    _redis.delete(_key(identifier))
