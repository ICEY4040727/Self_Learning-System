import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.core.config import get_settings

settings = get_settings()

# Ensure data directory exists for SQLite
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.models import models  # noqa: F401
    from backend.services.user_llm_write_guard import register_user_llm_write_guards

    register_user_llm_write_guards()
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_user_llm_columns()
    _ensure_sqlite_character_llm_columns()
    _ensure_sqlite_world_character_context_columns()
    _ensure_sqlite_textbook_link_columns()


def _ensure_sqlite_user_llm_columns():
    """Keep local SQLite files usable when models gain nullable user columns."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("users")}
    columns = {
        "llm_provider_settings": "JSON",
        "temperature": "FLOAT",
        "max_tokens": "INTEGER",
        "model": "VARCHAR(100)",
        "llm_base_url": "VARCHAR(500)",
    }

    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))


def _ensure_sqlite_character_llm_columns():
    """Keep local SQLite files usable when models gain nullable character columns."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "characters" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("characters")}
    columns = {
        "llm_settings": "JSON",
    }

    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE characters ADD COLUMN {name} {ddl}"))


def _ensure_sqlite_world_character_context_columns():
    """Keep local SQLite files usable when world character context columns are added."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "world_characters" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("world_characters")}
    columns = {
        "world_title": "VARCHAR(100)",
        "world_background": "TEXT",
        "relationship_seed": "TEXT",
        "world_greeting": "TEXT",
    }

    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE world_characters ADD COLUMN {name} {ddl}"))


def _ensure_sqlite_textbook_link_columns():
    """Keep local SQLite textbook links aligned with the library model."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "textbooks" not in table_names or "textbook_library" not in table_names:
        return

    existing = {column["name"] for column in inspector.get_columns("textbooks")}

    with engine.begin() as conn:
        if "library_id" not in existing:
            conn.execute(text("ALTER TABLE textbooks ADD COLUMN library_id INTEGER"))
        if "owns_file" not in existing:
            conn.execute(text("ALTER TABLE textbooks ADD COLUMN owns_file BOOLEAN NOT NULL DEFAULT 1"))

        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_textbooks_library_id ON textbooks (library_id)"))
        conn.execute(text("UPDATE textbooks SET owns_file = 1 WHERE owns_file IS NULL"))
        conn.execute(text(
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
