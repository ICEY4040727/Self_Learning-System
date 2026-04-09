"""add course meta json

Revision ID: 2026_04_08_002
Revises: 2026_04_08_001
Create Date: 2026-04-08

添加 Course 模型的 meta JSON 列，用于存储表单扩展字段
(current_level, motivation, pace, weekly_minutes, sage_ids 等)
见文档: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md 附录 A
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '2026_04_08_002'
down_revision = '2026_04_08_001'  # 接入 add_character_title，形成线性链
branch_labels = None
depends_on = None


def upgrade() -> None:
    # meta column is now created in 2026_04_06_000 (base tables)
    pass


def downgrade() -> None:
    # meta column is part of base tables, cannot be dropped here
    pass
