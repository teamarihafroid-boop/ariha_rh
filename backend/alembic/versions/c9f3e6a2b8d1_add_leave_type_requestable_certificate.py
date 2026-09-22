"""add employee_requestable and certificate_kind to leave_types

Revision ID: c9f3e6a2b8d1
Revises: b6d2f4a91c37
Create Date: 2026-09-17 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9f3e6a2b8d1'
down_revision: Union[str, None] = 'b6d2f4a91c37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'leave_types',
        sa.Column('employee_requestable', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'leave_types',
        sa.Column('certificate_kind', sa.String(length=20), nullable=True),
    )
    op.execute(
        "UPDATE leave_types SET employee_requestable = false "
        "WHERE libelle = 'Exceptionnel (mariage/naissance/décès)'"
    )
    op.execute("UPDATE leave_types SET certificate_kind = 'conge_paye' WHERE libelle = 'Congé payé'")
    op.execute(
        "UPDATE leave_types SET certificate_kind = 'recuperation' WHERE libelle = 'Récupération'"
    )


def downgrade() -> None:
    op.drop_column('leave_types', 'certificate_kind')
    op.drop_column('leave_types', 'employee_requestable')
