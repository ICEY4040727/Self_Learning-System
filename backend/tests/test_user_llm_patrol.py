"""Tests for scheduled User LLM patrol + repair."""
from __future__ import annotations

import logging

from backend.models.models import User
from backend.services.user_llm_repair import (
    patrol_exit_code,
    patrol_user_llm_consistency,
)
from backend.services.user_llm_telemetry import MARKER_AUDIT


def _create_user(session, username: str = "patrol-user") -> User:
    user = User(username=username, password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_patrol_repair_heals_legacy_json_mismatch(db_session):
    user = _create_user(db_session)
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {
        "openai": {"model": "json-model", "base_url": "https://api.openai.example/v1"},
    }
    db_session.commit()

    result = patrol_user_llm_consistency(db_session, apply_repair=True)
    assert result.pre_issues
    assert result.repaired_user_count == 1
    assert result.post_issues == []


def test_patrol_dry_run_does_not_mutate(db_session):
    user = _create_user(db_session, username="patrol-dry")
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {"openai": {"model": "json-model"}}
    db_session.commit()

    result = patrol_user_llm_consistency(db_session, apply_repair=False)
    assert result.post_issues
    db_session.refresh(user)
    assert user.model == "legacy-model"


def test_patrol_job_fail_on_issues_exits_non_zero(db_session, caplog):
    user = _create_user(db_session, username="patrol-exit")
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {"openai": {"model": "json-model"}}
    db_session.commit()

    caplog.set_level(logging.ERROR, logger="user_llm.telemetry")
    result = patrol_user_llm_consistency(db_session, apply_repair=False)
    exit_code = patrol_exit_code(result, fail_on_issues=True)
    assert exit_code == 1
    assert f"[{MARKER_AUDIT}] event=patrol_failed" in caplog.text


def test_patrol_job_repair_clears_issues(db_session):
    user = _create_user(db_session, username="patrol-repair-cli")
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {"openai": {"model": "json-model"}}
    db_session.commit()

    result = patrol_user_llm_consistency(db_session, apply_repair=True)
    exit_code = patrol_exit_code(result, fail_on_issues=True)
    assert exit_code == 0
    assert result.post_issues == []
