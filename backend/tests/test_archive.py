"""Tests for archive CRUD endpoints (character, world, course)."""

from backend.models.models import Knowledge


class TestCharacterCRUD:
    def test_create_character(self, client, auth_headers):
        resp = client.post("/api/character", json={
            "name": "Socrates",
            "type": "sage",
            "personality": "Wise philosopher",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Socrates"
        assert resp.json()["type"] == "sage"

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
        assert resp.status_code == 200

    def test_update_character(self, client, auth_headers):
        create = client.post("/api/character", json={"name": "Original"}, headers=auth_headers)
        char_id = create.json()["id"]
        resp = client.put(f"/api/character/{char_id}", json={
            "name": "Updated",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

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
            json={"character_id": character_id, "role": "sage", "is_primary": True},
            headers=auth_headers,
        )
        assert bind_resp.status_code == 200
        assert bind_resp.json()["world_id"] == world_id
        assert bind_resp.json()["character_id"] == character_id
        assert bind_resp.json()["role"] == "sage"
        assert bind_resp.json()["is_primary"] is True
        assert bind_resp.json()["character_name"] == "Socrates"

        list_resp = client.get(f"/api/worlds/{world_id}/characters", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
        assert list_resp.json()[0]["character_id"] == character_id
        assert list_resp.json()[0]["role"] == "sage"

        delete_resp = client.delete(
            f"/api/worlds/{world_id}/characters/{character_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 200

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


class TestLegacySubjectsCompatibility:
    def _create_character(self, client, auth_headers, name="LegacyTeacher"):
        resp = client.post(
            "/api/character",
            json={"name": name, "type": "sage"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_legacy_subjects_crud_works(self, client, auth_headers):
        character_id = self._create_character(client, auth_headers)

        create_resp = client.post(
            "/api/subjects",
            json={
                "character_id": character_id,
                "name": "Legacy Subject",
                "description": "compat",
                "target_level": "beginner",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 200
        subject_id = create_resp.json()["id"]

        list_resp = client.get(f"/api/subjects?character_id={character_id}", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
        assert list_resp.json()[0]["name"] == "Legacy Subject"

        detail_resp = client.get(f"/api/subjects/{subject_id}", headers=auth_headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == subject_id

        update_resp = client.put(
            f"/api/subjects/{subject_id}",
            json={
                "character_id": character_id,
                "name": "Legacy Subject Updated",
                "description": "updated",
                "target_level": "intermediate",
            },
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Legacy Subject Updated"

        delete_resp = client.delete(f"/api/subjects/{subject_id}", headers=auth_headers)
        assert delete_resp.status_code == 200


class TestWorldKnowledgeInitialization:
    def test_create_world_initializes_knowledge_row(self, client, auth_headers, db_session):
        create = client.post(
            "/api/worlds",
            json={"name": "Knowledge World", "description": "test"},
            headers=auth_headers,
        )
        assert create.status_code == 200
        world_id = create.json()["id"]

        knowledge = db_session.query(Knowledge).filter(Knowledge.world_id == world_id).first()
        assert knowledge is not None
        assert knowledge.graph == {}

    def test_legacy_subject_auto_world_initializes_knowledge(self, client, auth_headers, db_session):
        character = client.post(
            "/api/character",
            json={"name": "LegacyAutoWorld", "type": "sage"},
            headers=auth_headers,
        )
        assert character.status_code == 200
        character_id = character.json()["id"]

        create_subject = client.post(
            "/api/subjects",
            json={
                "character_id": character_id,
                "name": "Needs Auto World",
                "description": "compat",
                "target_level": "beginner",
            },
            headers=auth_headers,
        )
        assert create_subject.status_code == 200
        world_id = create_subject.json()["world_id"]

        knowledge = db_session.query(Knowledge).filter(Knowledge.world_id == world_id).first()
        assert knowledge is not None
        assert knowledge.graph == {}

    def test_existing_world_link_backfills_missing_knowledge(self, client, auth_headers, db_session):
        character = client.post(
            "/api/character",
            json={"name": "KnowledgeBackfill", "type": "sage"},
            headers=auth_headers,
        )
        assert character.status_code == 200
        character_id = character.json()["id"]

        world = client.post(
            "/api/worlds",
            json={"name": "Backfill World", "description": "test"},
            headers=auth_headers,
        )
        assert world.status_code == 200
        world_id = world.json()["id"]

        bind = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage", "is_primary": True},
            headers=auth_headers,
        )
        assert bind.status_code == 200

        db_session.query(Knowledge).filter(Knowledge.world_id == world_id).delete()
        db_session.commit()
        assert db_session.query(Knowledge).filter(Knowledge.world_id == world_id).count() == 0

        create_subject = client.post(
            "/api/subjects",
            json={
                "character_id": character_id,
                "name": "Backfill Trigger",
                "description": "legacy resolver path",
                "target_level": "beginner",
            },
            headers=auth_headers,
        )
        assert create_subject.status_code == 200
        assert create_subject.json()["world_id"] == world_id

        knowledge_rows = db_session.query(Knowledge).filter(Knowledge.world_id == world_id).all()
        assert len(knowledge_rows) == 1
        assert knowledge_rows[0].graph == {}

    def test_resolver_path_is_idempotent_for_knowledge(self, client, auth_headers, db_session):
        character = client.post(
            "/api/character",
            json={"name": "KnowledgeIdempotent", "type": "sage"},
            headers=auth_headers,
        )
        assert character.status_code == 200
        character_id = character.json()["id"]

        world = client.post(
            "/api/worlds",
            json={"name": "Idempotent World", "description": "test"},
            headers=auth_headers,
        )
        assert world.status_code == 200
        world_id = world.json()["id"]

        bind = client.post(
            f"/api/worlds/{world_id}/characters",
            json={"character_id": character_id, "role": "sage", "is_primary": True},
            headers=auth_headers,
        )
        assert bind.status_code == 200

        first_subject = client.post(
            "/api/subjects",
            json={
                "character_id": character_id,
                "name": "First Subject",
                "description": "legacy",
                "target_level": "beginner",
            },
            headers=auth_headers,
        )
        assert first_subject.status_code == 200
        assert first_subject.json()["world_id"] == world_id

        second_subject = client.post(
            "/api/subjects",
            json={
                "character_id": character_id,
                "name": "Second Subject",
                "description": "legacy",
                "target_level": "intermediate",
            },
            headers=auth_headers,
        )
        assert second_subject.status_code == 200
        assert second_subject.json()["world_id"] == world_id

        assert db_session.query(Knowledge).filter(Knowledge.world_id == world_id).count() == 1
