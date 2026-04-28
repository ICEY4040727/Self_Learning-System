"""[TR-A1+A2] split concept_mastery out of progress_trackings (cross-world)

The original ProgressTracking row keyed (course_id, user_id, topic) — concept
mastery was thus per-course. Product semantics calls for "学习画像跨世界共享":
the same user learning "递归" once should be reflected in any course / world
they later open. This migration:

  1. Creates a new `concept_mastery` table keyed by (user_id, concept_id).
  2. Backfills it from ProgressTracking concept rows, picking MAX values per
     (user_id, topic) when the same user studied the concept across multiple
     courses.
  3. Deletes the migrated concept rows from progress_trackings — lesson rows
     stay there, that's the only thing the table tracks now.

Revision ID: 2026_04_27_concept_mastery
Revises: 2026_04_27_fsrs_card_data
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa


revision = '2026_04_27_concept_mastery'
down_revision = '2026_04_27_fsrs_card_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'concept_mastery',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('concept_id', sa.String(length=150), nullable=False),
        sa.Column('mastery_level', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_review', sa.DateTime(), nullable=True),
        sa.Column('next_review', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('user_id', 'concept_id', name='uq_concept_mastery_user_concept'),
    )
    op.create_index('ix_concept_mastery_user', 'concept_mastery', ['user_id'])

    # Backfill from progress_trackings concept rows.
    # MAX(mastery_level) — the highest level the user reached anywhere wins.
    # MAX(last_review) / MAX(next_review) — most recent review wins.
    op.execute(
        """
        INSERT INTO concept_mastery (user_id, concept_id, mastery_level, last_review, next_review)
        SELECT user_id, topic,
               MAX(COALESCE(mastery_level, 0)),
               MAX(last_review),
               MAX(next_review)
        FROM progress_trackings
        WHERE topic_type = 'concept'
        GROUP BY user_id, topic
        """
    )

    # Drop the migrated rows — they're now redundant and would otherwise drift.
    op.execute("DELETE FROM progress_trackings WHERE topic_type = 'concept'")


def downgrade() -> None:
    # Best-effort restore: copy concept_mastery back into progress_trackings,
    # but we have no course_id to attach to. Pick the user's first course as
    # a fallback so the row isn't orphaned. Lossy by design.
    op.execute(
        """
        INSERT INTO progress_trackings (course_id, user_id, topic, topic_type, mastery_level, last_review, next_review)
        SELECT
            (SELECT c.id FROM courses c
             JOIN worlds w ON w.id = c.world_id
             WHERE w.user_id = cm.user_id
             ORDER BY c.id LIMIT 1) AS course_id,
            cm.user_id, cm.concept_id, 'concept', cm.mastery_level, cm.last_review, cm.next_review
        FROM concept_mastery cm
        WHERE EXISTS (
            SELECT 1 FROM courses c
            JOIN worlds w ON w.id = c.world_id
            WHERE w.user_id = cm.user_id
        )
        """
    )
    op.drop_index('ix_concept_mastery_user', table_name='concept_mastery')
    op.drop_table('concept_mastery')
