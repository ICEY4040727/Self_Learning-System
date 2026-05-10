"""add_lesson_plan_and_course_progress

Revision ID: 338f419824e9
Revises: 637c7fa4687b
Create Date: 2026-05-04 07:55:17.501709

Phase 3 Step 3: LessonPlan content column (nullable) + CourseProgress table.
Tables already exist from previous migration — this is a schema stamp.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '338f419824e9'
down_revision: Union[str, None] = '637c7fa4687b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite does not support ALTER constraints; the lesson_plans table
    # already has a working FK from the previous migration. No-op.
    pass


def downgrade() -> None:
    pass

