"""Tests for Phase 3 Step 4: 掌握度追踪与自适应进度

- MasteryTracker 核心逻辑
- 掌握度更新 + 自动推进
- FSRS 调度
- 课程掌握度概览
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.models import Course, MemoryFact, ProgressTracking, FSRSState
from backend.services.mastery_tracker import MasteryTracker, AUTO_ADVANCE_THRESHOLD


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
            db=MagicMock(), memories=[], course_id=1, world_id=1,
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
            world_id=1,
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
                db=db, memories=facts, course_id=1, world_id=1,
            )

            assert "变量" in result["updated_concepts"]
            assert "类型" in result["updated_concepts"]
            assert mock_review.call_count == 2  # both concepts scheduled

    def test_update_concept_struggle(self):
        db = MagicMock()
        course = self._make_course()

        with patch.object(self.tracker, '_update_concept_mastery') as mock_update, \
             patch.object(self.tracker, '_check_lesson_mastered', return_value=False):
            db.query.return_value.filter.return_value.first.return_value = course

            facts = [self._make_fact("concept_struggle", ["循环"])]
            result = self.tracker.update_from_memories(
                db=db, memories=facts, course_id=1, world_id=1,
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
            db=db, memories=facts, course_id=1, world_id=1,
        )
        assert result["updated_concepts"] == []

    def test_update_ignores_facts_without_concept_tags(self):
        db = MagicMock()
        facts = [self._make_fact("concept_mastered", [])]
        result = self.tracker.update_from_memories(
            db=db, memories=facts, course_id=1, world_id=1,
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
                db=db, memories=facts, course_id=1, world_id=1,
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
                db=db, memories=facts, course_id=1, world_id=1,
            )
            assert result["auto_advanced"] is False

    # ── _update_concept_mastery ────────────────────────────────────

    def test_update_concept_mastery_new(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        self.tracker._update_concept_mastery(db, 1, "变量", 25, 1)

        # Should have added a new tracking
        assert db.add.called

    def test_update_concept_mastery_existing(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 50
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, 1, "变量", 25, 1)

        assert tracking.mastery_level == 75
        assert not db.add.called

    def test_update_concept_mastery_clamped_max(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 90
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, 1, "变量", 25, 1)
        assert tracking.mastery_level == 100  # clamped

    def test_update_concept_mastery_clamped_min(self):
        db = MagicMock()
        tracking = MagicMock()
        tracking.mastery_level = 10
        db.query().filter().first.return_value = tracking

        self.tracker._update_concept_mastery(db, 1, "变量", -15, 1)
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