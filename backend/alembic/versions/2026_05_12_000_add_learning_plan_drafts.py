"""Add learning_plan_drafts table.

Revision ID: 2026_05_12_000
Revises: 2026_05_11_004
Create Date: 2026-05-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "2026_05_12_000"
down_revision = "2026_05_11_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_plan_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_ids", sa.JSON(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("course_form", sa.JSON(), nullable=True),
        sa.Column("material_analysis", sa.JSON(), nullable=True),
        sa.Column("knowledge_blueprint", sa.JSON(), nullable=True),
        sa.Column("course_blueprint", sa.JSON(), nullable=True),
        sa.Column("world_plan", sa.JSON(), nullable=True),
        sa.Column("character_plan", sa.JSON(), nullable=True),
        sa.Column("stage", sa.String(length=40), nullable=False, server_default="blueprint"),
        sa.Column("committed_world_id", sa.Integer(), sa.ForeignKey("worlds.id", ondelete="SET NULL"), nullable=True),
        sa.Column("committed_course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_learning_plan_drafts_id", "learning_plan_drafts", ["id"])
    op.create_index("ix_learning_plan_drafts_user_id", "learning_plan_drafts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_plan_drafts_user_id", table_name="learning_plan_drafts")
    op.drop_index("ix_learning_plan_drafts_id", table_name="learning_plan_drafts")
    op.drop_table("learning_plan_drafts")
