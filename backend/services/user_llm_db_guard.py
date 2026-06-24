"""Database-side helpers for DBA / repair sessions."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

REPAIR_MODE_SETTING = "app.user_llm_repair_mode"

SQLITE_BLOCK_LEGACY_ONLY_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS trg_users_block_legacy_only_llm_update
BEFORE UPDATE ON users
FOR EACH ROW
WHEN (
    (
        OLD.default_provider IS NOT NEW.default_provider OR
        OLD.encrypted_api_key IS NOT NEW.encrypted_api_key OR
        OLD.model IS NOT NEW.model OR
        OLD.llm_base_url IS NOT NEW.llm_base_url
    )
    AND OLD.llm_provider_settings IS NEW.llm_provider_settings
)
BEGIN
    SELECT RAISE(ABORT, 'legacy LLM columns cannot be updated alone; update llm_provider_settings together');
END;
"""


@contextmanager
def user_llm_repair_mode(session: Session) -> Iterator[None]:
    """Enable DB repair mode for the current transaction (PostgreSQL)."""
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        session.execute(text(f"SET LOCAL {REPAIR_MODE_SETTING} = 'on'"))
    try:
        yield
    finally:
        if dialect == "postgresql":
            session.execute(text(f"SET LOCAL {REPAIR_MODE_SETTING} = 'off'"))


def is_postgresql(session: Session) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def install_sqlite_user_llm_guard(connection: Connection) -> None:
    connection.execute(text(SQLITE_BLOCK_LEGACY_ONLY_TRIGGER))


def drop_sqlite_user_llm_guard(connection: Connection) -> None:
    connection.execute(text("DROP TRIGGER IF EXISTS trg_users_block_legacy_only_llm_update"))


def install_postgresql_user_llm_guard(connection: Connection) -> None:
    """Install PostgreSQL triggers that block legacy-only LLM column updates."""
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
    connection.execute(
        text(
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
    )
    connection.execute(
        text(
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
    )
    connection.execute(text("DROP TRIGGER IF EXISTS trg_users_block_legacy_only_llm_update ON users"))
    connection.execute(
        text(
            """
            CREATE TRIGGER trg_users_block_legacy_only_llm_update
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION app.users_block_legacy_only_llm_update()
            """
        )
    )
    connection.execute(text("DROP TRIGGER IF EXISTS trg_users_sync_legacy_llm_mirror ON users"))
    connection.execute(
        text(
            """
            CREATE TRIGGER trg_users_sync_legacy_llm_mirror
            BEFORE UPDATE OF llm_provider_settings, default_provider ON users
            FOR EACH ROW
            EXECUTE FUNCTION app.users_sync_legacy_llm_mirror()
            """
        )
    )


def drop_postgresql_user_llm_guard(connection: Connection) -> None:
    connection.execute(text("DROP TRIGGER IF EXISTS trg_users_sync_legacy_llm_mirror ON users"))
    connection.execute(text("DROP TRIGGER IF EXISTS trg_users_block_legacy_only_llm_update ON users"))
    connection.execute(text("DROP FUNCTION IF EXISTS app.users_sync_legacy_llm_mirror()"))
    connection.execute(text("DROP FUNCTION IF EXISTS app.users_block_legacy_only_llm_update()"))
