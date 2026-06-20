"""Tests for audit_user_llm_consistency_job CLI."""
from __future__ import annotations

import logging

import pytest

from backend.models.models import User
from backend.scripts import audit_user_llm_consistency_job as job
from backend.services.user_llm_telemetry import MARKER_AUDIT


def _create_dirty_user(session, username: str = "audit-job-user") -> User:
    user = User(username=username, password_hash="hash")
    session.add(user)
    session.commit()
    user.default_provider = "openai"
    user.model = "legacy-model"
    user.llm_provider_settings = {"openai": {"model": "json-model"}}
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def patrol_session(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(job, "SessionLocal", lambda: db_session)
    return db_session


def test_audit_job_dry_run_exits_non_zero_on_issues(patrol_session, caplog):
    _create_dirty_user(patrol_session, username="audit-dry")
    caplog.set_level(logging.INFO, logger="user_llm.telemetry")

    exit_code = job.main(["--dry-run", "--fail-on-issues"])
    assert exit_code == 1
    assert f"[{MARKER_AUDIT}] event=patrol_metrics" in caplog.text
    assert "legacy_backfill_candidates=" in caplog.text


def test_audit_job_repair_clears_issues(patrol_session, caplog):
    _create_dirty_user(patrol_session, username="audit-repair")
    caplog.set_level(logging.INFO, logger="user_llm.telemetry")

    exit_code = job.main(["--repair", "--fail-on-issues"])
    assert exit_code == 0
    assert f"[{MARKER_AUDIT}] event=patrol_metrics" in caplog.text
