"""add_character_llm_settings

Revision ID: 2026_05_11_002
Revises: 2026_05_11_001
Create Date: 2026-05-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2026_05_11_002"
down_revision: str | None = "2026_05_11_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("characters", "llm_settings"):
        op.add_column("characters", sa.Column("llm_settings", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _has_column("characters", "llm_settings"):
        op.drop_column("characters", "llm_settings")
