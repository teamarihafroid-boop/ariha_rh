"""add recruitment core pipeline (job offers, candidates, applications)

Revision ID: c3d8f1a9b2e6
Revises: b1c4e9a02f7d
Create Date: 2026-09-05 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d8f1a9b2e6'
down_revision: Union[str, None] = 'b1c4e9a02f7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'job_offer_statuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('libelle', sa.String(length=60), nullable=False),
        sa.Column('couleur', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('libelle'),
    )

    op.create_table(
        'application_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('libelle', sa.String(length=60), nullable=False),
        sa.Column('ordre', sa.Integer(), nullable=False),
        sa.Column('couleur', sa.String(length=20), nullable=False),
        sa.Column('is_hire_stage', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('libelle'),
    )

    op.create_table(
        'job_offers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titre', sa.String(length=150), nullable=False),
        sa.Column('ville', sa.String(length=100), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.Column('status_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('responsable', sa.String(length=150), nullable=True),
        sa.Column(
            'date_creation',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('date_cloture', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['status_id'], ['job_offer_statuses.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'candidates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nom_complet', sa.String(length=150), nullable=False),
        sa.Column('telephone', sa.String(length=30), nullable=True),
        sa.Column('email', sa.String(length=150), nullable=True),
        sa.Column('ville', sa.String(length=100), nullable=True),
        sa.Column('annees_experience', sa.Numeric(4, 1), nullable=True),
        sa.Column('experience_resume', sa.Text(), nullable=True),
        sa.Column('competences', sa.Text(), nullable=True),
        sa.Column('diplomes', sa.Text(), nullable=True),
        sa.Column('langues', sa.Text(), nullable=True),
        sa.Column('favori', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column(
            'date_ajout', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False
        ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'job_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('job_offer_id', sa.Integer(), nullable=False),
        sa.Column('stage_id', sa.Integer(), nullable=True),
        sa.Column('responsable', sa.String(length=150), nullable=True),
        sa.Column(
            'date_creation',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'date_dernier_mouvement',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id']),
        sa.ForeignKeyConstraint(['job_offer_id'], ['job_offers.id']),
        sa.ForeignKeyConstraint(['stage_id'], ['application_stages.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'candidate_id', 'job_offer_id', name='uq_job_applications_candidate_offer'
        ),
    )

    op.create_table(
        'application_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('texte', sa.Text(), nullable=False),
        sa.Column('auteur_user_id', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['application_id'], ['job_applications.id']),
        sa.ForeignKeyConstraint(['auteur_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('application_comments')
    op.drop_table('job_applications')
    op.drop_table('candidates')
    op.drop_table('job_offers')
    op.drop_table('application_stages')
    op.drop_table('job_offer_statuses')
