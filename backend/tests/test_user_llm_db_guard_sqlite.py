"""Tests for SQLite DB trigger blocking legacy-only User LLM updates."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base
from backend.models.models import User
from backend.services.user_llm_db_guard import install_sqlite_user_llm_guard
from backend.services.user_llm_settings import update_provider_settings


def _create_guarded_sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        install_sqlite_user_llm_guard(connection)
    return sessionmaker(bind=engine)(), engine


def test_sqlite_trigger_blocks_legacy_only_update(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    session, engine = _create_guarded_sqlite_session()
    user = User(username="trigger-user", password_hash="hash")
    session.add(user)
    session.commit()

    with pytest.raises(IntegrityError, match="legacy LLM columns cannot be updated alone"):
        session.execute(
            text("UPDATE users SET model = :model WHERE id = :id"),
            {"model": "bad-model", "id": user.id},
        )

    session.rollback()
    session.close()
    engine.dispose()


def test_write_gateway_full_update_passes_sqlite_trigger(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    session, engine = _create_guarded_sqlite_session()
    user = User(username="gateway-user", password_hash="hash")
    session.add(user)
    session.commit()

    update_provider_settings(
        user,
        "openai",
        model="gpt-4.1-mini",
        base_url="https://api.openai.example/v1",
    )
    session.commit()
    session.refresh(user)

    assert user.model == "gpt-4.1-mini"
    session.close()
    engine.dispose()
