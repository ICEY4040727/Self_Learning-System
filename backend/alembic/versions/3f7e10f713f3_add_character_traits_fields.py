"""add_character_traits_fields

Revision ID: 3f7e10f713f3
Revises: 2026_04_14_001
Create Date: 2026-04-14 22:44:39.387534
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "3f7e10f713f3"
down_revision: str | None = "2026_04_14_001"
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


def _ensure_not_null(
    table_name: str,
    column_name: str,
    *,
    column_type: sa.types.TypeEngine,
    server_default: str | None = None,
) -> None:
    if not _has_column(table_name, column_name):
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column = next(
        (item for item in inspector.get_columns(table_name) if item["name"] == column_name),
        None,
    )
    if column is None or column.get("nullable") is False:
        return

    op.alter_column(
        table_name,
        column_name,
        existing_type=column_type,
        nullable=False,
        existing_server_default=sa.text(server_default) if server_default else None,
    )


def upgrade() -> None:
    _add_column_if_missing(
        "characters",
        sa.Column(
            "traits",
            sa.JSON(),
            nullable=True,
            comment="性格参数 5 维 {strictness, pace, questioning, warmth, humor}",
        ),
    )
    _add_column_if_missing(
        "characters",
        sa.Column(
            "system_prompt_template",
            sa.Text(),
            nullable=True,
            comment="自定义 system prompt 模板",
        ),
    )
    _add_column_if_missing(
        "characters",
        sa.Column(
            "template_name",
            sa.String(length=50),
            nullable=True,
            comment="角色模板 key，如 socrates/einstein",
        ),
    )
    _add_column_if_missing(
        "characters",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=True,
            comment="是否可用于教学（DD1: 替代 TeacherPersona.is_active）",
        ),
    )
    _ensure_not_null(
        "characters",
        "experience_points",
        column_type=sa.INTEGER(),
        server_default="0",
    )
    _ensure_not_null(
        "characters",
        "level",
        column_type=sa.INTEGER(),
        server_default="1",
    )


def downgrade() -> None:
    if _has_column("characters", "level"):
        op.alter_column(
            "characters",
            "level",
            existing_type=sa.INTEGER(),
            nullable=True,
            existing_server_default=sa.text("1"),
        )
    if _has_column("characters", "experience_points"):
        op.alter_column(
            "characters",
            "experience_points",
            existing_type=sa.INTEGER(),
            nullable=True,
            existing_server_default=sa.text("0"),
        )
    _drop_column_if_present("characters", "is_active")
    _drop_column_if_present("characters", "template_name")
    _drop_column_if_present("characters", "system_prompt_template")
    _drop_column_if_present("characters", "traits")
