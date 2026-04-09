"""Add title column to Character table

Revision ID: 2026_04_08_001
Revises: 2026_04_06_002
Create Date: 2026-04-08

NOTE: title column is now created in 2026_04_06_000 (base tables).
This migration is kept for downgrade compatibility only.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_04_08_001'
down_revision = '2026_04_06_002'  # add_character_experience 迁移
depends_on = None


def upgrade() -> None:
    # title column is now created in 2026_04_06_000 (base tables)
    pass


def downgrade() -> None:
    # title column is part of base tables, cannot be dropped here
    pass
