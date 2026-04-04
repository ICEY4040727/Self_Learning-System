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

    def test_world_course_checkpoint_timeline_chain(self, client, auth_headers):
        world = client.post(
            "/api/worlds",
            json={"name": "Timeline World", "description": "timeline"},
            headers=auth_headers,
        )
        assert world.status_code == 200
        world_id = world.json()["id"]

        course = client.post(
            f"/api/worlds/{world_id}/courses",
            json={"name": "Timeline Course", "description": "test", "target_level": "beginner"},
            headers=auth_headers,
        )
        assert course.status_code == 200
        course_id = course.json()["id"]

        start = client.post(f"/api/courses/{course_id}/start", headers=auth_headers)
        assert start.status_code == 200
        source_session_id = start.json()["session_id"]

        chat = client.post(
            f"/api/courses/{course_id}/chat",
            json={"message": "我们来讨论递归"},
            headers=auth_headers,
        )
        assert chat.status_code == 200

        checkpoint = client.post(
            "/api/checkpoints",
            json={"world_id": world_id, "session_id": source_session_id, "save_name": "timeline_cp"},
            headers=auth_headers,
        )
        assert checkpoint.status_code == 200
        checkpoint_id = checkpoint.json()["id"]

        world_checkpoints = client.get(f"/api/worlds/{world_id}/checkpoints", headers=auth_headers)
        assert world_checkpoints.status_code == 200
        assert len(world_checkpoints.json()) == 1
        assert world_checkpoints.json()[0]["id"] == checkpoint_id

        branch = client.post(
            f"/api/checkpoints/{checkpoint_id}/branch",
            json={"branch_name": "alt-line"},
            headers=auth_headers,
        )
        assert branch.status_code == 200
        branched_session_id = branch.json()["session_id"]
        assert branched_session_id != source_session_id
        assert branch.json()["parent_checkpoint_id"] == checkpoint_id

        timelines = client.get(f"/api/worlds/{world_id}/timelines", headers=auth_headers)
        assert timelines.status_code == 200
        payload = timelines.json()
        session_ids = {item["id"] for item in payload["sessions"]}
        assert source_session_id in session_ids
        assert branched_session_id in session_ids
        branched = [item for item in payload["sessions"] if item["id"] == branched_session_id][0]
        assert branched["parent_checkpoint_id"] == checkpoint_id


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

    def test_legacy_save_subject_filter_is_subject_scoped(self, client, auth_headers):
        world_id = _create_world(client, auth_headers)
        course_a = _create_course(client, auth_headers, world_id)
        course_b = _create_course(client, auth_headers, world_id)

        start_a = client.post(f"/api/subjects/{course_a}/start", headers=auth_headers)
        assert start_a.status_code == 200
        session_a = start_a.json()["session_id"]

        start_b = client.post(f"/api/subjects/{course_b}/start", headers=auth_headers)
        assert start_b.status_code == 200
        session_b = start_b.json()["session_id"]

        save_a = client.post(
            "/api/save",
            json={
                "subject_id": course_a,
                "session_id": session_a,
                "save_name": "legacy_a",
            },
            headers=auth_headers,
        )
        assert save_a.status_code == 200

        save_b = client.post(
            "/api/save",
            json={
                "subject_id": course_b,
                "session_id": session_b,
                "save_name": "legacy_b",
            },
            headers=auth_headers,
        )
        assert save_b.status_code == 200

        list_a = client.get(f"/api/save?subject_id={course_a}", headers=auth_headers)
        assert list_a.status_code == 200
        assert len(list_a.json()) == 1
        assert list_a.json()[0]["save_name"] == "legacy_a"

        list_b = client.get(f"/api/save?subject_id={course_b}", headers=auth_headers)
        assert list_b.status_code == 200
        assert len(list_b.json()) == 1
        assert list_b.json()[0]["save_name"] == "legacy_b"
