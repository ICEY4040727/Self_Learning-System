"""BEHAVIOR tests for Seam A2-1 — lesson pointer single source."""

from pathlib import Path

from backend.models.models import (
    ConceptMastery,
    Course,
    CourseProgress,
    LessonPlan,
    MemoryFact,
    User,
    World,
)
from backend.services.mastery_tracker import AUTO_ADVANCE_THRESHOLD, mastery_tracker
from backend.services.teaching_planner import teaching_planner


ROOT = Path(__file__).resolve().parents[2]


def _seed_test_user(db_session, username: str) -> User:
    user = User(username=username, password_hash="hash", role="user")  # NOSONAR
    db_session.add(user)
    db_session.flush()
    return user


def _seed_dual_source_course(db_session, *, cp_index: int = 0, meta_index: int = 5):
    """CourseProgress 与 course.meta 故意分叉。"""
    user = _seed_test_user(db_session, "a2-dual")

    world = World(user_id=user.id, name="A2 World", scenes={})
    db_session.add(world)
    db_session.flush()

    course = Course(
        world_id=world.id,
        name="A2 Course",
        meta={
            "generated_lessons": [
                {"title": "Lesson 0", "concepts": ["递归"]},
                {"title": "Lesson 1", "concepts": ["循环"]},
            ],
            "current_lesson_index": meta_index,
            "completed_lessons": [],
        },
    )
    db_session.add(course)
    db_session.flush()

    for i, (title, concepts) in enumerate(
        [("Lesson 0", ["递归"]), ("Lesson 1", ["循环"])]
    ):
        db_session.add(
            LessonPlan(
                course_id=course.id,
                order_index=i,
                title=title,
                description="",
                concepts=concepts,
            )
        )

    db_session.add(
        CourseProgress(
            course_id=course.id,
            user_id=user.id,
            current_lesson_index=cp_index,
            completed_lesson_ids=[],
        )
    )
    db_session.flush()
    db_session.refresh(course)
    return user, course


def _seed_meta_only_course(db_session):
    user = _seed_test_user(db_session, "a2-meta")

    world = World(user_id=user.id, name="Legacy World", scenes={})
    db_session.add(world)
    db_session.flush()

    course = Course(
        world_id=world.id,
        name="Legacy Course",
        meta={
            "generated_lessons": [
                {"title": "L0", "concepts": ["变量"]},
                {"title": "L1", "concepts": ["函数"]},
            ],
            "current_lesson_index": 0,
            "completed_lessons": [],
        },
    )
    db_session.add(course)
    db_session.flush()
    db_session.refresh(course)
    return user, course


class TestLessonPointerHardEvidence:
    def test_mastery_tracker_does_not_assign_lesson_pointer_in_meta(self):
        source = (ROOT / "backend/services/mastery_tracker.py").read_text(encoding="utf-8")
        assert 'course.meta["current_lesson_index"]' not in source
        assert 'course.meta["completed_lessons"]' not in source


class TestTryAutoAdvanceIfMastered:
    def test_auto_advance_writes_course_progress_not_stale_meta(self, db_session):
        user, course = _seed_dual_source_course(db_session, cp_index=0, meta_index=5)

        db_session.add(
            ConceptMastery(
                user_id=user.id,
                concept_id="递归",
                mastery_level=AUTO_ADVANCE_THRESHOLD,
            )
        )
        db_session.flush()

        advanced, new_idx = teaching_planner.try_auto_advance_if_mastered(
            db_session, course, user.id,
        )
        db_session.flush()

        assert advanced is True
        assert new_idx == 1

        cp = db_session.query(CourseProgress).filter_by(
            course_id=course.id, user_id=user.id,
        ).one()
        assert cp.current_lesson_index == 1
        assert 0 in (cp.completed_lesson_ids or [])

        db_session.refresh(course)
        assert course.meta["current_lesson_index"] == 5

        progress = teaching_planner.get_progress(db_session, course)
        assert progress["current_index"] == 1

    def test_auto_advance_at_last_lesson_is_noop(self, db_session):
        user, course = _seed_dual_source_course(db_session, cp_index=1, meta_index=0)
        db_session.add(
            ConceptMastery(
                user_id=user.id,
                concept_id="循环",
                mastery_level=AUTO_ADVANCE_THRESHOLD,
            )
        )
        db_session.flush()

        advanced, new_idx = teaching_planner.try_auto_advance_if_mastered(
            db_session, course, user.id,
        )
        assert advanced is False
        assert new_idx is None


