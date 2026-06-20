"""add textbook library links

Revision ID: 2026_05_11_004
Revises: 2026_05_11_003
Create Date: 2026-05-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2026_05_11_004"
down_revision: str | None = "2026_05_11_003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _has_foreign_key(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return constraint_name in {
        fk.get("name")
        for fk in inspector.get_foreign_keys(table_name)
        if fk.get("name")
    }


def upgrade() -> None:
    if not _has_column("textbooks", "library_id"):
        op.add_column(
            "textbooks",
            sa.Column("library_id", sa.Integer(), nullable=True),
        )
    if not _has_column("textbooks", "owns_file"):
        op.add_column(
            "textbooks",
            sa.Column("owns_file", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        )

    if not _has_index("textbooks", "ix_textbooks_library_id"):
        op.create_index("ix_textbooks_library_id", "textbooks", ["library_id"])

    # SQLite cannot add named foreign-key constraints via ALTER TABLE, and the
    # local dev database does not enable FK enforcement. Route-level 409 guards
    # protect the destructive path there; DB-level FK is added for engines that
    # support it.
    if op.get_bind().dialect.name != "sqlite" and not _has_foreign_key(
        "textbooks",
        "fk_textbooks_library_id_textbook_library",
    ):
        op.create_foreign_key(
            "fk_textbooks_library_id_textbook_library",
            "textbooks",
            "textbook_library",
            ["library_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE textbooks SET owns_file = 1 WHERE owns_file IS NULL"))
    bind.execute(sa.text(
        """
        UPDATE textbooks
        SET library_id = (
            SELECT textbook_library.id
            FROM textbook_library
            WHERE textbook_library.user_id = textbooks.user_id
              AND textbook_library.file_path = textbooks.file_path
            ORDER BY textbook_library.id
            LIMIT 1
        ),
        owns_file = 0
        WHERE library_id IS NULL
          AND EXISTS (
            SELECT 1
            FROM textbook_library
            WHERE textbook_library.user_id = textbooks.user_id
              AND textbook_library.file_path = textbooks.file_path
          )
        """
    ))


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite" and _has_foreign_key(
        "textbooks",
        "fk_textbooks_library_id_textbook_library",
    ):
        op.drop_constraint(
            "fk_textbooks_library_id_textbook_library",
            "textbooks",
            type_="foreignkey",
        )
    if _has_index("textbooks", "ix_textbooks_library_id"):
        op.drop_index("ix_textbooks_library_id", table_name="textbooks")
    if _has_column("textbooks", "owns_file"):
        op.drop_column("textbooks", "owns_file")
    if _has_column("textbooks", "library_id"):
        op.drop_column("textbooks", "library_id")
