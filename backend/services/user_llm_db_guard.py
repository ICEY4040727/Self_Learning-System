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
