"""add_user_llm_settings

Revision ID: 2026_05_11_001
Revises: 338f419824e9
Create Date: 2026-05-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2026_05_11_001"
down_revision: str | None = "338f419824e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_present(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing("users", sa.Column("llm_provider_settings", sa.JSON(), nullable=True))
    _add_column_if_missing("users", sa.Column("temperature", sa.Float(), nullable=True))
    _add_column_if_missing("users", sa.Column("max_tokens", sa.Integer(), nullable=True))
    _add_column_if_missing("users", sa.Column("model", sa.String(length=100), nullable=True))
    _add_column_if_missing("users", sa.Column("llm_base_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    _drop_column_if_present("users", "llm_provider_settings")
    _drop_column_if_present("users", "llm_base_url")
