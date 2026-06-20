"""Tests for User LLM settings optimistic locking."""

from backend.models.models import User
from backend.services.user_llm_settings import (
    lock_user_for_update,
    update_generation_params,
    update_provider_settings,
)


def _put_settings(client, auth_headers, payload: dict):
    version_resp = client.get("/api/settings", headers=auth_headers)
    assert version_resp.status_code == 200, version_resp.text
    payload = {**payload, "version": version_resp.json()["version"]}
    return client.put("/api/settings", json=payload, headers=auth_headers)


def test_get_settings_includes_version(client, auth_headers, db_session):
    user = db_session.query(User).filter_by(username="testuser").one()
    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == user.version


def test_put_settings_increments_version(client, auth_headers):
    baseline = client.get("/api/settings", headers=auth_headers).json()["version"]
    resp = _put_settings(
        client,
        auth_headers,
        {"default_provider": "openai", "temperature": 0.5},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["version"] == baseline + 1

    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.json()["version"] == baseline + 1


def test_put_settings_rejects_stale_version(client, auth_headers):
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


def test_lock_user_for_update_serializes_gateway_writes(db_session):
    user = User(username="lock-user", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    start_version = user.version

    locked = lock_user_for_update(db_session, user.id)
    update_provider_settings(locked, "openai", model="gpt-4.1-mini")
    db_session.commit()
    db_session.refresh(locked)

    assert locked.version == start_version + 1

    locked_again = lock_user_for_update(db_session, user.id)
    update_generation_params(locked_again, temperature=0.8)
    db_session.commit()
    db_session.refresh(locked_again)

    assert locked_again.version == start_version + 2
