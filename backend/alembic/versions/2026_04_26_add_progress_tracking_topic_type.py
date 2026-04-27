"""[TODO-T3] add topic_type to progress_trackings

Distinguishes per-concept rows (mastery_tracker) from per-lesson rows
(teaching_planner) that previously shared the topic column.

Revision ID: 2026_04_26_topic_type
Revises: 2026_04_25_temporal
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa


revision = '2026_04_26_topic_type'
down_revision = '2026_04_25_temporal'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Default existing rows to 'concept' — that was the original semantics
    # used by mastery_tracker. teaching_planner started writing lesson rows
    # later and conflated the two; downstream code now sets the type
    # explicitly for new rows.
    op.add_column(
        'progress_trackings',
        sa.Column(
            'topic_type', sa.String(20), nullable=False,
            server_default='concept',
            comment="'concept' (concept_tag from MemoryFact) or 'lesson' (course lesson title)",
        ),
    )
    op.create_index(
        'ix_progress_trackings_course_topic_type',
        'progress_trackings',
        ['course_id', 'topic_type'],
    )


def downgrade() -> None:
    op.drop_index('ix_progress_trackings_course_topic_type', table_name='progress_trackings')
    op.drop_column('progress_trackings', 'topic_type')
