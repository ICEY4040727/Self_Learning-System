"""Tests for archive CRUD endpoints (character, persona, subject)."""


class TestCharacterCRUD:
    def test_create_character(self, client, auth_headers):
        resp = client.post("/api/character", json={
            "name": "Socrates",
            "personality": "Wise philosopher",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Socrates"

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


class TestSubjectCRUD:
    def _create_character(self, client, auth_headers):
        resp = client.post("/api/character", json={"name": "TestChar"}, headers=auth_headers)
        return resp.json()["id"]

    def test_create_subject(self, client, auth_headers):
        char_id = self._create_character(client, auth_headers)
        resp = client.post("/api/subjects", json={
            "character_id": char_id,
            "name": "Mathematics",
            "target_level": "intermediate",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Mathematics"

    def test_list_subjects(self, client, auth_headers):
        char_id = self._create_character(client, auth_headers)
        client.post("/api/subjects", json={"character_id": char_id, "name": "Math"}, headers=auth_headers)
        client.post("/api/subjects", json={"character_id": char_id, "name": "Physics"}, headers=auth_headers)
        resp = client.get(f"/api/subjects?character_id={char_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
