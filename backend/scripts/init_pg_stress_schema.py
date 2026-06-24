"""Minimal PostgreSQL schema for nightly User LLM stress tests.

Full ``alembic upgrade head`` fails on fresh PG due to checkpoints/sessions FK
cycle in historical migrations. Stress tests only need ``users`` + DB guard triggers.
"""
from __future__ import annotations

from backend.db.database import engine
from backend.models.models import User
from backend.services.user_llm_db_guard import install_postgresql_user_llm_guard
from backend.services.user_llm_write_guard import register_user_llm_write_guards


def main() -> None:
    register_user_llm_write_guards()
    User.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        install_postgresql_user_llm_guard(conn)
    print("PostgreSQL stress schema ready (users + LLM guard triggers)")


if __name__ == "__main__":
    main()
