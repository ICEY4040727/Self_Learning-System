"""
Alembic 迁移脚本
──────────────────────────────────────────────────────────────
revision: add_course_content
description: 新增 course_materials 和 learning_units 表；
             在 courses 表添加 back_populates 关联。

使用方法：
    alembic revision --autogenerate -m "add_course_content"
    # 然后将本文件内容合并/替换到生成的迁移文件中

    alembic upgrade head
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers — 替换为 alembic 自动生成的值
revision    = "a1b2c3d4e5f6"
down_revision = "<上一个迁移的 revision>"   # ← 填入现有最新 revision
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── course_materials ──────────────────────────────────────
    op.create_table(
        "course_materials",
        sa.Column("id",                sa.Integer(),      primary_key=True, index=True),
        sa.Column("course_id",         sa.Integer(),      sa.ForeignKey("courses.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id",           sa.Integer(),      sa.ForeignKey("users.id",    ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("filename",          sa.String(512),    nullable=False),
        sa.Column("original_filename", sa.String(512),    nullable=False),
        sa.Column("content_type",      sa.String(128),    nullable=False),
        sa.Column("file_size",         sa.Integer(),      nullable=False),
        sa.Column("text_content",      sa.Text(),         nullable=True),
        sa.Column("extraction_status", sa.String(20),     nullable=False, server_default="pending"),
        sa.Column("error_message",     sa.Text(),         nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_course_materials_course_id", "course_materials", ["course_id"])

    # ── learning_units ────────────────────────────────────────
    op.create_table(
        "learning_units",
        sa.Column("id",                     sa.Integer(),  primary_key=True, index=True),
        sa.Column("course_id",              sa.Integer(),  sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("unit_index",             sa.Integer(),  nullable=False),
        sa.Column("title",                  sa.String(256),nullable=False),
        sa.Column("summary",                sa.Text(),     nullable=False),
        sa.Column("raw_content",            sa.Text(),     nullable=False),
        sa.Column("learning_objectives",    sa.JSON(),     nullable=False, server_default="[]"),
        sa.Column("bloom_level",            sa.String(20), nullable=True),
        sa.Column("estimated_minutes",      sa.Integer(),  nullable=False, server_default="20"),
        sa.Column("key_concepts",           sa.JSON(),     nullable=False, server_default="[]"),
        sa.Column("prerequisite_unit_ids",  sa.JSON(),     nullable=False, server_default="[]"),
        sa.Column("dialogue_hints",         sa.JSON(),     nullable=False, server_default="[]"),
        sa.Column("status",                 sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at",             sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",             sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_learning_units_course_id", "learning_units", ["course_id"])
    op.create_index(
        "uq_learning_units_course_index",
        "learning_units",
        ["course_id", "unit_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("learning_units")
    op.drop_table("course_materials")


# ── 同步追加到 Course 模型的说明 (不含在 SQL 中，需手动修改 ORM 模型) ──
"""
在 backend/models/course.py 的 Course 类中追加：

    materials     = relationship("CourseMaterial", back_populates="course", cascade="all, delete-orphan")
    learning_units = relationship("LearningUnit",  back_populates="course", cascade="all, delete-orphan",
                                  order_by="LearningUnit.unit_index")
"""
