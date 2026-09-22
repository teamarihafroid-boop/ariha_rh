"""add leave_pending notification type

Revision ID: a1f3c9d2e8b4
Revises: 882c031558ac
Create Date: 2026-09-15 14:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a1f3c9d2e8b4"
down_revision: str | None = "882c031558ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The initial migration created this enum with sa.Enum(...) values equal
    # to the Python NotificationType members' *names* (LEAVE_APPROVED,
    # LEAVE_REJECTED) — SQLAlchemy's default native-enum behavior — not their
    # lowercase .value strings. Match that existing convention, not the
    # Python-side lowercase value, or inserts fail with "invalid input value
    # for enum notification_type".
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'LEAVE_PENDING'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enum types — removing a value would
    # require rebuilding the type and every column/index that uses it.
    # Left as a no-op, matching the general one-directional-enum-growth
    # posture already accepted elsewhere in this codebase's migrations.
    pass
