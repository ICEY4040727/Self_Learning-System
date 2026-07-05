"""BEHAVIOR tests for ProgressFacade seam (v1.0.5)."""

import pytest

from backend.models.models import (
    ConceptMastery,
    Course,
    CourseProgress,
    LessonPlan,
    ProgressTracking,
    User,
    World,
)


def _seed_course_with_lessons(db_session, user_id: int) -> int:
    world = World(user_id=user_id, name="Facade World", description="test")
    db_session.add(world)
    db_session.flush()

    course = Course(
        world_id=world.id,
        name="Facade Course",
        description="test",
        meta={"generated_lessons": [{"title": "L1", "concepts": ["c1"]}]},
    )
    db_session.add(course)
    db_session.flush()

    db_session.add(
        LessonPlan(
            course_id=course.id,
            order_index=0,
            title="Lesson A",
            description="",
            concepts=["c1"],
        )
    )
    db_session.add(
        LessonPlan(
            course_id=course.id,
            order_index=1,
            title="Lesson B",
            description="",
            concepts=["c2"],
        )
    )
    db_session.add(
        CourseProgress(
            course_id=course.id,
            user_id=user_id,
            current_lesson_index=1,
            completed_lesson_ids=[0],
        )
    )
    db_session.commit()
    return course.id


class TestProgressFacadeBehavior:
    def test_canonical_pointer_matches_textbook_and_archive(
        self, client, auth_headers, db_session,
    ):
        user = db_session.query(User).filter_by(username="testuser").one()
        course_id = _seed_course_with_lessons(db_session, user.id)

        textbook_resp = client.get(
            f"/api/courses/{course_id}/progress",
            headers=auth_headers,
        )
        assert textbook_resp.status_code == 200
        textbook_index = textbook_resp.json()["current_index"]

        archive_resp = client.get(
            f"/api/progress?course_id={course_id}",
            headers=auth_headers,
        )
        assert archive_resp.status_code == 200
        assert archive_resp.headers.get("Deprecation") == "true"
        assert (
            archive_resp.headers.get("X-Canonical-Current-Lesson-Index")
            == str(textbook_index)
        )
        assert textbook_index == 1

    def test_archive_post_progress_compat_without_new_progress_tracking_row(
        self, client, auth_headers, db_session,
    ):
        user = db_session.query(User).filter_by(username="testuser").one()
        course_id = _seed_course_with_lessons(db_session, user.id)

        before = db_session.query(ProgressTracking).count()
        resp = client.post(
            "/api/progress",
            json={
                "course_id": course_id,
                "topic": "new_concept",
                "mastery_level": 55,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["topic"] == "new_concept"
        assert payload["mastery_level"] == 55
        assert resp.headers.get("Deprecation") == "true"

        after = db_session.query(ProgressTracking).count()
        assert after == before

        cm = (
            db_session.query(ConceptMastery)
            .filter(
                ConceptMastery.user_id == user.id,
                ConceptMastery.concept_id == "new_concept",
            )
            .one()
        )
        assert cm.mastery_level == 55

    def test_teaching_planner_advance_does_not_insert_progress_tracking(
        self, client, auth_headers, db_session,
    ):
        user = db_session.query(User).filter_by(username="testuser").one()
        course_id = _seed_course_with_lessons(db_session, user.id)

        before = db_session.query(ProgressTracking).count()
        resp = client.post(
            f"/api/courses/{course_id}/advance",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        after = db_session.query(ProgressTracking).count()
        assert after == before

    def test_rollback_flag_restores_archive_progress_tracking_insert(
        self, client, auth_headers, db_session, monkeypatch,
    ):
        from backend.core.config import get_settings

        monkeypatch.setenv("USE_PROGRESS_FACADE", "false")
        get_settings.cache_clear()

        user = db_session.query(User).filter_by(username="testuser").one()
        course_id = _seed_course_with_lessons(db_session, user.id)

        before = db_session.query(ProgressTracking).count()
        resp = client.post(
            "/api/progress",
            json={
                "course_id": course_id,
                "topic": "legacy_topic",
                "mastery_level": 40,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        after = db_session.query(ProgressTracking).count()
        assert after == before + 1

        get_settings.cache_clear()

    def test_handlers_delegate_to_facade_not_direct_orm_insert(self):
        import inspect

        from backend.api.routes import archive as archive_routes
        from backend.services import teaching_planner as teaching_planner_module

        source = inspect.getsource(archive_routes.create_progress)
        assert "progress_facade.create_progress_compat" in source
        assert "ProgressTracking(" not in source

        planner_source = inspect.getsource(teaching_planner_module.TeachingPlanner)
        assert "ProgressTracking" not in planner_source

        textbook_source = open(
            __file__.replace("test_progress_facade.py", "../api/routes/textbook.py"),
            encoding="utf-8",
        ).read()
        assert "progress_facade.get_lesson_progress" in textbook_source
        assert "teaching_planner.get_progress" not in textbook_source.split(
            "get_course_progress",
        )[1].split("def advance_lesson")[0]
