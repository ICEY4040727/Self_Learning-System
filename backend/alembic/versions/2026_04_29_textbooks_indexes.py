"""[TR-X13] add FK indexes on textbooks.course_id / user_id

Postgres does NOT auto-index foreign keys. The original migration only
created ``ix_textbooks_id`` (the PK), so list_textbooks / generate /
delete (all of which filter by ``course_id`` AND ``user_id``) ended up
sequentially scanning the table. Negligible at small data volume but
linearly worse as users accumulate uploads.

Revision ID: 2026_04_29_textbooks_indexes
Revises: 2026_04_27_fsrs_per_user
Create Date: 2026-04-29
"""
from alembic import op


revision = '2026_04_29_textbooks_indexes'
down_revision = '2026_04_27_fsrs_per_user'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_textbooks_course_id', 'textbooks', ['course_id'])
    op.create_index('ix_textbooks_user_id', 'textbooks', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_textbooks_user_id', table_name='textbooks')
    op.drop_index('ix_textbooks_course_id', table_name='textbooks')
