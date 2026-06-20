"""add_user_version

Revision ID: 2026_06_20_002
Revises: 2026_06_20_001
Create Date: 2026-06-20

Optimistic-lock version column for users.settings updates.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2026_06_20_002"
down_revision: str | None = "2026_06_20_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("users", "version"):
        op.add_column(
            "users",
            sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("users", "version"):
        op.drop_column("users", "version")
