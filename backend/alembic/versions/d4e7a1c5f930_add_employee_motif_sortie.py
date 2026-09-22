"""add motif_sortie to employees

Revision ID: d4e7a1c5f930
Revises: a1f3c9d2e8b4
Create Date: 2026-09-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e7a1c5f930'
down_revision: Union[str, None] = 'a1f3c9d2e8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('motif_sortie', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'motif_sortie')
