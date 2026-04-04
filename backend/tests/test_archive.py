"""Tests for archive CRUD endpoints (character, world, course)."""


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
