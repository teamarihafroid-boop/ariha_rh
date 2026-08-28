from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    HR = "hr"
    DG = "dg"
    EMPLOYEE = "employee"


class LeaveRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class NotificationType(str, enum.Enum):
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
