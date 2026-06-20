"""Tests for read-path legacy -> JSON self-heal."""
from __future__ import annotations

from backend.models.models import User
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    persist_legacy_backfill,
)


def _create_user(session, username: str = "read-heal-user") -> User:
    user = User(username=username, password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_get_effective_llm_config_persists_legacy_backfill_to_json(db_session):
    user = _create_user(db_session)
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_base_url = "https://api.openai.example/v1"
    user.llm_provider_settings = {}
    db_session.commit()

    config = get_effective_llm_config(user)
    assert config.model == "legacy-model"
    assert config.base_url == "https://api.openai.example/v1"

    db_session.expire_all()
    refreshed = db_session.query(User).filter_by(id=user.id).one()
    assert refreshed.llm_provider_settings == {
        "openai": {
            "model": "legacy-model",
            "base_url": "https://api.openai.example/v1",
        }
    }
    assert audit_user_llm_consistency(db_session) == []


def test_persist_legacy_backfill_is_idempotent(db_session):
    user = _create_user(db_session, username="read-heal-idempotent")
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {}
    db_session.commit()

    assert persist_legacy_backfill(user.id, "openai") is True
    db_session.expire_all()
    first = db_session.query(User).filter_by(id=user.id).one()
    assert first.llm_provider_settings["openai"]["model"] == "legacy-model"

    assert persist_legacy_backfill(user.id, "openai") is False


def test_get_effective_llm_config_skips_persist_when_disabled(db_session):
    user = _create_user(db_session, username="read-heal-disabled")
    user.default_provider = "openai"
    user.model = "legacy-only"
    user.llm_provider_settings = {}
    db_session.commit()

    config = get_effective_llm_config(user, auto_persist_legacy_backfill=False)
    assert config.model == "legacy-only"

    db_session.refresh(user)
    assert user.llm_provider_settings == {}
