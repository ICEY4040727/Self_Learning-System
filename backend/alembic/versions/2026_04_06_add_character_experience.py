"""Add experience_points and level to Character table

Revision ID: 2026_04_06_002
Revises: 2026_04_06_000
Create Date: 2026-04-06

NOTE: experience_points and level columns are now created in 2026_04_06_000 (base tables).
This migration is kept for downgrade compatibility only.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_04_06_002'
down_revision = '2026_04_06_000'  # 基础表迁移
depends_on = None


def upgrade() -> None:
    # experience_points and level columns are now created in 2026_04_06_000 (base tables)
    pass


def downgrade() -> None:
    # These columns are part of base tables, cannot be dropped here
    pass
