"""add equipe (team) to employees

Revision ID: e7f2b8a4c103
Revises: d4e7a1c5f930
Create Date: 2026-09-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7f2b8a4c103'
down_revision: Union[str, None] = 'd4e7a1c5f930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('equipe', sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'equipe')
