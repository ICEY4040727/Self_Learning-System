"""Risk 4 — read-path legacy backfill and automatic JSON persistence."""
from __future__ import annotations

from backend.models.models import User
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    persist_legacy_backfill,
    serialize_provider_settings,
)

from .conftest import create_user


class TestReadPathLegacyBackfill:
    def test_runtime_read_uses_legacy_when_json_missing(self, db_session):
        user = create_user(db_session, username="risk4-read")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {}
        db_session.commit()

        config = get_effective_llm_config(user, auto_persist_legacy_backfill=False)
        assert config.model == "legacy-model"

    def test_auto_persist_disabled_leaves_json_empty(self, db_session):
        user = create_user(db_session, username="risk4-no-persist")
        user.default_provider = "openai"
        user.model = "legacy-only"
        user.llm_provider_settings = {}
        db_session.commit()

        get_effective_llm_config(user, auto_persist_legacy_backfill=False)
        db_session.refresh(user)
        assert user.llm_provider_settings == {}

    def test_auto_persist_enabled_writes_json_without_put(self, db_session):
        user = create_user(db_session, username="risk4-auto-persist")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_base_url = "https://api.openai.example/v1"
        user.llm_provider_settings = {}
        db_session.commit()

        get_effective_llm_config(user, auto_persist_legacy_backfill=True)

        db_session.expire_all()
        refreshed = db_session.query(User).filter_by(id=user.id).one()
        assert refreshed.llm_provider_settings == {
            "openai": {
                "model": "legacy-model",
                "base_url": "https://api.openai.example/v1",
            }
        }
        assert audit_user_llm_consistency(db_session) == []

    def test_json_value_wins_over_conflicting_legacy(self, db_session):
        user = create_user(db_session, username="risk4-json-priority")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {"openai": {"model": "json-model"}}
        db_session.commit()

        config = get_effective_llm_config(user, auto_persist_legacy_backfill=True)
        assert config.model == "json-model"

        db_session.refresh(user)
        assert user.llm_provider_settings["openai"]["model"] == "json-model"
        assert persist_legacy_backfill(user.id, "openai") is False

    def test_non_active_provider_does_not_use_top_level_legacy(self, db_session):
        user = create_user(db_session, username="risk4-inactive")
        user.default_provider = "openai"
        user.model = "legacy-openai-only"
        user.llm_provider_settings = {"claude": {}}
        db_session.commit()

        config = get_effective_llm_config(
            user,
            provider="claude",
            auto_persist_legacy_backfill=False,
        )
        assert config.provider == "claude"
        assert config.model is None

        serialized = serialize_provider_settings(user)
        assert serialized.get("claude", {}).get("model") is None

    def test_persist_legacy_backfill_is_idempotent(self, db_session):
        user = create_user(db_session, username="risk4-idempotent")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {}
        db_session.commit()

        assert persist_legacy_backfill(user.id, "openai") is True
        assert persist_legacy_backfill(user.id, "openai") is False
