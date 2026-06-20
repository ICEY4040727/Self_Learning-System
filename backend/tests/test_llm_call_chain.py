"""Regression tests for the user-configured LLM call chain."""

from backend.models.models import Character, User


def _settings_version(client, auth_headers) -> int:
    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["version"]


def _put_settings(client, auth_headers, payload: dict):
    if "version" not in payload:
        payload = {**payload, "version": _settings_version(client, auth_headers)}
    return client.put("/api/settings", json=payload, headers=auth_headers)


def _create_course_with_sage(client, auth_headers):
    world = client.post(
        "/api/worlds",
        json={"name": "LLM World", "description": "world"},
        headers=auth_headers,
    )
    assert world.status_code == 200, world.text
    world_id = world.json()["id"]

    course = client.post(
        "/api/courses",
        json={"world_id": world_id, "name": "LLM Course"},
        headers=auth_headers,
    )
    assert course.status_code == 200, course.text
    course_id = course.json()["id"]

    character = client.post(
        "/api/character",
        json={"name": "Sage", "type": "sage"},
        headers=auth_headers,
    )
    assert character.status_code == 200, character.text
    sage_id = character.json()["id"]

    bind = client.post(
        f"/api/worlds/{world_id}/characters",
        json={"character_id": sage_id, "role": "sage", "is_primary": True},
        headers=auth_headers,
    )
    assert bind.status_code == 200, bind.text
    return course_id, sage_id


def _start_session(client, auth_headers, course_id, sage_id):
    start = client.post(
        f"/api/courses/{course_id}/start",
        json={"sage_id": sage_id},
        headers=auth_headers,
    )
    assert start.status_code == 200, start.text
    return start.json()["session_id"]


