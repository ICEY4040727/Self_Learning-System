"""Risk 2 — database trigger / consistency constraints for User LLM storage."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_db_guard import install_sqlite_user_llm_guard
from backend.services.user_llm_settings import update_provider_settings

from .conftest import create_user


def _guarded_sqlite_sessionmaker():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        install_sqlite_user_llm_guard(connection)
    return sessionmaker(bind=engine), engine


class TestSqliteLegacyOnlyTrigger:
    def test_raw_sql_legacy_only_update_is_rejected(self, monkeypatch):
        monkeypatch.setenv("TESTING", "1")
        factory, engine = _guarded_sqlite_sessionmaker()
        session = factory()
        user = create_user(session, username="db-legacy-only")

        with pytest.raises(IntegrityError, match="legacy LLM columns cannot be updated alone"):
            session.execute(
                text("UPDATE users SET model = :model WHERE id = :id"),
                {"model": "bad-model", "id": user.id},
            )

        session.rollback()
        session.close()
        engine.dispose()

    def test_gateway_full_update_passes_trigger(self, monkeypatch):
        monkeypatch.setenv("TESTING", "1")
        factory, engine = _guarded_sqlite_sessionmaker()
        session = factory()
        user = create_user(session, username="db-gateway-pass")

        update_provider_settings(
            user,
            "openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.example/v1",
        )
        session.commit()
        session.refresh(user)

        assert user.model == "gpt-4.1-mini"
        assert user.llm_provider_settings["openai"]["model"] == "gpt-4.1-mini"
        assert audit_user_llm_consistency(session) == []

        session.close()
        engine.dispose()


class TestJsonLegacyConsistencyDetection:
    def test_audit_detects_json_legacy_model_mismatch(self, db_session):
        user = create_user(db_session, username="db-mismatch")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {
            "openai": {"model": "json-model", "base_url": "https://api.openai.example/v1"},
        }
        db_session.commit()

        issues = audit_user_llm_consistency(db_session)
        assert any(issue.user_id == user.id and issue.field == "model" for issue in issues)

    def test_malformed_json_entry_types_still_persist_but_audit_can_compare(self, db_session):
        """SQLite JSON column has no schema validator; audit catches active-provider drift."""
        user = create_user(db_session, username="db-malformed-json")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {"openai": {"model": 12345}}
        db_session.commit()

        issues = audit_user_llm_consistency(db_session)
        assert issues

    def test_json_only_sql_update_does_not_auto_sync_legacy_mirror(self, monkeypatch):
        """Current SQLite trigger blocks legacy-only writes, not JSON-only drift."""
        monkeypatch.setenv("TESTING", "1")
        factory, engine = _guarded_sqlite_sessionmaker()
        session = factory()
        user = create_user(session, username="db-json-only-sql")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {"openai": {"model": "legacy-model"}}
        session.commit()

        session.execute(
            text("UPDATE users SET llm_provider_settings = :settings WHERE id = :id"),
            {
                "settings": '{"openai": {"model": "json-only-model"}}',
                "id": user.id,
            },
        )
        session.commit()
        session.refresh(user)

        assert user.model == "legacy-model"
        assert user.llm_provider_settings["openai"]["model"] == "json-only-model"
        assert audit_user_llm_consistency(session)

        session.close()
        engine.dispose()
