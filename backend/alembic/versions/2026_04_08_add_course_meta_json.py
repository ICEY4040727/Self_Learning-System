"""add course meta json

Revision ID: add_course_meta_json
Revises: 
Create Date: 2026-04-08

添加 Course 模型的 meta JSON 列，用于存储表单扩展字段
(current_level, motivation, pace, weekly_minutes, sage_ids 等)
见文档: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md 附录 A
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_course_meta_json'
down_revision = '2026_04_06_002'  # 接入主链
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'courses',
        sa.Column('meta', sa.JSON(), nullable=True, default=dict)
    )


def downgrade() -> None:
    op.drop_column('courses', 'meta')
