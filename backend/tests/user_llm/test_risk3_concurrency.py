"""Risk 3 — concurrency controls keep JSON and Legacy aligned."""
from __future__ import annotations

import pytest
from sqlalchemy.orm.exc import StaleDataError

from backend.models.models import User
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_settings import (
    lock_user_for_update,
    update_provider_settings,
)
from backend.tests.conftest import TestSessionLocal

from .conftest import create_user


def _put_settings(client, auth_headers, payload: dict):
    version_resp = client.get("/api/settings", headers=auth_headers)
    assert version_resp.status_code == 200, version_resp.text
    payload = {**payload, "version": version_resp.json()["version"]}
    return client.put("/api/settings", json=payload, headers=auth_headers)


class TestOptimisticLockApi:
    def test_get_settings_includes_version(self, client, auth_headers, db_session):
        user = db_session.query(User).filter_by(username="testuser").one()
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["version"] == user.version

    def test_put_settings_rejects_stale_version(self, client, auth_headers):
        baseline = client.get("/api/settings", headers=auth_headers).json()["version"]
        first = _put_settings(
            client,
            auth_headers,
            {"default_provider": "openai", "temperature": 0.5},
        )
        assert first.status_code == 200, first.text

        stale = client.put(
            "/api/settings",
            json={"version": baseline, "default_provider": "claude"},
            headers=auth_headers,
        )
        assert stale.status_code == 409, stale.text
        detail = stale.json()["detail"]
        assert detail["code"] == "user_llm_settings_conflict"
        assert detail["expected_version"] == baseline
        assert detail["current_version"] == baseline + 1


class TestPessimisticLockGateway:
    def test_lock_user_for_update_serializes_updates(self, db_session):
        user = create_user(db_session, username="risk3-lock")
        start_version = user.version

        locked = lock_user_for_update(db_session, user.id)
        update_provider_settings(locked, "openai", model="gpt-4.1-mini")
        db_session.commit()
        db_session.refresh(locked)

        assert locked.version == start_version + 1
        assert audit_user_llm_consistency(db_session) == []


class TestConcurrentGatewayWrites:
    def test_sequential_locked_updates_stay_consistent(self, db_session):
        """单线程模拟并发：行锁串行化后 JSON 与 Legacy 始终对齐。"""
        user = create_user(db_session, username="risk3-serial")
        user_id = user.id
        start_version = user.version

        for index in range(10):
            locked = lock_user_for_update(db_session, user_id)
            update_provider_settings(
                locked,
                "openai",
                model=f"gpt-thread-{index}",
                base_url="https://api.openai.example/v1",
            )
            db_session.commit()

        db_session.expire_all()
        final = db_session.get(User, user_id)
        assert final is not None
        assert final.version == start_version + 10
        assert final.model == "gpt-thread-9"
        assert final.llm_provider_settings["openai"]["model"] == final.model
        assert audit_user_llm_consistency(db_session) == []

    def test_unserialized_sessions_raise_stale_data_on_lost_update(self, db_session):
        user = create_user(db_session, username="risk3-stale")
        user_id = user.id
        start_version = user.version

        session_a = TestSessionLocal()
        session_b = TestSessionLocal()
        try:
            user_a = session_a.get(User, user_id)
            user_b = session_b.get(User, user_id)
            assert user_a is not None and user_b is not None

            update_provider_settings(user_a, "openai", model="writer-a")
            session_a.commit()

            update_provider_settings(user_b, "openai", model="writer-b")
            with pytest.raises(StaleDataError):
                session_b.commit()
        finally:
            session_a.close()
            session_b.close()

        db_session.expire_all()
        final = db_session.get(User, user_id)
        assert final is not None
        assert final.version == start_version + 1
        assert final.model == "writer-a"
        assert final.llm_provider_settings["openai"]["model"] == "writer-a"
