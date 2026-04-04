"""Tests for checkpoint endpoints replacing legacy save endpoints."""


def _create_world(client, auth_headers):
    resp = client.post(
        "/api/worlds",
        json={"name": "Checkpoint World", "description": "test world"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_course(client, auth_headers, world_id):
    resp = client.post(
        "/api/courses",
        json={"world_id": world_id, "name": "Checkpoint Course"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


class TestCheckpointCRUD:
    def test_create_list_get_delete_checkpoint(self, client, auth_headers):
        world_id = _create_world(client, auth_headers)
        course_id = _create_course(client, auth_headers, world_id)

        start = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        create = client.post(
            "/api/checkpoints",
            json={
                "world_id": world_id,
                "session_id": session_id,
                "save_name": "cp1",
            },
            headers=auth_headers,
        )
        assert create.status_code == 200
        checkpoint_id = create.json()["id"]
        assert create.json()["world_id"] == world_id

        listed = client.get(f"/api/checkpoints?world_id={world_id}", headers=auth_headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = client.get(f"/api/checkpoints/{checkpoint_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["save_name"] == "cp1"
        assert "state" in detail.json()

        deleted = client.delete(f"/api/checkpoints/{checkpoint_id}", headers=auth_headers)
        assert deleted.status_code == 200

        listed_after = client.get(f"/api/checkpoints?world_id={world_id}", headers=auth_headers)
        assert listed_after.status_code == 200
        assert listed_after.json() == []


class TestLegacySaveCompatibility:
    def test_legacy_save_endpoints_work(self, client, auth_headers):
        world_id = _create_world(client, auth_headers)
        course_id = _create_course(client, auth_headers, world_id)

        start = client.post(f"/api/subjects/{course_id}/start", headers=auth_headers)
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        create = client.post(
            "/api/save",
            json={
                "subject_id": course_id,
                "session_id": session_id,
                "save_name": "legacy_cp",
            },
            headers=auth_headers,
        )
        assert create.status_code == 200
        save_id = create.json()["id"]

        listed = client.get(f"/api/save?subject_id={course_id}", headers=auth_headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["save_name"] == "legacy_cp"

        detail = client.get(f"/api/save/{save_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["session_meta"]["subject_id"] == course_id
        assert "relationship_stage" in detail.json()["data"]

        deleted = client.delete(f"/api/save/{save_id}", headers=auth_headers)
        assert deleted.status_code == 200
