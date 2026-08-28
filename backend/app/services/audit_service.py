from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog


def log(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_user_id: int,
    actor_email: str,
    description: str = "",
) -> AuditLog:
    """Every write path in this slice must call this with the real
    authenticated session user — never a host-machine fallback. This is the
    fix for the prototype's audit_service.current_user() bug."""
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        description=description,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )
    db.add(entry)
    db.flush()
    return entry
