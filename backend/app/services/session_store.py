from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass

import redis
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

settings = get_settings()
_redis = redis.from_url(settings.redis_url, decode_responses=True)
_signer = URLSafeTimedSerializer(settings.session_secret, salt="ariha-session")

SESSION_COOKIE_NAME = "ariha_session"
CSRF_COOKIE_NAME = "csrf_token"


@dataclass
class SessionData:
    user_id: int
    role: str
    employee_id: int | None
    created_at: float
    last_seen_at: float


def _redis_key(sid: str) -> str:
    return f"session:{sid}"


def _unsign(signed_sid: str) -> str | None:
    """Signature timestamp is fixed at creation and never re-signed on
    refresh, so max_age here naturally enforces the absolute session cap
    without tracking created_at separately."""
    try:
        return _signer.loads(signed_sid, max_age=settings.session_absolute_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None


def create_session(user_id: int, role: str, employee_id: int | None) -> tuple[str, str]:
    sid = secrets.token_urlsafe(32)
    now = time.time()
    data = SessionData(
        user_id=user_id, role=role, employee_id=employee_id, created_at=now, last_seen_at=now
    )
    _redis.set(_redis_key(sid), json.dumps(asdict(data)), ex=settings.session_idle_ttl_seconds)
    csrf_token = secrets.token_urlsafe(24)
    _redis.set(f"csrf:{sid}", csrf_token, ex=settings.session_idle_ttl_seconds)
    return _signer.dumps(sid), csrf_token


def load_session(signed_sid: str | None) -> SessionData | None:
    if not signed_sid:
        return None
    sid = _unsign(signed_sid)
    if not sid:
        return None
    raw = _redis.get(_redis_key(sid))
    if not raw:
        return None
    data = SessionData(**json.loads(raw))
    data.last_seen_at = time.time()
    _redis.set(_redis_key(sid), json.dumps(asdict(data)), ex=settings.session_idle_ttl_seconds)
    _redis.expire(f"csrf:{sid}", settings.session_idle_ttl_seconds)
    return data


def destroy_session(signed_sid: str | None) -> None:
    if not signed_sid:
        return
    sid = _unsign(signed_sid)
    if not sid:
        return
    _redis.delete(_redis_key(sid))
    _redis.delete(f"csrf:{sid}")


def get_csrf_token(signed_sid: str | None) -> str | None:
    if not signed_sid:
        return None
    sid = _unsign(signed_sid)
    if not sid:
        return None
    return _redis.get(f"csrf:{sid}")
