"""add t_valid/t_invalid to memory_facts

Revision ID: 2026_04_25_temporal
Revises:
Create Date: 2026-04-25 20:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '2026_04_25_temporal'
down_revision = '2026_04_25_textbooks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('memory_facts', sa.Column('t_valid', sa.DateTime(), nullable=True, comment='记忆生效时间（事实开始成立的时刻）'))
    op.add_column('memory_facts', sa.Column('t_invalid', sa.DateTime(), nullable=True, comment='记忆失效时间（事实被纠正/过期的时刻）'))


def downgrade() -> None:
    op.drop_column('memory_facts', 't_invalid')
    op.drop_column('memory_facts', 't_valid')