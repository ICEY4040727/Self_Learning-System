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
    drop_sqlite_user_llm_guard,
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
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.users_block_legacy_only_llm_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            legacy_changed boolean;
            json_changed boolean;
            repair_mode boolean;
        BEGIN
            legacy_changed := (
                OLD.default_provider IS DISTINCT FROM NEW.default_provider OR
                OLD.encrypted_api_key IS DISTINCT FROM NEW.encrypted_api_key OR
                OLD.model IS DISTINCT FROM NEW.model OR
                OLD.llm_base_url IS DISTINCT FROM NEW.llm_base_url
            );
            json_changed := OLD.llm_provider_settings IS DISTINCT FROM NEW.llm_provider_settings;
            repair_mode := COALESCE(current_setting('app.user_llm_repair_mode', true), '') = 'on';

            IF legacy_changed AND NOT json_changed AND NOT repair_mode THEN
                RAISE EXCEPTION
                    'legacy LLM columns cannot be updated alone; '
                    'update llm_provider_settings together (full update) '
                    'or SET LOCAL app.user_llm_repair_mode = ''on'' for DBA repair';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.users_sync_legacy_llm_mirror()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            active_provider text;
            entry jsonb;
        BEGIN
            IF NEW.llm_provider_settings IS NULL THEN
                RETURN NEW;
            END IF;

            active_provider := COALESCE(NULLIF(NEW.default_provider, ''), 'claude');
            entry := NEW.llm_provider_settings -> active_provider;
            IF entry IS NULL OR jsonb_typeof(entry) <> 'object' THEN
                RETURN NEW;
            END IF;

            IF entry ? 'encrypted_api_key' THEN
                NEW.encrypted_api_key := entry ->> 'encrypted_api_key';
            END IF;
            IF entry ? 'model' THEN
                NEW.model := entry ->> 'model';
            END IF;
            IF entry ? 'base_url' THEN
                NEW.llm_base_url := entry ->> 'base_url';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_users_block_legacy_only_llm_update ON users")
    op.execute(
        """
        CREATE TRIGGER trg_users_block_legacy_only_llm_update
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION app.users_block_legacy_only_llm_update()
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_users_sync_legacy_llm_mirror ON users")
    op.execute(
        """
        CREATE TRIGGER trg_users_sync_legacy_llm_mirror
        BEFORE UPDATE OF llm_provider_settings, default_provider ON users
        FOR EACH ROW
        EXECUTE FUNCTION app.users_sync_legacy_llm_mirror()
        """
    )


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
        op.execute("DROP TRIGGER IF EXISTS trg_users_sync_legacy_llm_mirror ON users")
        op.execute("DROP TRIGGER IF EXISTS trg_users_block_legacy_only_llm_update ON users")
        op.execute("DROP FUNCTION IF EXISTS app.users_sync_legacy_llm_mirror()")
        op.execute("DROP FUNCTION IF EXISTS app.users_block_legacy_only_llm_update()")
    elif dialect == "sqlite":
        drop_sqlite_user_llm_guard(op.get_bind())
