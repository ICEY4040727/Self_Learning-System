"""add_user_llm_db_guard

Revision ID: 2026_06_20_001
Revises: 2026_05_15_000
Create Date: 2026-06-20

Database-side guardrails for users LLM settings:
  - block legacy-only UPDATE (single-field / mirror-only writes)
  - allow full updates when llm_provider_settings changes together
  - optional PostgreSQL repair mode via app.user_llm_repair_mode=on
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from backend.services.user_llm_db_guard import (
    drop_postgresql_user_llm_guard,
    drop_sqlite_user_llm_guard,
    install_postgresql_user_llm_guard,
    install_sqlite_user_llm_guard,
)


revision: str = "2026_06_20_001"
down_revision: str | None = "2026_05_15_000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _dialect() -> str:
    bind = op.get_bind()
    return bind.dialect.name


def _install_postgresql_guard() -> None:
    install_postgresql_user_llm_guard(op.get_bind())


def _install_sqlite_guard() -> None:
    install_sqlite_user_llm_guard(op.get_bind())


def upgrade() -> None:
    dialect = _dialect()
    if dialect == "postgresql":
        _install_postgresql_guard()
    elif dialect == "sqlite":
        _install_sqlite_guard()


def downgrade() -> None:
    dialect = _dialect()
    if dialect == "postgresql":
        drop_postgresql_user_llm_guard(op.get_bind())
    elif dialect == "sqlite":
        drop_sqlite_user_llm_guard(op.get_bind())
