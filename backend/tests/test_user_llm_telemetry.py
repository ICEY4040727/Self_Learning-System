"""Tests for User LLM write telemetry markers."""
from __future__ import annotations

import logging

import pytest

from backend.models.models import User
from backend.services.user_llm_settings import update_provider_settings
from backend.services.user_llm_telemetry import MARKER_BLOCKED, MARKER_WRITE
from backend.services.user_llm_write_guard import UserLLMWriteForbidden, register_user_llm_write_guards


def test_gateway_write_emits_marker(db_session, caplog):
    user = User(username="telemetry-user", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    caplog.set_level(logging.INFO, logger="user_llm.telemetry")
    update_provider_settings(user, "openai", model="gpt-4.1-mini")
    db_session.commit()

    joined = caplog.text
    assert MARKER_WRITE in joined
    assert "event=gateway_write" in joined
    assert "dual_write=True" in joined
    assert "trace_id=" in joined


def test_blocked_write_emits_marker(db_session, caplog, monkeypatch):
    monkeypatch.setenv("TESTING", "0")
    register_user_llm_write_guards()

    user = User(username="blocked-user", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    caplog.set_level(logging.WARNING, logger="user_llm.telemetry")
    with pytest.raises(UserLLMWriteForbidden):
        user.model = "raw-write"

    assert MARKER_BLOCKED in caplog.text
    assert "event=blocked_write" in caplog.text


def test_settings_conflict_emits_marker(caplog):
    from fastapi import HTTPException

    from backend.core.conflicts.user_llm_settings import raise_settings_conflict_http
    from backend.services.user_llm_telemetry import MARKER_CONFLICT

    caplog.set_level(logging.WARNING, logger="user_llm.telemetry")
    with pytest.raises(HTTPException) as exc_info:
        raise_settings_conflict_http(
            user_id=42,
            expected_version=3,
            current_version=4,
        )
    assert exc_info.value.status_code == 409
    assert MARKER_CONFLICT in caplog.text
    assert "event=optimistic_lock_conflict" in caplog.text
