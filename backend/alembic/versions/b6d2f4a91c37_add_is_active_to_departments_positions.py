"""add is_active to departments and positions

Revision ID: b6d2f4a91c37
Revises: a3c7e91b0f5d
Create Date: 2026-09-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6d2f4a91c37'
down_revision: Union[str, None] = 'a3c7e91b0f5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'departments',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'positions',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('positions', 'is_active')
    op.drop_column('departments', 'is_active')
