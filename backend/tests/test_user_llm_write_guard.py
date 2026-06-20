"""Tests for ORM runtime guard on User LLM column writes."""
from __future__ import annotations

import pytest
from sqlalchemy import update

from backend.models.models import User
from backend.services.user_llm_settings import update_provider_settings
from backend.services.user_llm_write_guard import (
    UserLLMWriteForbidden,
    register_user_llm_write_guards,
)


@pytest.fixture
def guarded_session(db_session, monkeypatch):
    monkeypatch.setenv("TESTING", "0")
    register_user_llm_write_guards()
    return db_session


def _create_user(session) -> User:
    user = User(username="guard-user", password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_direct_assignment_is_blocked(guarded_session):
    user = _create_user(guarded_session)

    with pytest.raises(UserLLMWriteForbidden, match="User\\.model"):
        user.model = "gpt-4o"


def test_setattr_is_blocked(guarded_session):
    user = _create_user(guarded_session)

    with pytest.raises(UserLLMWriteForbidden, match="User\\.temperature"):
        setattr(user, "temperature", 0.2)


def test_write_gateway_allows_persisted_update(guarded_session):
    user = _create_user(guarded_session)

    update_provider_settings(
        user,
        "openai",
        model="gpt-4.1-mini",
        base_url="https://api.openai.example/v1",
    )
    guarded_session.commit()
    guarded_session.refresh(user)

    assert user.default_provider == "openai"
    assert user.model == "gpt-4.1-mini"
    assert user.llm_base_url == "https://api.openai.example/v1"


def test_bulk_update_is_blocked(guarded_session):
    user = _create_user(guarded_session)

    with pytest.raises(UserLLMWriteForbidden, match="bulk UPDATE"):
        guarded_session.execute(
            update(User).where(User.id == user.id).values(model="gpt-4o")
        )


def test_guard_disabled_in_testing_mode(db_session, monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    register_user_llm_write_guards()
    user = _create_user(db_session)

    user.model = "legacy-fixture-value"
    db_session.commit()
    db_session.refresh(user)

    assert user.model == "legacy-fixture-value"
