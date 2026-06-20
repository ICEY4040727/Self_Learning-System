"""Tests for User LLM JSON/legacy audit and DBA runner."""
from __future__ import annotations

import pytest

from backend.models.models import User
from backend.scripts.dba_user_llm_runner import DBAUserLLMValidationError, run_dba_user_llm_script
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_settings import update_provider_settings


def _create_user(session, username: str = "audit-user") -> User:
    user = User(username=username, password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_audit_detects_legacy_json_mismatch(db_session):
    user = _create_user(db_session)
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {
        "openai": {"model": "json-model", "base_url": "https://api.openai.example/v1"},
    }
    db_session.commit()

    issues = audit_user_llm_consistency(db_session)
    assert any(issue.field == "model" and issue.user_id == user.id for issue in issues)


def test_audit_ok_after_write_gateway(db_session):
    user = _create_user(db_session, username="audit-ok")
    update_provider_settings(
        user,
        "openai",
        model="gpt-4.1-mini",
        base_url="https://api.openai.example/v1",
    )
    db_session.commit()

    issues = audit_user_llm_consistency(db_session)
    assert issues == []


def test_dba_runner_requires_staging_validation(db_session):
    user = _create_user(db_session, username="dba-gate")

    with pytest.raises(DBAUserLLMValidationError, match="staging-validated"):
        run_dba_user_llm_script(
            db_session,
            lambda session: update_provider_settings(
                session.query(User).filter_by(id=user.id).one(),
                "openai",
                model="gpt-4.1-mini",
            ),
            staging_validated=False,
        )


def test_dba_runner_post_audit_fails_on_inconsistent_legacy(db_session):
    user = _create_user(db_session, username="dba-post")
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {"openai": {"model": "json-model"}}
    db_session.commit()

    with pytest.raises(DBAUserLLMValidationError, match="Post-audit failed"):
        run_dba_user_llm_script(
            db_session,
            lambda session: None,
            staging_validated=True,
            apply=True,
        )
