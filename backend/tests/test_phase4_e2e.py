"""Phase 4 E2E/regression coverage for issue #127 acceptance matrix."""

from backend.models.models import RelationshipStageRecord
from backend.models.models import Session as SessionModel
from backend.services.knowledge import knowledge_service


def _create_world(client, auth_headers, name: str):
    resp = client.post(
        "/api/worlds",
        json={"name": name, "description": "phase4-e2e"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _create_character(client, auth_headers, name: str, role_type: str):
    resp = client.post(
        "/api/character",
        json={"name": name, "type": role_type},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _bind_character(client, auth_headers, world_id: int, character_id: int, role: str, is_primary: bool):
    resp = client.post(
        f"/api/worlds/{world_id}/characters",
        json={"character_id": character_id, "role": role, "is_primary": is_primary},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _create_course(client, auth_headers, world_id: int, name: str):
    resp = client.post(
        f"/api/worlds/{world_id}/courses",
        json={"name": name, "description": "phase4-course", "target_level": "beginner"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()


class TestPhase4AcceptanceFlow:
    def test_full_flow_checkpoint_branch_and_temporal_visibility(self, client, auth_headers, db_session):
        world = _create_world(client, auth_headers, "Phase4 World")
        world_id = world["id"]

        sage = _create_character(client, auth_headers, "Phase4 Sage", "sage")
        traveler = _create_character(client, auth_headers, "Phase4 Traveler", "traveler")
        _bind_character(client, auth_headers, world_id, sage["id"], "sage", True)
        _bind_character(client, auth_headers, world_id, traveler["id"], "traveler", True)

        persona = client.post(
            "/api/teacher_persona",
            json={
                "character_id": sage["id"],
                "name": "Phase4 Mentor",
                "system_prompt_template": "你是 Phase4 Mentor。",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert persona.status_code == 200

        course = _create_course(client, auth_headers, world_id, "Phase4 Course")
        course_id = course["id"]

        start = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start.status_code == 200
        source_session_id = start.json()["session_id"]

        chat = client.post(
            f"/api/courses/{course_id}/chat",
            json={"message": "我们来学习递归和终止条件"},
            headers=auth_headers,
        )
        assert chat.status_code == 200

        checkpoint = client.post(
            "/api/checkpoints",
            json={"world_id": world_id, "session_id": source_session_id, "save_name": "phase4-cp"},
            headers=auth_headers,
        )
        assert checkpoint.status_code == 200
        checkpoint_id = checkpoint.json()["id"]
        checkpoint_time = checkpoint.json()["created_at"]

        branch = client.post(
            f"/api/checkpoints/{checkpoint_id}/branch",
            json={"branch_name": "phase4-branch"},
            headers=auth_headers,
        )
        assert branch.status_code == 200
        branch_session_id = branch.json()["session_id"]
        assert branch.json()["course_id"] == course_id
        assert branch.json()["parent_checkpoint_id"] == checkpoint_id

        timelines = client.get(f"/api/worlds/{world_id}/timelines", headers=auth_headers)
        assert timelines.status_code == 200
        timeline_sessions = {item["id"] for item in timelines.json()["sessions"]}
        assert source_session_id in timeline_sessions
        assert branch_session_id in timeline_sessions

        # Add post-checkpoint mainline knowledge and branch-owned knowledge,
        # then validate temporal/session visibility through graph API.
        knowledge_service.update_after_chat(
            db_session,
            world_id,
            "主线后置概念",
            "分叉后主线新增",
            {"emotion_type": "neutral"},
            session_id=source_session_id,
        )
        knowledge_service.update_after_chat(
            db_session,
            world_id,
            "分叉专属概念",
            "分叉会话新增",
            {"emotion_type": "neutral"},
            session_id=branch_session_id,
        )
        db_session.commit()

        graph = client.get(
            f"/api/worlds/{world_id}/knowledge-graph",
            params={"checkpoint_time": checkpoint_time, "session_id": branch_session_id},
            headers=auth_headers,
        )
        assert graph.status_code == 200
        node_names = {node["name"] for node in graph.json().get("nodes", [])}
        assert "主线后置概念" not in node_names
        assert "分叉专属概念" in node_names

    def test_relationship_dimensions_stage_and_events(self, client, auth_headers, db_session):
        world = _create_world(client, auth_headers, "Relationship World")
        course = _create_course(client, auth_headers, world["id"], "Relationship Course")
        course_id = course["id"]

        start = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        # Preload relationship near stage threshold to force stage transition and breakthroughs.
        session = db_session.query(SessionModel).filter(SessionModel.id == session_id).first()
        assert session is not None
        session.relationship = {
            "dimensions": {
                "trust": 0.59,
                "familiarity": 0.59,
                "respect": 0.69,
                "comfort": 0.69,
            },
            "stage": "friend",
            "history": [],
        }
        db_session.commit()

        chat = client.post(
            f"/api/courses/{course_id}/chat",
            json={"message": "我很好奇这个概念之间的联系"},
            headers=auth_headers,
        )
        assert chat.status_code == 200
        payload = chat.json()
        assert payload["relationship_stage"] == "mentor"

        events = payload.get("relationship_events") or []
        assert any(event.get("type") == "stage_change" for event in events)
        assert any(
            event.get("type") == "dimension_breakthrough" and event.get("dimension") in {"trust", "familiarity"}
            for event in events
        )

        stage_records = db_session.query(RelationshipStageRecord).filter(
            RelationshipStageRecord.session_id == session_id
        ).all()
        assert len(stage_records) >= 1


class TestCharacterCourseMigrationFlow:
    def test_course_crud_and_world_binding_paths(self, client, auth_headers):
        character = _create_character(client, auth_headers, "Migration Sage", "sage")
        character_id = character["id"]

        worlds_resp = client.get("/api/worlds", headers=auth_headers)
        assert worlds_resp.status_code == 200
        assert worlds_resp.json() == []

        # Equivalent to Character.vue ensurePrimaryWorldForCharacter path.
        world = _create_world(client, auth_headers, "Migration Sage World")
        world_id = world["id"]
        _bind_character(client, auth_headers, world_id, character_id, "sage", True)

        created = _create_course(client, auth_headers, world_id, "Migration Course A")
        course_id = created["id"]

        listed = client.get(f"/api/worlds/{world_id}/courses", headers=auth_headers)
        assert listed.status_code == 200
        assert any(item["id"] == course_id for item in listed.json())

        updated = client.put(
            f"/api/courses/{course_id}",
            json={
                "world_id": world_id,
                "name": "Migration Course A Updated",
                "description": "updated",
                "target_level": "intermediate",
            },
            headers=auth_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Migration Course A Updated"

        second_world = _create_world(client, auth_headers, "Migration Extra World")
        second_world_id = second_world["id"]
        _bind_character(client, auth_headers, second_world_id, character_id, "traveler", False)
        _create_course(client, auth_headers, second_world_id, "Migration Course B")

        first_world_courses = client.get(f"/api/worlds/{world_id}/courses", headers=auth_headers)
        second_world_courses = client.get(f"/api/worlds/{second_world_id}/courses", headers=auth_headers)
        assert first_world_courses.status_code == 200
        assert second_world_courses.status_code == 200
        assert len(first_world_courses.json()) == 1
        assert len(second_world_courses.json()) == 1

        deleted = client.delete(f"/api/courses/{course_id}", headers=auth_headers)
        assert deleted.status_code == 200
        listed_after_delete = client.get(f"/api/worlds/{world_id}/courses", headers=auth_headers)
        assert listed_after_delete.status_code == 200
        assert listed_after_delete.json() == []