class TestDualSourceRegression:
    def test_memory_auto_advance_updates_canonical_progress_with_stale_meta(
        self, db_session,
    ):
        user, course = _seed_dual_source_course(db_session, cp_index=0, meta_index=5)

        fact = MemoryFact(
            character_id=1,
            world_id=course.world_id,
            fact_type="concept_mastered",
            content="ok",
            concept_tags=["递归"],
            salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()

        result = mastery_tracker.update_from_memories(
            db=db_session,
            memories=[fact],
            course_id=course.id,
            world_id=course.world_id,
            user_id=user.id,
        )
        db_session.flush()

        assert result["auto_advanced"] is True
        assert result["new_lesson_index"] == 1

        progress = teaching_planner.get_progress(db_session, course)
        assert progress["current_index"] == 1

        cp = db_session.query(CourseProgress).filter_by(
            course_id=course.id, user_id=user.id,
        ).one()
        assert cp.current_lesson_index == 1
        assert course.meta["current_lesson_index"] == 5

    def test_manual_advance_then_auto_advance_is_monotonic(self, client, auth_headers, db_session):
        user = db_session.query(User).filter_by(username="testuser").one()
        user_id = user.id

        world = World(user_id=user_id, name="Mono World", description="")
        db_session.add(world)
        db_session.flush()

        course = Course(
            world_id=world.id,
            name="Mono Course",
            meta={"generated_lessons": [], "current_lesson_index": 0, "completed_lessons": []},
        )
        db_session.add(course)
        db_session.flush()

        for i, (title, concepts) in enumerate(
            [("L0", ["a"]), ("L1", ["b"]), ("L2", ["c"])]
        ):
            db_session.add(
                LessonPlan(
                    course_id=course.id,
                    order_index=i,
                    title=title,
                    concepts=concepts,
                )
            )
        db_session.add(
            CourseProgress(
                course_id=course.id,
                user_id=user_id,
                current_lesson_index=0,
                completed_lesson_ids=[],
            )
        )
        db_session.commit()

        course_id = course.id

        manual = client.post(f"/api/courses/{course_id}/advance", headers=auth_headers)
        assert manual.status_code == 200
        assert manual.json()["current_index"] == 1

        db_session.expire_all()
        course = db_session.query(Course).filter(Course.id == course_id).one()
        db_session.add(
            ConceptMastery(
                user_id=user_id,
                concept_id="b",
                mastery_level=AUTO_ADVANCE_THRESHOLD,
            )
        )
        fact = MemoryFact(
            character_id=1,
            world_id=course.world_id,
            fact_type="concept_mastered",
            content="ok",
            concept_tags=["b"],
            salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()

        result = mastery_tracker.update_from_memories(
            db=db_session,
            memories=[fact],
            course_id=course_id,
            world_id=course.world_id,
            user_id=user_id,
        )
        db_session.flush()

        assert result["auto_advanced"] is True
        assert result["new_lesson_index"] == 2

        canonical = client.get(f"/api/courses/{course_id}/progress", headers=auth_headers)
        assert canonical.status_code == 200
        assert canonical.json()["current_index"] == 2


class TestLegacyMetaFallback:
    def test_auto_advance_without_course_progress_writes_meta(self, db_session):
        user, course = _seed_meta_only_course(db_session)

        db_session.add(
            ConceptMastery(
                user_id=user.id,
                concept_id="变量",
                mastery_level=AUTO_ADVANCE_THRESHOLD,
            )
        )
        db_session.flush()

        advanced, new_idx = teaching_planner.try_auto_advance_if_mastered(
            db_session, course, user.id,
        )
        db_session.flush()
        db_session.refresh(course)

        assert advanced is True
        assert new_idx == 1
        assert course.meta["current_lesson_index"] == 1
        assert 0 in course.meta["completed_lessons"]

        progress = teaching_planner.get_progress(db_session, course)
        assert progress["current_index"] == 1


class TestLearningEntryAlignment:
    def test_learning_course_progress_read_matches_canonical(self, db_session):
        """learning.py 读 CourseProgress；与 teaching_planner canonical 一致。"""
        user, course = _seed_dual_source_course(db_session, cp_index=1, meta_index=0)

        canonical = teaching_planner.get_progress(db_session, course)["current_index"]

        cp = db_session.query(CourseProgress).filter(
            CourseProgress.course_id == course.id,
            CourseProgress.user_id == user.id,
        ).one()
        lesson_index_as_learning = cp.current_lesson_index or 0

        assert lesson_index_as_learning == canonical == 1
        assert course.meta["current_lesson_index"] == 0

    def test_progress_api_matches_learning_read_after_auto_advance(
        self, client, auth_headers, db_session,
    ):
        user = db_session.query(User).filter_by(username="testuser").one()
        world = World(user_id=user.id, name="API Align World", description="")
        db_session.add(world)
        db_session.flush()

        course = Course(
            world_id=world.id,
            name="API Align Course",
            meta={
                "generated_lessons": [
                    {"title": "Lesson 0", "concepts": ["递归"]},
                    {"title": "Lesson 1", "concepts": ["循环"]},
                ],
                "current_lesson_index": 9,
                "completed_lessons": [],
            },
        )
        db_session.add(course)
        db_session.flush()

        for i, (title, concepts) in enumerate(
            [("Lesson 0", ["递归"]), ("Lesson 1", ["循环"])]
        ):
            db_session.add(
                LessonPlan(
                    course_id=course.id,
                    order_index=i,
                    title=title,
                    concepts=concepts,
                )
            )
        db_session.add(
            CourseProgress(
                course_id=course.id,
                user_id=user.id,
                current_lesson_index=0,
                completed_lesson_ids=[],
            )
        )
        db_session.commit()

        fact = MemoryFact(
            character_id=1,
            world_id=course.world_id,
            fact_type="concept_mastered",
            content="ok",
            concept_tags=["递归"],
            salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()

        mastery_tracker.update_from_memories(
            db=db_session,
            memories=[fact],
            course_id=course.id,
            world_id=course.world_id,
            user_id=user.id,
        )
        db_session.commit()

        api_progress = client.get(
            f"/api/courses/{course.id}/progress",
            headers=auth_headers,
        )
        assert api_progress.status_code == 200
        api_index = api_progress.json()["current_index"]

        cp = db_session.query(CourseProgress).filter(
            CourseProgress.course_id == course.id,
            CourseProgress.user_id == user.id,
        ).one()
        assert cp.current_lesson_index == api_index == 1


class TestA22CanonicalLessonReads:
    def test_course_content_uses_planner_not_direct_course_progress(self):
        source = (
            ROOT / "backend/services/prompt_builder/modules/course_content.py"
        ).read_text(encoding="utf-8")
        start = source.index("def _get_lessons_and_progress")
        rest = source[start + 1:]
        next_def = rest.index("\n    def ")
        chunk = source[start: start + 1 + next_def]
        assert "query(CourseProgress)" not in chunk

    def test_course_content_honors_course_progress_over_stale_meta(
        self, db_session,
    ):
        from backend.services.prompt_builder.modules.course_content import (
            CourseContentModule,
        )

        user, course = _seed_dual_source_course(
            db_session, cp_index=1, meta_index=5,
        )
        db_session.commit()

        module = CourseContentModule()
        rendered = module.assemble({
            "db": db_session,
            "course_id": course.id,
        })

        assert "第2课: Lesson 1" in rendered
        assert "[当前章节]" in rendered
        assert "第1课: Lesson 0" in rendered
        assert "已完成" in rendered
