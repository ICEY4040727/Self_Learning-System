"""Tests for archive CRUD endpoints (character, world, course)."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# Knowledge model was removed; tests that use it are skipped below


class TestCharacterCRUD:
    def test_create_character(self, client, auth_headers):
        resp = client.post("/api/character", json={
            "name": "Socrates",
            "type": "sage",
            "personality": "Wise philosopher",
            "speech_style": "温和追问",
            "greeting": "让我们从最简单的问题开始。",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Socrates"
        assert resp.json()["type"] == "sage"
        assert resp.json()["greeting"] == "让我们从最简单的问题开始。"

    def test_list_characters(self, client, auth_headers):
        client.post("/api/character", json={"name": "Teacher1"}, headers=auth_headers)
        client.post("/api/character", json={"name": "Teacher2"}, headers=auth_headers)
        resp = client.get("/api/character", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_delete_character(self, client, auth_headers):
        create = client.post("/api/character", json={"name": "ToDelete"}, headers=auth_headers)
        char_id = create.json()["id"]
        resp = client.delete(f"/api/character/{char_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_update_character(self, client, auth_headers):
        create = client.post("/api/character", json={
            "name": "Original",
            "greeting": "你好，欢迎来到这里。",
            "template_name": "socratic",
        }, headers=auth_headers)
        char_id = create.json()["id"]
        resp = client.put(f"/api/character/{char_id}", json={
            "name": "Updated",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        assert resp.json()["greeting"] == "你好，欢迎来到这里。"
        assert resp.json()["template_name"] == "socratic"

    def test_list_characters_filters_by_current_user(self, client, auth_headers):
        own = client.post("/api/character", json={"name": "OwnerChar"}, headers=auth_headers)
        assert own.status_code == 200

        client.post("/api/auth/register", json={
            "username": "other_user",
            "password": "testpass123",
        })
        login = client.post("/api/auth/login", data={
            "username": "other_user",
            "password": "testpass123",
        })
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        other = client.post("/api/character", json={"name": "OtherChar"}, headers=other_headers)
        assert other.status_code == 200

        listed = client.get("/api/character", headers=auth_headers)
        assert listed.status_code == 200
        names = {item["name"] for item in listed.json()}
        assert "OwnerChar" in names
        assert "OtherChar" not in names


class TestCourseCRUD:
    def _create_world(self, client, auth_headers):
        resp = client.post(
            "/api/worlds",
            json={"name": "Athens Academy", "description": "Philosophy world"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_create_course(self, client, auth_headers):
        world_id = self._create_world(client, auth_headers)
        resp = client.post("/api/courses", json={
            "world_id": world_id,
            "name": "Mathematics",
            "target_level": "intermediate",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Mathematics"
        assert resp.json()["world_id"] == world_id

    def test_list_courses(self, client, auth_headers):
        world_id = self._create_world(client, auth_headers)
        client.post("/api/courses", json={"world_id": world_id, "name": "Math"}, headers=auth_headers)
        client.post("/api/courses", json={"world_id": world_id, "name": "Physics"}, headers=auth_headers)
        resp = client.get(f"/api/courses?world_id={world_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_world_scoped_course_endpoints(self, client, auth_headers):
        world_id = self._create_world(client, auth_headers)
        create = client.post(
            f"/api/worlds/{world_id}/courses",
            json={"name": "World Scoped Course", "description": "desc", "target_level": "intro"},
            headers=auth_headers,
        )
        assert create.status_code == 200
        course_id = create.json()["id"]
        assert create.json()["world_id"] == world_id

        listed = client.get(f"/api/worlds/{world_id}/courses", headers=auth_headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["id"] == course_id


class TestWorldCRUD:
    def test_create_world_accepts_top_level_background_picture(self, client, auth_headers):
        resp = client.post(
            "/api/worlds",
            json={
                "name": "Shell World",
                "description": "A stable learning world shell.",
                "background_picture": "/themes/academy.jpg",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["background_picture"] == "/themes/academy.jpg"
        assert "scenes" not in payload

    def test_create_world_rejects_legacy_scenes_field(self, client, auth_headers):
        resp = client.post(
            "/api/worlds",
            json={
                "name": "Legacy Shell World",
                "description": "legacy payload",
                "scenes": {"background": "/themes/legacy.jpg"},
            },
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_update_world_preserves_background_picture_contract(self, client, auth_headers):
        create = client.post(
            "/api/worlds",
            json={
                "name": "Shell World",
                "description": "before",
                "background_picture": "/themes/academy.jpg",
            },
            headers=auth_headers,
        )
        assert create.status_code == 200
        world_id = create.json()["id"]

        update = client.put(
            f"/api/worlds/{world_id}",
            json={
                "name": "Shell World Updated",
                "description": "after",
                "background_picture": "/themes/library.jpg",
            },
            headers=auth_headers,
        )

        assert update.status_code == 200
        payload = update.json()
        assert payload["name"] == "Shell World Updated"
        assert payload["background_picture"] == "/themes/library.jpg"
        assert "scenes" not in payload

    def test_partial_update_world_keeps_existing_background_picture(self, client, auth_headers):
        create = client.post(
            "/api/worlds",
            json={
                "name": "Shell World",
                "description": "before",
                "background_picture": "/themes/academy.jpg",
            },
            headers=auth_headers,
        )
        assert create.status_code == 200
        world_id = create.json()["id"]

        update = client.put(
            f"/api/worlds/{world_id}",
            json={
                "name": "Shell World Renamed",
                "description": "after",
            },
            headers=auth_headers,
        )

        assert update.status_code == 200
        payload = update.json()
        assert payload["name"] == "Shell World Renamed"
        assert payload["description"] == "after"
        assert payload["background_picture"] == "/themes/academy.jpg"


class TestWorldCharacterCRUD:
    def _create_world(self, client, auth_headers):
        resp = client.post(
            "/api/worlds",
            json={"name": "World for Bindings", "description": "world"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def _create_character(self, client, auth_headers, name="Socrates", role_type="sage"):
        resp = client.post(
            "/api/character",
            json={"name": name, "type": role_type},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_bind_list_and_unbind_world_character(self, client, auth_headers):
        world_id = self._create_world(client, auth_headers)
        character_id = self._create_character(client, auth_headers)

        bind_resp = client.post(
            f"/api/worlds/{world_id}/characters",
            json={
                "character_id": character_id,
                "role": "sage",
                "is_primary": True,
                "world_title": "学院导师",
                "world_background": "在这个世界里，他负责引导新生。",
                "relationship_seed": "第一次在图书馆相遇。",
                "world_greeting": "欢迎来到学院，我们从最基本的概念开始。",
            },
            headers=auth_headers,
        )
        assert bind_resp.status_code == 200
        assert bind_resp.json()["world_id"] == world_id
        assert bind_resp.json()["character_id"] == character_id
        assert bind_resp.json()["role"] == "sage"
        assert bind_resp.json()["is_primary"] is True
        assert bind_resp.json()["character_name"] == "Socrates"
        assert bind_resp.json()["world_title"] == "学院导师"
        assert bind_resp.json()["world_background"] == "在这个世界里，他负责引导新生。"
        assert bind_resp.json()["relationship_seed"] == "第一次在图书馆相遇。"
        assert bind_resp.json()["world_greeting"] == "欢迎来到学院，我们从最基本的概念开始。"

        list_resp = client.get(f"/api/worlds/{world_id}/characters", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
        assert list_resp.json()[0]["character_id"] == character_id
        assert list_resp.json()[0]["role"] == "sage"
        assert list_resp.json()[0]["world_background"] == "在这个世界里，他负责引导新生。"

        delete_resp = client.delete(
            f"/api/worlds/{world_id}/characters/{character_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 204

        list_after_delete = client.get(f"/api/worlds/{world_id}/characters", headers=auth_headers)
        assert list_after_delete.status_code == 200
        assert list_after_delete.json() == []

    def test_bind_world_character_rejects_duplicate(self, client, auth_headers):
        world_id = self._create_world(client, auth_headers)
        character_id = self._create_character(client, auth_headers)

        first = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage", "is_primary": False},
            headers=auth_headers,
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage", "is_primary": False},
            headers=auth_headers,
        )
        assert second.status_code == 409

    def test_update_world_character_context(self, client, auth_headers):
        world_id = self._create_world(client, auth_headers)
        character_id = self._create_character(client, auth_headers)

        bind_resp = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage"},
            headers=auth_headers,
        )
        assert bind_resp.status_code == 200

        update_resp = client.patch(
            f"/api/worlds/{world_id}/characters/{character_id}",
            json={
                "world_title": "山中书院导师",
                "world_background": "在这座山中的世界里，他是负责守护知识的导师。",
                "relationship_seed": "曾在山门前引路相识。",
                "world_greeting": "进来吧，今天我们先看整体。",
            },
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["world_title"] == "山中书院导师"
        assert update_resp.json()["world_background"] == "在这座山中的世界里，他是负责守护知识的导师。"
        assert update_resp.json()["relationship_seed"] == "曾在山门前引路相识。"
        assert update_resp.json()["world_greeting"] == "进来吧，今天我们先看整体。"

    def test_generate_world_character_context(self, client, auth_headers, db_session, monkeypatch):
        from backend.models.models import User

        world_resp = client.post(
            "/api/worlds",
            json={
                "name": "雾港学院",
                "description": "一座适合学习逻辑与表达的学院。",
            },
            headers=auth_headers,
        )
        assert world_resp.status_code == 200
        world_id = world_resp.json()["id"]

        character_resp = client.post(
            "/api/character",
            json={
                "name": "林问之",
                "type": "sage",
                "title": "循证式学习引导者",
                "personality": "温和，喜欢通过追问帮助学生澄清问题。",
            },
            headers=auth_headers,
        )
        assert character_resp.status_code == 200
        character_id = character_resp.json()["id"]

        user = db_session.query(User).filter_by(username="testuser").one()
        user.default_provider = "local"
        db_session.commit()

        captured = {}

        class FakeAdapter:
            async def chat(self, **kwargs):
                captured.update(kwargs)
                return """{
                    "world_title": "雾港学院导师",
                    "world_background": "在雾港学院里，林问之负责带领新生拆解复杂问题，将模糊困惑整理成可验证的学习路径。",
                    "relationship_seed": "学习者第一次来到雾港学院时，在图书馆入口遇见了正在整理问题卡片的林问之。",
                    "world_greeting": "欢迎来到雾港学院。先告诉我，你现在最想弄清楚的问题是什么？"
                }"""

        import backend.services.llm.adapter as adapter_module

        monkeypatch.setattr(adapter_module, "get_llm_adapter", lambda *args, **kwargs: FakeAdapter())

        resp = client.post(
            f"/api/worlds/{world_id}/characters/{character_id}/generate-context",
            json={"role": "sage"},
            headers=auth_headers,
        )

        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["world_title"] == "雾港学院导师"
        assert "雾港学院" in payload["world_background"]
        assert "图书馆入口" in payload["relationship_seed"]
        assert payload["world_greeting"].startswith("欢迎来到雾港学院")
        assert "雾港学院" in captured["messages"][0]["content"]
        assert "一座适合学习逻辑与表达的学院。" in captured["messages"][0]["content"]
        assert "林问之" in captured["messages"][0]["content"]


@pytest.mark.skip(reason="Knowledge model removed - knowledge graph not in current schema")
class TestWorldKnowledgeInitialization:
    def _create_character(self, client, auth_headers, name: str):
        resp = client.post(
            "/api/character",
            json={"name": name, "type": "sage"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def _create_world(self, client, auth_headers, name: str):
        world = client.post(
            "/api/worlds",
            json={"name": name, "description": "test"},
            headers=auth_headers,
        )
        assert world.status_code == 200
        return world.json()["id"]

    def test_create_world_initializes_knowledge_row(self, client, auth_headers, db_session):
        world_id = self._create_world(client, auth_headers, "Knowledge World")

        knowledge = db_session.query(Knowledge).filter(Knowledge.world_id == world_id).first()
        assert knowledge is not None
        assert knowledge.graph == {}

    def test_world_character_bind_backfills_missing_knowledge(self, client, auth_headers, db_session):
        character_id = self._create_character(client, auth_headers, "KnowledgeBackfill")
        world_id = self._create_world(client, auth_headers, "Backfill World")

        db_session.query(Knowledge).filter(Knowledge.world_id == world_id).delete()
        db_session.commit()
        assert db_session.query(Knowledge).filter(Knowledge.world_id == world_id).count() == 0

        bind = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage", "is_primary": True},
            headers=auth_headers,
        )
        assert bind.status_code == 200
        knowledge_rows = db_session.query(Knowledge).filter(Knowledge.world_id == world_id).all()
        assert len(knowledge_rows) == 1
        assert knowledge_rows[0].graph == {}

    def test_world_character_bind_backfill_is_idempotent(self, client, auth_headers, db_session):
        world_id = self._create_world(client, auth_headers, "Idempotent World")
        first_character_id = self._create_character(client, auth_headers, "KnowledgeIdempotentA")
        second_character_id = self._create_character(client, auth_headers, "KnowledgeIdempotentB")

        first_bind = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": first_character_id, "role": "sage", "is_primary": True},
            headers=auth_headers,
        )
        assert first_bind.status_code == 200

        second_bind = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": second_character_id, "role": "traveler", "is_primary": False},
            headers=auth_headers,
        )
        assert second_bind.status_code == 200

        assert db_session.query(Knowledge).filter(Knowledge.world_id == world_id).count() == 1

    def test_knowledge_unique_conflict_does_not_fail_world_character_bind(
        self,
        client,
        auth_headers,
        db_session,
        monkeypatch,
    ):
        character_id = self._create_character(client, auth_headers, "KnowledgeConcurrent")
        world_id = self._create_world(client, auth_headers, "Concurrent World")

        db_session.query(Knowledge).filter(Knowledge.world_id == world_id).delete()
        db_session.commit()
        assert db_session.query(Knowledge).filter(Knowledge.world_id == world_id).count() == 0

        original_flush = db_session.flush
        conflict_state = {"raised": False}

        def flush_with_conflict(*args, **kwargs):
            pending_knowledge = any(
                isinstance(obj, Knowledge) and obj.world_id == world_id
                for obj in db_session.new
            )
            if pending_knowledge and not conflict_state["raised"]:
                other_session = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=db_session.bind,
                )()
                try:
                    other_session.add(Knowledge(world_id=world_id, graph={}))
                    other_session.commit()
                finally:
                    other_session.close()
                conflict_state["raised"] = True
                raise IntegrityError("INSERT INTO knowledge", {}, Exception("duplicate key"))
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(db_session, "flush", flush_with_conflict)

        bind = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage", "is_primary": True},
            headers=auth_headers,
        )
        assert bind.status_code == 200
        assert conflict_state["raised"] is True
        assert db_session.query(Knowledge).filter(Knowledge.world_id == world_id).count() == 1
