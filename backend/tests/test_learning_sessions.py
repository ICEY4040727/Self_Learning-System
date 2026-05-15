"""Tests for course sessions and relationship JSON behavior."""

import pytest

from backend.models.models import Session


def _create_world(client, auth_headers):
    resp = client.post(
        "/api/worlds",
        json={"name": "Session World", "description": "world"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_course(client, auth_headers, world_id):
    resp = client.post(
        "/api/courses",
        json={"world_id": world_id, "name": "Session Course"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


class TestCourseSessionRelationship:
    def test_session_uses_relationship_json(self, client, auth_headers, db_session):
        world_id = _create_world(client, auth_headers)
        course_id = _create_course(client, auth_headers, world_id)

        start = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        db_session_obj = db_session.query(Session).filter(Session.id == session_id).first()
        assert db_session_obj is not None
        assert isinstance(db_session_obj.relationship, dict)
        assert db_session_obj.relationship.get("stage") == "stranger"

        db_session_obj.relationship = {
            "dimensions": {
                "trust": 0.8,
                "familiarity": 0.8,
                "respect": 0.8,
                "comfort": 0.8,
            },
            "stage": "mentor",
            "history": [],
        }
        db_session.commit()

        listed = client.get("/api/sessions", headers=auth_headers)
        assert listed.status_code == 200
        assert listed.json()[0]["relationship_stage"] == "mentor"

    def test_start_learning_returns_bound_sage_persona(self, client, auth_headers):
        world_resp = client.post(
            "/api/worlds",
            json={
                "name": "Session World with Scene",
                "description": "world",
                "scenes": {"default": "/scenes/academy.png"},
            },
            headers=auth_headers,
        )
        assert world_resp.status_code == 200
        world_id = world_resp.json()["id"]
        course_id = _create_course(client, auth_headers, world_id)

        character_resp = client.post(
            "/api/character",
            json={
                "name": "Socrates",
                "type": "sage",
                "sprites": {"default": "/sprites/socrates-default.png"},
                "system_prompt_template": "You are Socrates.",
            },
            headers=auth_headers,
        )
        assert character_resp.status_code == 200
        character_id = character_resp.json()["id"]

        bind_resp = client.post(
            f"/api/worlds/{world_id}/characters",
            json={
                "character_id": character_id,
                "role": "sage",
                "is_primary": True,
                "world_title": "学院导师",
                "world_background": "这是一个专注于逻辑与提问的世界。",
                "relationship_seed": "第一次在图书馆门口遇见。",
                "world_greeting": "欢迎来到学院，今天我们先看整体结构。",
            },
            headers=auth_headers,
        )
        assert bind_resp.status_code == 200

        traveler_resp = client.post(
            "/api/character",
            json={
                "name": "Traveler",
                "type": "traveler",
                "sprites": {"default": "/sprites/traveler-default.png"},
            },
            headers=auth_headers,
        )
        assert traveler_resp.status_code == 200
        traveler_id = traveler_resp.json()["id"]

        bind_traveler_resp = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": traveler_id, "role": "traveler", "is_primary": True},
            headers=auth_headers,
        )
        assert bind_traveler_resp.status_code == 200

        start_resp = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start_resp.status_code == 200
        payload = start_resp.json()
        assert payload["teacher_persona"] == "Socrates"  # DD1: TeacherPersona merged into Character
        assert payload["greeting"] == "欢迎来到学院，今天我们先看整体结构。"
        assert payload["relationship_stage"] == "stranger"
        assert payload["relationship"]["dimensions"]["trust"] == 0.0
        assert payload["scenes"] == {"default": "/scenes/academy.png"}
        assert payload["sage_sprites"] == {"default": "/sprites/socrates-default.png"}
        assert payload["traveler_sprites"] == {"default": "/sprites/traveler-default.png"}

    def test_start_learning_returns_top_level_background_picture(self, client, auth_headers):
        world_resp = client.post(
            "/api/worlds",
            json={
                "name": "Session World with Background",
                "description": "world",
                "background_picture": "/themes/academy.jpg",
            },
            headers=auth_headers,
        )
        assert world_resp.status_code == 200
        world_id = world_resp.json()["id"]
        course_id = _create_course(client, auth_headers, world_id)

        start_resp = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start_resp.status_code == 200
        payload = start_resp.json()
        assert payload["background_picture"] == "/themes/academy.jpg"

    @pytest.mark.skip(reason="knowledge-graph endpoint not yet implemented")
    def test_chat_updates_world_knowledge_graph(self, client, auth_headers):
        world_id = _create_world(client, auth_headers)
        course_id = _create_course(client, auth_headers, world_id)

        start_resp = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start_resp.status_code == 200

        chat_resp = client.post(
            f"/api/courses/{course_id}/chat",
            json={"message": "今天我想学习递归和终止条件"},
            headers=auth_headers,
        )
        assert chat_resp.status_code == 200

        graph_resp = client.get(f"/api/worlds/{world_id}/knowledge-graph", headers=auth_headers)
        assert graph_resp.status_code == 200
        payload = graph_resp.json()
        assert "nodes" in payload
        assert "edges" in payload
        assert isinstance(payload["nodes"], list)
        assert len(payload["nodes"]) >= 1
