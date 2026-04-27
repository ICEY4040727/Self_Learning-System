"""Tests for Phase 3 Step 4: 掌握度追踪与自适应进度

- MasteryTracker 核心逻辑
- 掌握度更新 + 自动推进
- FSRS 调度
- 课程掌握度概览

NOTE: TestMasteryTracker below uses MagicMock heavily — DB constraints are
NOT exercised. Real-DB regression coverage lives in TestMasteryTrackerRealDB
at the bottom of this file. Add to that class when adding tests that touch
INSERT paths.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.models import (
    Course,
    MemoryFact,
    ProgressTracking,
    FSRSState,
    User,
    World,
)
from backend.services.mastery_tracker import (
    MasteryTracker,
    AUTO_ADVANCE_THRESHOLD,
    mastery_tracker,
)


class TestMasteryTracker:
    """MasteryTracker 单元测试"""

    def setup_method(self):
        self.tracker = MasteryTracker()

    def _make_fact(self, fact_type, concept_tags, content="test") -> MemoryFact:
        fact = MagicMock(spec=MemoryFact)
        fact.fact_type = fact_type
        fact.concept_tags = concept_tags
        fact.content = content
        return fact

    def _make_course(self, lessons=None, current_idx=0, completed=None) -> Course:
        course = MagicMock(spec=Course)
        course.id = 1
        course.meta = {
            "generated_lessons": lessons or [],
            "current_lesson_index": current_idx,
            "completed_lessons": completed or [],
        }
        return course

    # ── update_from_memories ───────────────────────────────────────

    def test_update_empty_memories(self):
        result = self.tracker.update_from_memories(
            db=MagicMock(), memories=[], course_id=1, world_id=1, user_id=1,
        )
        assert result["updated_concepts"] == []
        assert result["auto_advanced"] is False

    def test_update_no_course(self):
        db = MagicMock()
        db.query().filter().first.return_value = None
        result = self.tracker.update_from_memories(
            db=db,
            memories=[self._make_fact("student_state", ["x"])],
            course_id=999,
            world_id=1, user_id=1,
        )
        assert result["updated_concepts"] == []

    def test_update_concept_mastered(self):
        db = MagicMock()
        course = self._make_course()

        with patch.object(self.tracker, '_update_concept_mastery') as mock_update, \
             patch.object(self.tracker, '_schedule_review') as mock_review:
            # db.query(Course).filter().first() → course
            db.query.return_value.filter.return_value.first.return_value = course

            facts = [self._make_fact("concept_mastered", ["变量", "类型"])]
            result = self.tracker.update_from_memories(
                db=db, memories=facts, course_id=1, world_id=1, user_id=1,
            )

            assert "变量" in result["updated_concepts"]
            assert "类型" in result["updated_concepts"]
            assert mock_review.call_count == 2  # both concepts scheduled

    def test_update_concept_struggle(self):
        db = MagicMock()
        course = self._make_course()

        # [TODO-T2] struggle now also triggers _schedule_review, patch it.
        with patch.object(self.tracker, '_update_concept_mastery') as mock_update, \
             patch.object(self.tracker, '_check_lesson_mastered', return_value=False), \
             patch.object(self.tracker, '_schedule_review'):
            db.query.return_value.filter.return_value.first.return_value = course

            facts = [self._make_fact("concept_struggle", ["循环"])]
            result = self.tracker.update_from_memories(
                db=db, memories=facts, course_id=1, world_id=1, user_id=1,
            )

            assert "循环" in result["updated_concepts"]
            # mastery delta should be -15
            mock_update.assert_called_once()
            assert mock_update.call_args.kwargs["concept"] == "循环"
            assert mock_update.call_args.kwargs["delta"] == -15

    def test_update_ignores_non_concept_facts(self):
        db = MagicMock()
        facts = [
            self._make_fact("student_state", ["状态"]),
            self._make_fact("preference", ["偏好"]),
            self._make_fact("event", ["事件"]),
        ]
        result = self.tracker.update_from_memories(
            db=db, memories=facts, course_id=1, world_id=1, user_id=1,
        )
        assert result["updated_concepts"] == []

    def test_update_ignores_facts_without_concept_tags(self):
        db = MagicMock()
        facts = [self._make_fact("concept_mastered", [])]
        result = self.tracker.update_from_memories(
            db=db, memories=facts, course_id=1, world_id=1, user_id=1,
        )
        assert result["updated_concepts"] == []

    # ── auto advance ───────────────────────────────────────────────

    def test_auto_advance_when_all_concepts_mastered(self):
        db = MagicMock()

        lessons = [
            {"title": "L1", "concepts": ["变量", "类型"]},
            {"title": "L2", "concepts": ["循环"]},
        ]
        course = self._make_course(lessons=lessons, current_idx=0)
        db.query.return_value.filter.return_value.first.return_value = course

        with patch.object(self.tracker, '_update_concept_mastery'), \
             patch.object(self.tracker, '_schedule_review'), \
             patch.object(self.tracker, '_check_lesson_mastered', return_value=True), \
             patch.object(self.tracker, '_try_auto_advance', return_value=(True, 1)):
            facts = [self._make_fact("concept_mastered", ["变量"])]
            result = self.tracker.update_from_memories(
                db=db, memories=facts, course_id=1, world_id=1, user_id=1,
            )
            assert result["auto_advanced"] is True
            assert result["new_lesson_index"] == 1

    def test_no_auto_advance_at_last_lesson(self):
        db = MagicMock()
        lessons = [{"title": "L1", "concepts": ["a"]}]
        course = self._make_course(lessons=lessons, current_idx=0)
        db.query.return_value.filter.return_value.first.return_value = course

        with patch.object(self.tracker, '_update_concept_mastery'), \
             patch.object(self.tracker, '_schedule_review'), \
             patch.object(self.tracker, '_check_lesson_mastered', return_value=True), \
             patch.object(self.tracker, '_try_auto_advance', return_value=(False, None)):
            facts = [self._make_fact("concept_mastered", ["a"])]
            result = self.tracker.update_from_memories(
                db=db, memories=facts, course_id=1, world_id=1, user_id=1,
            )
            assert result["auto_advanced"] is False

    # ── _update_concept_mastery ────────────────────────────────────

    def test_update_concept_mastery_new(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        self.tracker._update_concept_mastery(db, 1, "变量", 25, 1, 1)

        # Should have added a new tracking
        assert db.add.called

    def test_update_concept_mastery_existing(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 50
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, 1, "变量", 25, 1, 1)

        assert tracking.mastery_level == 75
        assert not db.add.called

    def test_update_concept_mastery_clamped_max(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 90
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, 1, "变量", 25, 1, 1)
        assert tracking.mastery_level == 100  # clamped

    def test_update_concept_mastery_clamped_min(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 10
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, 1, "变量", -15, 1, 1)
        assert tracking.mastery_level == 0  # clamped

    # ── _check_lesson_mastered ─────────────────────────────────────

    def test_check_lesson_mastered_true(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = AUTO_ADVANCE_THRESHOLD
        db.query().filter().first.return_value = tracking

        result = self.tracker._check_lesson_mastered(db, 1, ["a", "b"])
        assert result is True

    def test_check_lesson_mastered_false_low_mastery(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 30
        db.query().filter().first.return_value = tracking

        result = self.tracker._check_lesson_mastered(db, 1, ["a"])
        assert result is False

    def test_check_lesson_mastered_false_untracked(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        result = self.tracker._check_lesson_mastered(db, 1, ["a"])
        assert result is False

    def test_check_lesson_mastered_empty_concepts(self):
        result = self.tracker._check_lesson_mastered(MagicMock(), 1, [])
        assert result is False

    # ── _try_auto_advance ──────────────────────────────────────────

    def test_try_auto_advance_success(self):
        db = MagicMock()
        lessons = [{"title": "L1"}, {"title": "L2"}]
        course = self._make_course(lessons=lessons, current_idx=0)

        with patch("sqlalchemy.orm.attributes.flag_modified"):
            success, new_idx = self.tracker._try_auto_advance(db, course)
            assert success is True
            assert new_idx == 1
            assert course.meta["current_lesson_index"] == 1
            assert 0 in course.meta["completed_lessons"]

    def test_try_auto_advance_at_end(self):
        db = MagicMock()
        lessons = [{"title": "L1"}, {"title": "L2"}]
        course = self._make_course(lessons=lessons, current_idx=1)

        with patch("sqlalchemy.orm.attributes.flag_modified"):
            success, new_idx = self.tracker._try_auto_advance(db, course)
            assert success is False
            assert new_idx is None

    # ── get_course_mastery ─────────────────────────────────────────

    def test_get_course_mastery_empty(self):
        db = MagicMock()
        db.query().filter().all.return_value = []

        result = self.tracker.get_course_mastery(db, 1)
        assert result["overall_mastery"] == 0.0
        assert result["concepts"] == {}
        assert result["weak_concepts"] == []
        assert result["mastered_count"] == 0

    def test_get_course_mastery_with_data(self):
        db = MagicMock()

        t1 = MagicMock()
        t1.topic = "变量"
        t1.mastery_level = 80

        t2 = MagicMock()
        t2.topic = "循环"
        t2.mastery_level = 30

        t3 = MagicMock()
        t3.topic = "函数"
        t3.mastery_level = 75

        db.query().filter().all.return_value = [t1, t2, t3]

        result = self.tracker.get_course_mastery(db, 1)
        assert result["overall_mastery"] == 61.7  # (80+30+75)/3
        assert result["concepts"]["变量"] == 80
        assert "循环" in result["weak_concepts"]
        assert result["mastered_count"] == 2  # 80 and 75 >= 70
        assert result["total_tracked"] == 3

    # ── _schedule_review ───────────────────────────────────────────

    def test_schedule_review_new(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        self.tracker._schedule_review(db, 1, "变量")
        assert db.add.called

    def test_schedule_review_existing(self):
        db = MagicMock()
        fsrs = MagicMock()
        fsrs.reps = 2
        fsrs.stability = 3.0
        db.query().filter().first.return_value = fsrs

        self.tracker._schedule_review(db, 1, "变量")
        assert fsrs.reps == 3
        assert fsrs.stability == 4.5  # 3.0 * 1.5
        assert not db.add.called


class TestMasteryTrackerRealDB:
    """[TODO-T1] Real-DB regression tests — exercises actual SQL constraints
    that MagicMock-based tests above cannot catch.

    Add tests here whenever the code path performs an INSERT/UPDATE on a
    table with NOT NULL or FK constraints, or whenever a previous bug only
    surfaced under real DB semantics."""

    def _seed_user_world_course(self, db_session) -> tuple[int, int, int]:
        u = User(username="t-mastery", password_hash="x", role="user")
        db_session.add(u)
        db_session.flush()
        w = World(user_id=u.id, name="W", scenes={})
        db_session.add(w)
        db_session.flush()
        c = Course(world_id=w.id, name="C", meta={})
        db_session.add(c)
        db_session.flush()
        return u.id, w.id, c.id

    def test_update_from_memories_inserts_progress_tracking_with_user_id(self, db_session):
        """[TODO-T1] Regression: ProgressTracking.user_id is NOT NULL on the
        real schema. The previous implementation omitted it, so any production
        run hit IntegrityError on first INSERT. This test would have caught
        the bug if it existed in the new code."""
        user_id, world_id, course_id = self._seed_user_world_course(db_session)

        fact = MemoryFact(
            character_id=1,
            world_id=world_id,
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
            course_id=course_id,
            world_id=world_id,
            user_id=user_id,
        )
        db_session.flush()  # would raise IntegrityError if user_id missing

        assert result["updated_concepts"] == ["递归"]

        rows = db_session.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.topic == "递归",
        ).all()
        assert len(rows) == 1
        assert rows[0].user_id == user_id
        assert rows[0].mastery_level == 75  # 50 + 25 (concept_mastered delta)

    def test_topic_type_isolates_concept_from_lesson(self, db_session):
        """[TODO-T3] A lesson title equal to a concept name must not collide.
        Without topic_type, the two writers stomped each other."""
        from backend.services.teaching_planner import teaching_planner

        user_id, world_id, course_id = self._seed_user_world_course(db_session)
        # Set up course with a lesson titled exactly the same as a concept.
        course = db_session.query(Course).filter(Course.id == course_id).first()
        course.meta = {
            "generated_lessons": [
                {"title": "递归", "description": "", "concepts": ["递归"]},
            ],
            "current_lesson_index": 0,
            "completed_lessons": [],
        }
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(course, "meta")
        db_session.flush()

        # mastery_tracker writes a 'concept' row for "递归"
        fact = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_mastered",
            content="ok", concept_tags=["递归"], salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()
        mastery_tracker.update_from_memories(
            db=db_session, memories=[fact],
            course_id=course_id, world_id=world_id, user_id=user_id,
        )

        # teaching_planner writes a 'lesson' row also titled "递归"
        teaching_planner._record_lesson_progress(db_session, course, 0)
        db_session.flush()

        rows = db_session.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.topic == "递归",
        ).all()
        assert len(rows) == 2, "concept and lesson rows must coexist"
        types = {r.topic_type for r in rows}
        assert types == {"concept", "lesson"}

        # mastery overview must report only the concept row
        overview = mastery_tracker.get_course_mastery(db_session, course_id)
        assert overview["total_tracked"] == 1
        assert "递归" in overview["concepts"]

    def test_struggle_schedules_fsrs_with_short_interval(self, db_session):
        """[TODO-T2] concept_struggle must also schedule FSRS — and with a
        SHORTER interval than mastered, since the student needs to revisit."""
        user_id, world_id, course_id = self._seed_user_world_course(db_session)
        struggle_fact = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_struggle",
            content="不懂", concept_tags=["递归"], salience=0.6,
        )
        db_session.add(struggle_fact)
        db_session.flush()

        mastery_tracker.update_from_memories(
            db=db_session, memories=[struggle_fact],
            course_id=course_id, world_id=world_id, user_id=user_id,
        )
        db_session.flush()

        fsrs = db_session.query(FSRSState).filter(
            FSRSState.world_id == world_id,
            FSRSState.concept_id == "递归",
        ).first()
        assert fsrs is not None, "struggle must trigger FSRS schedule"
        assert fsrs.reps == 0, "struggle should reset reps, not increment"
        assert fsrs.stability < 1.0, "struggle should start with sub-1.0 stability"

    def test_struggle_then_mastered_recovers(self, db_session):
        """Struggling first then mastering same concept: stability grows from
        the shrunken value, not reset."""
        user_id, world_id, course_id = self._seed_user_world_course(db_session)
        struggle = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_struggle",
            content="不懂", concept_tags=["递归"], salience=0.6,
        )
        mastered = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_mastered",
            content="懂了", concept_tags=["递归"], salience=0.7,
        )
        db_session.add_all([struggle, mastered])
        db_session.flush()

        mastery_tracker.update_from_memories(
            db=db_session, memories=[struggle],
            course_id=course_id, world_id=world_id, user_id=user_id,
        )
        mastery_tracker.update_from_memories(
            db=db_session, memories=[mastered],
            course_id=course_id, world_id=world_id, user_id=user_id,
        )
        db_session.flush()

        fsrs = db_session.query(FSRSState).filter(
            FSRSState.world_id == world_id,
            FSRSState.concept_id == "递归",
        ).first()
        assert fsrs.reps == 1, "mastered after struggle: reps from 0 → 1"
        assert fsrs.stability > 0.5, "stability should grow from 0.5 (post-struggle)"

    def test_update_existing_tracking_keyed_by_user(self, db_session):
        """Same course + same topic but different users → separate rows
        (user_id participates in lookup, not just course_id+topic)."""
        u1, world_id, course_id = self._seed_user_world_course(db_session)
        u2 = User(username="t-mastery-2", password_hash="x", role="user")
        db_session.add(u2)
        db_session.flush()

        fact = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_mastered",
            content="ok", concept_tags=["递归"], salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()

        for uid in (u1, u2.id):
            mastery_tracker.update_from_memories(
                db=db_session, memories=[fact],
                course_id=course_id, world_id=world_id, user_id=uid,
            )
        db_session.flush()

        rows = db_session.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.topic == "递归",
        ).all()
        assert len(rows) == 2
        assert {r.user_id for r in rows} == {u1, u2.id}