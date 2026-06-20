"""Shared helpers for User LLM risk-focused tests."""

from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import Session

from backend.models.models import User
from backend.services.user_llm_write_guard import register_user_llm_write_guards


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Fail CI runs that skip tests inside tests/user_llm/ (stress file excluded)."""
    outcome = yield
    report = outcome.get_result()
    if os.environ.get("PYTEST_FAIL_ON_SKIP") != "1":
        return
    if report.when != "call" or not report.skipped:
        return
    if "test_risk3_stress" in item.nodeid:
        return
    pytest.fail(f"Skipped test not allowed in CI: {item.nodeid}")


def create_user(session: Session, username: str = "llm-user") -> User:
    user = User(username=username, password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def guarded_session(db_session, monkeypatch):
    """ORM write guard enabled (production-like)."""
    monkeypatch.setenv("TESTING", "0")
    register_user_llm_write_guards()
    return db_session
