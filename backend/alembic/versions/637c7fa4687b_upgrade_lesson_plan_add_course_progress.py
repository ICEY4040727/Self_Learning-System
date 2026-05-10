"""upgrade_lesson_plan_add_course_progress

Revision ID: 637c7fa4687b
Revises: textbook_library
Create Date: 2026-05-04 07:43:34.605031

NOTE: Some columns may already exist from a partial previous run.
Uses batch_alter_table for SQLite compatibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '637c7fa4687b'
down_revision: Union[str, None] = 'textbook_library'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Upgrade lesson_plans using batch mode (SQLite safe)
    # Batch mode recreates the table, so all changes apply atomically.
    with op.batch_alter_table('lesson_plans', schema=None,
                               recreate='always') as batch_op:
        # Add columns if they don't exist (batch recreate makes this safe)
        batch_op.add_column(sa.Column('title', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('concepts', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('prerequisites', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        # Make content nullable
        batch_op.alter_column('content', existing_type=sa.TEXT(), nullable=True)

    # 2. Create course_progress table (idempotent - won't fail if exists due to batch)
    op.create_table('course_progress',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_lesson_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completed_lesson_ids', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('course_id', 'user_id', name='uq_course_progress_user'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    # 1. Drop course_progress table
    op.drop_table('course_progress')

    # 2. Revert lesson_plans
    with op.batch_alter_table('lesson_plans', schema=None,
                               recreate='always') as batch_op:
        batch_op.alter_column('content', existing_type=sa.TEXT(), nullable=False)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('prerequisites')
        batch_op.drop_column('concepts')
        batch_op.drop_column('order_index')
        batch_op.drop_column('description')
        batch_op.drop_column('title')

