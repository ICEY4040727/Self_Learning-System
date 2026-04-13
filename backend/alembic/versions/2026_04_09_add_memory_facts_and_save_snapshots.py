"""add memory_facts and save_snapshots tables

Revision ID: 2026_04_09_002
Revises: 2026_04_06_001
Create Date: 2026-04-09 13:00:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_09_002'
down_revision: str | None = '2026_04_06_001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建 memory_facts 表
    op.create_table(
        'memory_facts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=True),
        sa.Column('subject_id', sa.String(length=50), nullable=True),
        sa.Column('fact_type', sa.String(length=30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('concept_tags', sa.JSON(), nullable=True),
        sa.Column('source_message_id', sa.Integer(), nullable=True),
        sa.Column('salience', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_recalled_at', sa.DateTime(), nullable=True),
        sa.Column('recall_count', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_memory_facts_id'), 'memory_facts', ['id'], unique=False)

    # 创建 save_snapshots 表
    op.create_table(
        'save_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    op.create_index(op.f('ix_save_snapshots_id'), 'save_snapshots', ['id'], unique=False)

    # 删除 knowledge 表（如果存在）
    op.drop_table('knowledge')


def downgrade() -> None:
    # 重新创建 knowledge 表
    op.create_table(
        'knowledge',
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('graph', sa.JSON(), nullable=False),
    )

    # 删除 save_snapshots 表
    op.drop_index(op.f('ix_save_snapshots_id'), table_name='save_snapshots')
    op.drop_table('save_snapshots')

    # 删除 memory_facts 表
    op.drop_index(op.f('ix_memory_facts_id'), table_name='memory_facts')
    op.drop_table('memory_facts')
