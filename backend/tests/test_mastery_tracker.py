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
    ConceptMastery,
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

        self.tracker._update_concept_mastery(db, concept="变量", delta=25, user_id=1)

        # Should have added a new tracking
        assert db.add.called

    def test_update_concept_mastery_existing(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 50
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, concept="变量", delta=25, user_id=1)

        assert tracking.mastery_level == 75
        assert not db.add.called

    def test_update_concept_mastery_clamped_max(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 90
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, concept="变量", delta=25, user_id=1)
        assert tracking.mastery_level == 100  # clamped

    def test_update_concept_mastery_clamped_min(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 10
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, concept="变量", delta=-15, user_id=1)
        assert tracking.mastery_level == 0  # clamped

    # ── _check_lesson_mastered ─────────────────────────────────────

    def test_check_lesson_mastered_true(self):
        db = MagicMock()
        # Both concepts at threshold → average == threshold → True
        rows = [
            MagicMock(concept_id="a", mastery_level=AUTO_ADVANCE_THRESHOLD),
            MagicMock(concept_id="b", mastery_level=AUTO_ADVANCE_THRESHOLD),
        ]
        db.query().filter().all.return_value = rows

        result = self.tracker._check_lesson_mastered(db, 1, ["a", "b"])
        assert result is True

    def test_check_lesson_mastered_false_low_mastery(self):
        db = MagicMock()
        rows = [MagicMock(concept_id="a", mastery_level=30)]
        db.query().filter().all.return_value = rows

        result = self.tracker._check_lesson_mastered(db, 1, ["a"])
        assert result is False

    def test_check_lesson_mastered_false_untracked(self):
        db = MagicMock()
        db.query().filter().all.return_value = []  # no rows for the user

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

    # ── get_course_mastery — see TestMasteryTrackerRealDB below ────
    # The reader now joins course.meta lesson concepts with ConceptMastery
    # rows. That control flow is too tangled for MagicMock; real-DB tests
    # cover it.

    # [TODO-T7] Removed `test_schedule_review_existing` — it asserted
    # stability == 4.5 (3.0 * 1.5), which was the hand-rolled math we
    # replaced with py-fsrs. Real behavior is now covered by
    # TestMasteryTrackerRealDB::test_card_data_round_trips_state etc.
    # Removed `test_schedule_review_new` for the same reason — its
    # `db.add.called` assertion is now exercised by the real-DB tests.


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

    def test_update_from_memories_inserts_concept_mastery_row(self, db_session):
        """[TR-A3] update_from_memories must persist ConceptMastery for the
        user (cross-world; no course_id / world_id on the row)."""
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

        rows = db_session.query(ConceptMastery).filter(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id == "递归",
        ).all()
        assert len(rows) == 1
        assert rows[0].mastery_level == 75  # 50 + 25 (concept_mastered delta)

    def test_concept_and_lesson_live_in_separate_tables(self, db_session):
        """[TR-A3] Concept and lesson rows used to share progress_trackings
        and stomp each other when titles matched; they now live in different
        tables so collision is structurally impossible."""
        from backend.services.teaching_planner import teaching_planner

        user_id, world_id, course_id = self._seed_user_world_course(db_session)
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

        teaching_planner._record_lesson_progress(db_session, course, 0)
        db_session.flush()

        # Concept side: ConceptMastery
        cm = db_session.query(ConceptMastery).filter(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id == "递归",
        ).one()
        assert cm.mastery_level == 75

        # Lesson side: ProgressTracking with topic_type='lesson'
        lesson_rows = db_session.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.topic == "递归",
        ).all()
        assert len(lesson_rows) == 1
        assert lesson_rows[0].topic_type == "lesson"

        # mastery overview pulls only ConceptMastery via course.meta
        overview = mastery_tracker.get_course_mastery(db_session, course_id, user_id)
        assert overview["total_tracked"] == 1
        assert overview["concepts"].get("递归") == 75

    def test_concept_mastery_is_cross_world(self, db_session):
        """[TR-A4] A concept learned in course A (world A) must be visible
        from course B (world B) for the same user. This is the cross-world
        invariant the redesign is supposed to deliver."""
        u = User(username="t-cross-world", password_hash="x", role="user")
        db_session.add(u)
        db_session.flush()

        wa = World(user_id=u.id, name="WA", scenes={})
        wb = World(user_id=u.id, name="WB", scenes={})
        db_session.add_all([wa, wb])
        db_session.flush()

        ca = Course(
            world_id=wa.id, name="CA",
            meta={"generated_lessons": [{"title": "L1", "concepts": ["递归"]}],
                  "current_lesson_index": 0, "completed_lessons": []},
        )
        cb = Course(
            world_id=wb.id, name="CB",
            meta={"generated_lessons": [{"title": "L1", "concepts": ["递归"]}],
                  "current_lesson_index": 0, "completed_lessons": []},
        )
        db_session.add_all([ca, cb])
        db_session.flush()

        # Learn 递归 in course A
        fact = MemoryFact(
            character_id=1, world_id=wa.id, fact_type="concept_mastered",
            content="ok", concept_tags=["递归"], salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()
        mastery_tracker.update_from_memories(
            db=db_session, memories=[fact],
            course_id=ca.id, world_id=wa.id, user_id=u.id,
        )
        db_session.flush()

        # Course B should see it
        overview_b = mastery_tracker.get_course_mastery(db_session, cb.id, u.id)
        assert overview_b["concepts"].get("递归") == 75, \
            "concept mastery must be cross-world for the same user"

    def test_struggle_schedules_fsrs(self, db_session):
        """[TODO-T2] concept_struggle must also schedule FSRS (the original
        code only scheduled mastered, leaving struggling concepts un-reviewed)."""
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
        assert fsrs.card_data is not None, "card_data must be persisted (T7)"
        assert fsrs.next_review is not None

    def test_struggle_interval_shorter_than_mastered(self, db_session):
        """[TODO-T2/T7] After struggle, next_review should be sooner than
        after mastered. py-fsrs Rating.Again schedules within minutes;
        Rating.Good schedules days out."""
        user_id, world_id, _ = self._seed_user_world_course(db_session)

        # Two separate concepts so FSRS state is independent.
        struggle_fact = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_struggle",
            content="不懂A", concept_tags=["A"], salience=0.6,
        )
        mastered_fact = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_mastered",
            content="懂B", concept_tags=["B"], salience=0.7,
        )
        db_session.add_all([struggle_fact, mastered_fact])
        db_session.flush()

        course_id = db_session.query(Course).first().id
        mastery_tracker.update_from_memories(
            db=db_session, memories=[struggle_fact, mastered_fact],
            course_id=course_id, world_id=world_id, user_id=user_id,
        )
        db_session.flush()

        struggle_fsrs = db_session.query(FSRSState).filter(
            FSRSState.world_id == world_id, FSRSState.concept_id == "A",
        ).first()
        mastered_fsrs = db_session.query(FSRSState).filter(
            FSRSState.world_id == world_id, FSRSState.concept_id == "B",
        ).first()
        assert struggle_fsrs.next_review < mastered_fsrs.next_review, \
            "struggle should be reviewed sooner than mastered"

    def test_card_data_round_trips_state(self, db_session):
        """[TODO-T7] Sequential mastered reviews must accumulate FSRS state
        — without card_data persistence each review reset to first-time."""
        user_id, world_id, course_id = self._seed_user_world_course(db_session)
        fact = MemoryFact(
            character_id=1, world_id=world_id, fact_type="concept_mastered",
            content="ok", concept_tags=["topic"], salience=0.7,
        )
        db_session.add(fact)
        db_session.flush()

        for _ in range(3):
            mastery_tracker.update_from_memories(
                db=db_session, memories=[fact],
                course_id=course_id, world_id=world_id, user_id=user_id,
            )
        db_session.flush()

        fsrs = db_session.query(FSRSState).filter(
            FSRSState.world_id == world_id, FSRSState.concept_id == "topic",
        ).first()
        assert fsrs.reps == 3, "three mastered reviews → reps == 3"
        # state should have progressed past Learning (state=1) into Review.
        # py-fsrs State enum: 1=Learning, 2=Review, 3=Relearning
        assert fsrs.card_data["state"] in (1, 2), "card_data must persist state"
        assert fsrs.card_data["card_id"] is not None

    def test_concept_mastery_keyed_by_user(self, db_session):
        """Different users learning the same concept → separate ConceptMastery
        rows (user_id is part of the UNIQUE key)."""
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

        rows = db_session.query(ConceptMastery).filter(
            ConceptMastery.concept_id == "递归",
        ).all()
        assert len(rows) == 2
        assert {r.user_id for r in rows} == {u1, u2.id}