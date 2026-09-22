"""add lieu_naissance to employees

Revision ID: f8a1d5c9e214
Revises: e7f2b8a4c103
Create Date: 2026-09-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8a1d5c9e214'
down_revision: Union[str, None] = 'e7f2b8a4c103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('lieu_naissance', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'lieu_naissance')
