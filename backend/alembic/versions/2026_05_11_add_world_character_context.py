"""add_world_character_context

Revision ID: 2026_05_11_003
Revises: 2026_05_11_002
Create Date: 2026-05-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2026_05_11_003"
down_revision: str | None = "2026_05_11_002"
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
    _add_column_if_missing("world_characters", sa.Column("world_title", sa.String(length=100), nullable=True))
    _add_column_if_missing("world_characters", sa.Column("world_background", sa.Text(), nullable=True))
    _add_column_if_missing("world_characters", sa.Column("relationship_seed", sa.Text(), nullable=True))
    _add_column_if_missing("world_characters", sa.Column("world_greeting", sa.Text(), nullable=True))


def downgrade() -> None:
    _drop_column_if_present("world_characters", "world_greeting")
    _drop_column_if_present("world_characters", "relationship_seed")
    _drop_column_if_present("world_characters", "world_background")
    _drop_column_if_present("world_characters", "world_title")
