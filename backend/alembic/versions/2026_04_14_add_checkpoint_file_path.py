"""add file_path to checkpoints, drop save_snapshots

Revision ID: 2026_04_14_001
Revises: 2026_04_09_002
Create Date: 2026-04-14

Issue #207: 记忆系统文件化改造 Phase 1
- Add file_path, file_size_bytes to checkpoints table
- Drop save_snapshots table (dead code, never used in API)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_04_14_001'
down_revision = '2026_04_09_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add file_path and file_size_bytes to checkpoints
    with op.batch_alter_table('checkpoints', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_path', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('file_size_bytes', sa.Integer(), nullable=True))

    # 2. Drop save_snapshots table (dead code — no routes or frontend ever reference it)
    # SQLite doesn't need to drop FK constraints separately, just drop the table
    op.drop_index(op.f('ix_save_snapshots_id'), table_name='save_snapshots')
    op.drop_table('save_snapshots')


def downgrade() -> None:
    # 1. Recreate save_snapshots table
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_save_snapshots_id'), 'save_snapshots', ['id'], unique=False)

    # 2. Remove file columns from checkpoints
    with op.batch_alter_table('checkpoints', schema=None) as batch_op:
        batch_op.drop_column('file_size_bytes')
        batch_op.drop_column('file_path')
