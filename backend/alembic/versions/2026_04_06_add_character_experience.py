"""Add experience_points and level to Character table

Revision ID: add_character_experience
Revises: add_user_profiles
Create Date: 2026-04-06

This migration adds experience_points and level fields to the Character table
to support character leveling functionality (POST /api/character/{id}/levelup).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_04_06_002'
down_revision = '2026_04_06_001'  # 对应 add_user_profiles 迁移
depends_on = None


def upgrade() -> None:
    # 添加 experience_points 列（当前经验值）
    op.add_column(
        'characters',
        sa.Column('experience_points', sa.Integer(), nullable=False, server_default='0')
    )
    
    # 添加 level 列（当前等级）
    op.add_column(
        'characters',
        sa.Column('level', sa.Integer(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    op.drop_column('characters', 'level')
    op.drop_column('characters', 'experience_points')
