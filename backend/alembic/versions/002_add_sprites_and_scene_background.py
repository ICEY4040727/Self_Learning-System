# ruff: noqa
"""add sprites and scene_background

Revision ID: 002
Revises: 001
Create Date: 2026-03-26
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('characters', sa.Column('sprites', sa.JSON(), nullable=True))
    op.add_column('subjects', sa.Column('scene_background', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('subjects', 'scene_background')
    op.drop_column('characters', 'sprites')
