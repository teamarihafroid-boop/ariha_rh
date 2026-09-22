from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Employee, LeaveRequest, Notification, NotificationType, User
from app.models.enums import UserRole


def notify_leave_decision(
    db: Session, request: LeaveRequest, approved: bool
) -> Notification | None:
    """Called inside the same transaction as the status update. Only the
    leave owner is notified (EMP-05) — not the submitter, who may be a
    leave-responsable acting on someone else's behalf (RESP-01..03).
    If the owner has no login yet, skip silently rather than fail the
    approval/rejection itself."""
    target_user = db.query(User).filter(User.employee_id == request.employee_id).first()
    if target_user is None:
        return None

    period = f"du {request.date_debut.isoformat()} au {request.date_fin.isoformat()}"
    if approved:
        notif_type = NotificationType.LEAVE_APPROVED
        title = "Demande de congé approuvée"
        body = f"Votre demande de congé {period} a été approuvée."
    else:
        notif_type = NotificationType.LEAVE_REJECTED
        title = "Demande de congé refusée"
        body = f"Votre demande de congé {period} a été refusée."
        if request.decision_comment:
            body += f" Motif : {request.decision_comment}"

    notification = Notification(
        user_id=target_user.id,
        type=notif_type,
        title=title,
        body=body,
        related_entity_type="leave_request",
        related_entity_id=request.id,
    )
    db.add(notification)
    db.flush()
    return notification


def notify_leave_pending(db: Session, request: LeaveRequest) -> list[Notification]:
    """HR-38: HR gets pinged the moment a leave request needs a decision,
    instead of only finding out by checking /hr/demandes. Targets every
    active HR user, not just one — mirrors the self-lockout guard's own
    "there may be more than one HR account" assumption from user_service."""
    employee = db.get(Employee, request.employee_id)
    employee_nom = employee.full_name if employee else "Un collaborateur"
    period = f"du {request.date_debut.isoformat()} au {request.date_fin.isoformat()}"
    title = "Nouvelle demande de congé à traiter"
    body = f"{employee_nom} a soumis une demande de congé {period}."

    hr_users = db.query(User).filter(User.role == UserRole.HR, User.is_active.is_(True)).all()
    notifications = []
    for hr_user in hr_users:
        notification = Notification(
            user_id=hr_user.id,
            type=NotificationType.LEAVE_PENDING,
            title=title,
            body=body,
            related_entity_type="leave_request",
            related_entity_id=request.id,
        )
        db.add(notification)
        notifications.append(notification)
    db.flush()
    return notifications
