"""Add title column to Character table

Revision ID: add_character_title
Revises: 2026_04_06_002
Create Date: 2026-04-08

This migration adds the title column to the Character table
to support the sage/traveler title field.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_04_08_001'
down_revision = '2026_04_06_002'  # 对应 add_character_experience 迁移
depends_on = None


def upgrade() -> None:
    # 添加 title 列（知者/旅者名片头衔）
    op.add_column(
        'characters',
        sa.Column('title', sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('characters', 'title')
