from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    id: int
    type: NotificationType
    title: str
    body: str
    related_entity_type: str
    related_entity_id: int
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
