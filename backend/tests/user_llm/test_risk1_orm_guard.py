"""Risk 1 — ORM runtime guard blocks naked User LLM writes."""
from __future__ import annotations

import pytest
from sqlalchemy import update

from backend.models.models import User
from backend.services.user_llm_settings import update_provider_settings
from backend.services.user_llm_write_guard import UserLLMWriteForbidden

from .conftest import create_user


class TestOrmRuntimeGuard:
    def test_direct_legacy_field_assignment_is_blocked(self, guarded_session):
        user = create_user(guarded_session, username="guard-legacy")

        with pytest.raises(UserLLMWriteForbidden, match="User\\.default_provider"):
            user.default_provider = "openai"

    def test_direct_json_field_assignment_is_blocked(self, guarded_session):
        user = create_user(guarded_session, username="guard-json")

        with pytest.raises(UserLLMWriteForbidden, match="User\\.llm_provider_settings"):
            user.llm_provider_settings = {"openai": {"model": "gpt-4o"}}

    def test_commit_after_blocked_assign_never_reaches_db(self, guarded_session):
        user = create_user(guarded_session, username="guard-commit")
        user_id = user.id

        with pytest.raises(UserLLMWriteForbidden, match="User\\.model"):
            user.model = "orphan-model"
            guarded_session.commit()

        guarded_session.rollback()
        reloaded = guarded_session.get(User, user_id)
        assert reloaded is not None
        assert reloaded.model is None

    def test_write_gateway_dual_write_commits_cleanly(self, guarded_session):
        user = create_user(guarded_session, username="guard-gateway")

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
        assert user.llm_provider_settings["openai"]["model"] == "gpt-4.1-mini"

    def test_bulk_update_is_blocked(self, guarded_session):
        user = create_user(guarded_session, username="guard-bulk")

        with pytest.raises(UserLLMWriteForbidden, match="bulk UPDATE"):
            guarded_session.execute(
                update(User).where(User.id == user.id).values(model="gpt-4o")
            )
