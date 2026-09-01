"""add leave_types.is_active

Revision ID: 9a3f1c2b7d4e
Revises: 41174020e35a
Create Date: 2026-09-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9a3f1c2b7d4e'
down_revision: Union[str, None] = '41174020e35a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default backfills existing rows as active; dropped after so the
    # model's Python-side default is the only source of truth going forward.
    op.add_column(
        "leave_types",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("leave_types", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column('leave_types', 'is_active')