def test_chat_without_required_api_key_returns_business_error(client, auth_headers):
    course_id, sage_id = _create_course_with_sage(client, auth_headers)
    _start_session(client, auth_headers, course_id, sage_id)

    resp = client.post(
        f"/api/courses/{course_id}/chat",
        json={"message": "hello"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["type"] == "error"
    assert "API Key" in payload["reply"]


def test_chat_local_provider_passes_user_llm_params(
    client, auth_headers, db_session, monkeypatch,
):
    course_id, sage_id = _create_course_with_sage(client, auth_headers)
    _start_session(client, auth_headers, course_id, sage_id)

    user = db_session.query(User).filter_by(username="testuser").one()
    user.default_provider = "local"
    user.temperature = 0.3
    user.max_tokens = 1234
    user.model = "llama3.1"
    db_session.commit()

    captured = {}

    async def fake_process_message(**kwargs):
        captured.update(kwargs)
        return {
            "type": "text",
            "reply": "ok",
            "emotion": {"emotion_type": "neutral"},
            "relationship_stage": "stranger",
            "relationship": {},
            "relationship_events": [],
            "memory_extracted_count": 0,
            "narrative_events": [],
            "new_achievements": [],
        }

    import backend.api.routes.learning as learning_route

    monkeypatch.setattr(
        learning_route.learning_engine,
        "process_message",
        fake_process_message,
    )

    resp = client.post(
        f"/api/courses/{course_id}/chat",
        json={"message": "hello"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["reply"] == "ok"
    assert captured["provider"] == "local"
    assert captured["user_api_key"] is None
    assert captured["temperature"] == 0.3
    assert captured["max_tokens"] == 1234
    assert captured["model"] == "llama3.1"
    assert captured["base_url"] is None


def test_chat_uses_sage_character_llm_settings_over_user_defaults(
    client, auth_headers, db_session, monkeypatch,
):
    course_id, sage_id = _create_course_with_sage(client, auth_headers)
    _start_session(client, auth_headers, course_id, sage_id)

    user = db_session.query(User).filter_by(username="testuser").one()
    user.default_provider = "local"
    user.temperature = 0.3
    user.max_tokens = 1234
    user.model = "llama3.1"
    user.llm_base_url = "http://localhost:11434"
    from backend.core.security import encrypt_api_key
    user.llm_provider_settings = {
        "openai": {"encrypted_api_key": encrypt_api_key("openai-key")},
    }
    db_session.commit()

    sage = db_session.query(Character).filter_by(id=sage_id).one()
    sage.llm_settings = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "base_url": "https://api.openai.example/v1",
        "temperature": 0.9,
        "max_tokens": 256,
    }
    db_session.commit()

    captured = {}

    async def fake_process_message(**kwargs):
        captured.update(kwargs)
        return {
            "type": "text",
            "reply": "ok",
            "emotion": {"emotion_type": "neutral"},
            "relationship_stage": "stranger",
            "relationship": {},
            "relationship_events": [],
            "memory_extracted_count": 0,
            "narrative_events": [],
            "new_achievements": [],
        }

    import backend.api.routes.learning as learning_route

    monkeypatch.setattr(
        learning_route.learning_engine,
        "process_message",
        fake_process_message,
    )

    resp = client.post(
        f"/api/courses/{course_id}/chat",
        json={"message": "hello"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    assert captured["provider"] == "openai"
    assert captured["user_api_key"] == "openai-key"
    assert captured["temperature"] == 0.9
    assert captured["max_tokens"] == 256
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["base_url"] == "https://api.openai.example/v1"


def test_settings_round_trip_persists_llm_params(client, auth_headers, db_session):
    resp = _put_settings(
        client,
        auth_headers,
        {
            "default_provider": "local",
            "api_key": "secret-key",
            "temperature": 0.4,
            "max_tokens": 1536,
            "model": "llama3.1",
            "base_url": "https://ai.example.test",
        },
    )
    assert resp.status_code == 200, resp.text
    baseline = client.get("/api/settings", headers=auth_headers).json()["version"] - 1
    assert resp.json()["version"] == baseline + 1

    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["version"] == baseline + 1
    assert payload["default_provider"] == "local"
    assert payload["api_key_configured"] is True
    assert payload["temperature"] == 0.4
    assert payload["max_tokens"] == 1536
    assert payload["model"] == "llama3.1"
    assert payload["base_url"] == "https://ai.example.test"
    assert payload["provider_settings"]["local"] == {
        "api_key_configured": True,
        "model": "llama3.1",
        "base_url": "https://ai.example.test",
    }

    user = db_session.query(User).filter_by(username="testuser").one()
    assert user.default_provider == "local"
    assert user.temperature == 0.4
    assert user.max_tokens == 1536
    assert user.model == "llama3.1"
    assert user.llm_base_url == "https://ai.example.test"
    assert user.encrypted_api_key
    assert user.encrypted_api_key != "secret-key"


def test_settings_preserves_each_provider_independently(client, auth_headers, db_session):
    resp = _put_settings(
        client,
        auth_headers,
        {
            "default_provider": "custom",
            "api_key": "custom-key",
            "model": "gpt-4o-mini",
            "base_url": "https://ai.custom.test",
        },
    )
    assert resp.status_code == 200, resp.text

    resp = _put_settings(
        client,
        auth_headers,
        {
            "default_provider": "openai",
            "api_key": "openai-key",
            "model": "gpt-4.1-mini",
            "base_url": "https://api.openai.example/v1",
        },
    )
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["default_provider"] == "openai"
    assert payload["provider_settings"]["custom"] == {
        "api_key_configured": True,
        "model": "gpt-4o-mini",
        "base_url": "https://ai.custom.test/v1",
    }
    assert payload["provider_settings"]["openai"] == {
        "api_key_configured": True,
        "model": "gpt-4.1-mini",
        "base_url": "https://api.openai.example/v1",
    }


def test_chat_uses_active_provider_specific_settings(client, auth_headers, monkeypatch):
    course_id, sage_id = _create_course_with_sage(client, auth_headers)
    _start_session(client, auth_headers, course_id, sage_id)

    for provider, api_key, model, base_url in (
        ("custom", "custom-key", "gpt-4o-mini", "https://ai.custom.test"),
        ("openai", "openai-key", "gpt-4.1-mini", "https://api.openai.example/v1"),
    ):
        resp = _put_settings(
            client,
            auth_headers,
            {
                "default_provider": provider,
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
            },
        )
        assert resp.status_code == 200, resp.text

    captured = {}

    async def fake_process_message(**kwargs):
        captured.update(kwargs)
        return {
            "type": "text",
            "reply": "ok",
            "emotion": {"emotion_type": "neutral"},
            "relationship_stage": "stranger",
            "relationship": {},
            "relationship_events": [],
            "memory_extracted_count": 0,
            "narrative_events": [],
            "new_achievements": [],
        }

    import backend.api.routes.learning as learning_route

    monkeypatch.setattr(
        learning_route.learning_engine,
        "process_message",
        fake_process_message,
    )

    resp = client.post(
        f"/api/courses/{course_id}/chat",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert captured["provider"] == "openai"
    assert captured["user_api_key"] == "openai-key"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["base_url"] == "https://api.openai.example/v1"


def test_settings_response_shows_key_state_and_clear_key(client, auth_headers, db_session):
    resp = _put_settings(client, auth_headers, {"api_key": "secret-key"})
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["api_key_configured"] is True

    resp = _put_settings(client, auth_headers, {"clear_api_key": True})
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["api_key_configured"] is False

    user = db_session.query(User).filter_by(username="testuser").one()
    assert user.encrypted_api_key is None


def test_settings_test_connection_normalizes_custom_base_url(client, auth_headers, monkeypatch):
    class FakeAdapter:
        provider = "openai-compatible"
        model = "gpt-4o-mini"

        async def chat(self, **kwargs):
            return "ok"

    class FakeManager:
        def get_adapter(self, **kwargs):
            self.kwargs = kwargs
            return FakeAdapter()

    import backend.services.llm.manager as llm_manager

    fake_manager = FakeManager()
    monkeypatch.setattr(llm_manager, "_llm_manager", fake_manager)

    resp = client.post(
        "/api/settings/test-connection",
        json={
            "default_provider": "custom",
            "api_key": "secret-key",
            "model": "gpt-4o-mini",
            "base_url": "https://ai.shukelongda.cn/v1/chat/completions",
            "temperature": 0.2,
            "max_tokens": 64,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["base_url"] == "https://ai.shukelongda.cn/v1"
    assert fake_manager.kwargs["base_url"] == "https://ai.shukelongda.cn/v1"


def test_settings_model_listing_uses_gateway_models(client, auth_headers, monkeypatch):
    class FakeAdapter:
        async def list_models(self, user_api_key=None):
            return ["model-a", "model-b"]

    class FakeManager:
        def get_adapter(self, **kwargs):
            self.kwargs = kwargs
            return FakeAdapter()

    import backend.services.llm.manager as llm_manager

    fake_manager = FakeManager()
    monkeypatch.setattr(llm_manager, "_llm_manager", fake_manager)

    resp = client.post(
        "/api/settings/models",
        json={
            "default_provider": "custom",
            "api_key": "secret-key",
            "model": "gpt-4o-mini",
            "base_url": "https://ai.shukelongda.cn/v1/chat/completions",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["source"] == "remote"
    assert payload["models"] == ["model-a", "model-b"]
    assert payload["base_url"] == "https://ai.shukelongda.cn/v1"
    assert fake_manager.kwargs["base_url"] == "https://ai.shukelongda.cn/v1"


def test_generate_description_uses_string_llm_response(client, auth_headers, monkeypatch):
    class FakeAdapter:
        async def chat(self, **kwargs):
            return "  concise course description  "

    class FakeManager:
        def get_adapter(self, **kwargs):
            return FakeAdapter()

    import backend.services.llm.manager as llm_manager

    monkeypatch.setattr(llm_manager, "_llm_manager", FakeManager())

    resp = client.post(
        "/api/courses/generate-description",
        json={
            "domain": "Python",
            "course_name": "Python Basics",
            "current_level": "beginner",
            "target_level": "intermediate",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"description": "concise course description"}


def test_custom_provider_normalizes_base_url():
    from backend.services.llm.adapter import get_llm_adapter

    adapter = get_llm_adapter(
        provider="custom",
        api_key="test-key",
        base_url="https://ai.shukelongda.cn",
        model="gpt-4o-mini",
    )

    assert adapter.provider == "openai-compatible"
    assert adapter.model == "gpt-4o-mini"
    assert adapter._base_url == "https://ai.shukelongda.cn/v1"


def test_custom_provider_strips_full_chat_completions_endpoint():
    from backend.services.llm.adapter import get_llm_adapter

    adapter = get_llm_adapter(
        provider="custom",
        api_key="test-key",
        base_url="https://ai.shukelongda.cn/v1/chat/completions",
    )

    assert adapter.provider == "openai-compatible"
    assert adapter.model == "gpt-4o-mini"
    assert adapter._base_url == "https://ai.shukelongda.cn/v1"
