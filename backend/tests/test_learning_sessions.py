"""Tests for course sessions and relationship JSON behavior."""

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
