"""Core User LLM read/write contract regression tests."""
from __future__ import annotations

from backend.models.models import User
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    serialize_provider_settings,
    update_provider_settings,
)

from .conftest import create_user


def _put_settings(client, auth_headers, payload: dict):
    version_resp = client.get("/api/settings", headers=auth_headers)
    assert version_resp.status_code == 200, version_resp.text
    payload = {**payload, "version": version_resp.json()["version"]}
    return client.put("/api/settings", json=payload, headers=auth_headers)


class TestWriteGatewayContract:
    def test_gateway_dual_write_keeps_json_and_legacy_equal(self, db_session):
        user = create_user(db_session, username="contract-dual-write")
        update_provider_settings(
            user,
            "openai",
            api_key="secret-key",
            model="gpt-4.1-mini",
            base_url="https://api.openai.example/v1",
        )
        db_session.commit()

        entry = user.llm_provider_settings["openai"]
        assert user.default_provider == "openai"
        assert user.model == entry["model"] == "gpt-4.1-mini"
        assert user.llm_base_url == entry["base_url"] == "https://api.openai.example/v1"
        assert user.encrypted_api_key == entry["encrypted_api_key"]
        assert audit_user_llm_consistency(db_session) == []

    def test_switching_active_provider_syncs_legacy_mirror(self, db_session):
        user = create_user(db_session, username="contract-switch")
        update_provider_settings(
            user,
            "custom",
            api_key="custom-key",
            model="custom-model",
            base_url="https://ai.custom.test",
        )
        update_provider_settings(
            user,
            "openai",
            api_key="openai-key",
            model="gpt-4.1-mini",
            base_url="https://api.openai.example/v1",
        )
        db_session.commit()

        assert user.default_provider == "openai"
        assert user.model == "gpt-4.1-mini"
        assert user.llm_provider_settings["custom"]["model"] == "custom-model"
        assert user.llm_provider_settings["openai"]["model"] == "gpt-4.1-mini"
        assert audit_user_llm_consistency(db_session) == []

    def test_clear_api_key_and_model_empties_json_and_legacy(self, db_session):
        user = create_user(db_session, username="contract-clear")
        update_provider_settings(
            user,
            "openai",
            api_key="secret-key",
            model="gpt-4.1-mini",
            base_url="https://api.openai.example/v1",
        )
        update_provider_settings(user, "openai", clear_api_key=True, model="")
        db_session.commit()

        entry = user.llm_provider_settings.get("openai", {})
        assert user.encrypted_api_key is None
        assert user.model is None
        assert "encrypted_api_key" not in entry
        assert "model" not in entry

    def test_multi_provider_entries_do_not_cross_contaminate(self, db_session):
        user = create_user(db_session, username="contract-multi")
        update_provider_settings(user, "openai", model="gpt-4.1-mini")
        update_provider_settings(user, "local", model="llama3.1", base_url="http://127.0.0.1:11434")
        db_session.commit()

        assert user.llm_provider_settings["openai"]["model"] == "gpt-4.1-mini"
        assert user.llm_provider_settings["local"]["model"] == "llama3.1"
        assert user.llm_provider_settings["local"]["base_url"] == "http://127.0.0.1:11434"


class TestReadApiContract:
    def test_get_settings_matches_json_active_provider(self, client, auth_headers, db_session):
        user = db_session.query(User).filter_by(username="testuser").one()
        update_provider_settings(
            user,
            "openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.example/v1",
        )
        db_session.commit()

        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        payload = resp.json()

        assert payload["default_provider"] == "openai"
        assert payload["model"] == "gpt-4.1-mini"
        assert payload["provider_settings"]["openai"]["model"] == "gpt-4.1-mini"

        effective = get_effective_llm_config(user, auto_persist_legacy_backfill=False)
        assert effective.model == payload["model"]
        assert effective.base_url == payload["base_url"]
        assert serialize_provider_settings(user) == payload["provider_settings"]

    def test_put_then_get_round_trip_stays_consistent(self, client, auth_headers, db_session):
        resp = _put_settings(
            client,
            auth_headers,
            {
                "default_provider": "openai",
                "model": "gpt-4.1-mini",
                "base_url": "https://api.openai.example/v1",
                "temperature": 0.4,
                "max_tokens": 1536,
            },
        )
        assert resp.status_code == 200, resp.text

        user = db_session.query(User).filter_by(username="testuser").one()
        get_resp = client.get("/api/settings", headers=auth_headers)
        payload = get_resp.json()

        assert payload["model"] == user.model == "gpt-4.1-mini"
        assert payload["temperature"] == user.temperature == 0.4
        assert audit_user_llm_consistency(db_session) == []
