"""add employee records fields, emergency contacts, probation evaluations

Revision ID: b1c4e9a02f7d
Revises: 7222d653d23a
Create Date: 2026-09-05 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c4e9a02f7d'
down_revision: Union[str, None] = '7222d653d23a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('nom_arabe', sa.String(length=100), nullable=True))
    op.add_column('employees', sa.Column('prenom_arabe', sa.String(length=100), nullable=True))
    op.add_column('employees', sa.Column('date_naissance', sa.Date(), nullable=True))
    op.add_column('employees', sa.Column('date_fin_periode_essai', sa.Date(), nullable=True))
    op.add_column('employees', sa.Column('ville', sa.String(length=100), nullable=True))
    op.add_column('employees', sa.Column('adresse', sa.String(length=255), nullable=True))
    op.add_column('employees', sa.Column('cin', sa.String(length=30), nullable=True))
    op.add_column('employees', sa.Column('cnss', sa.String(length=30), nullable=True))
    op.add_column('employees', sa.Column('type_contrat', sa.String(length=30), nullable=True))
    op.add_column(
        'employees', sa.Column('categorie_professionnelle', sa.String(length=20), nullable=True)
    )
    op.add_column('employees', sa.Column('salaire_base', sa.Numeric(10, 2), nullable=True))
    op.add_column('employees', sa.Column('salaire_net', sa.Numeric(10, 2), nullable=True))
    op.add_column('employees', sa.Column('notes', sa.Text(), nullable=True))

    op.create_table(
        'emergency_contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('nom', sa.String(length=120), nullable=False),
        sa.Column('lien', sa.String(length=60), nullable=True),
        sa.Column('telephone', sa.String(length=30), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'probation_evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('date_evaluation', sa.Date(), nullable=False),
        sa.Column('avis_rh', sa.Text(), nullable=True),
        sa.Column('evaluateur_rh', sa.String(length=120), nullable=True),
        sa.Column('avis_dg', sa.Text(), nullable=True),
        sa.Column('evaluateur_dg', sa.String(length=120), nullable=True),
        sa.Column('decision', sa.String(length=20), nullable=True),
        sa.Column('nouvelle_date_fin', sa.Date(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('probation_evaluations')
    op.drop_table('emergency_contacts')

    op.drop_column('employees', 'notes')
    op.drop_column('employees', 'salaire_net')
    op.drop_column('employees', 'salaire_base')
    op.drop_column('employees', 'categorie_professionnelle')
    op.drop_column('employees', 'type_contrat')
    op.drop_column('employees', 'cnss')
    op.drop_column('employees', 'cin')
    op.drop_column('employees', 'adresse')
    op.drop_column('employees', 'ville')
    op.drop_column('employees', 'date_fin_periode_essai')
    op.drop_column('employees', 'date_naissance')
    op.drop_column('employees', 'prenom_arabe')
    op.drop_column('employees', 'nom_arabe')
