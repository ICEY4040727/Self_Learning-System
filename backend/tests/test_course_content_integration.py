"""Tests for Phase 3 Step 3: 课程感知教学集成

- CourseContentModule (prompt injection)
- TeachingPlanner (progress management)
- API endpoints (progress/advance/lesson)
"""

import pytest
from unittest.mock import MagicMock

from backend.services.prompt_builder.modules.course_content import CourseContentModule
from backend.services.teaching_planner import TeachingPlanner


# ── CourseContentModule Tests ──────────────────────────────────────────


class TestCourseContentModule:
    """CourseContentModule 单元测试"""

    def setup_method(self):
        self.module = CourseContentModule()

    def test_is_applicable_with_course_id(self):
        assert self.module.is_applicable({"course_id": 1}) is True

    def test_is_applicable_without_course_id(self):
        assert self.module.is_applicable({}) is False

    def test_should_include_no_db(self):
        """[TODO-T10] No db/course_id in context → skip module."""
        assert self.module.should_include({}) is False
        assert self.module.should_include({"course_id": 1}) is False  # no db

    def test_should_include_no_course(self):
        """[TODO-T10] course_id given but course not in DB → skip."""
        db = MagicMock()
        db.query().filter().first.return_value = None
        assert self.module.should_include({"db": db, "course_id": 999}) is False

    def test_should_include_no_generated_content(self):
        """[TODO-T10] Course exists but meta is empty → skip module."""
        db = MagicMock()
        course = MagicMock()
        course.meta = {}
        db.query().filter().first.return_value = course
        assert self.module.should_include({"db": db, "course_id": 1}) is False

    def test_should_include_with_generated_content(self):
        """[TODO-T10] Course has generated_lessons → include."""
        db = MagicMock()
        course = MagicMock()
        course.meta = {"generated_lessons": [{"title": "L1"}]}
        db.query().filter().first.return_value = course
        assert self.module.should_include({"db": db, "course_id": 1}) is True

    def test_get_priority(self):
        assert self.module.get_priority() == 12

    def test_get_section_name(self):
        assert "课程内容" in self.module.get_section_name()

    def test_assemble_no_db(self):
        result = self.module.assemble({"course_id": 1})
        assert result == ""

    def test_assemble_no_course_id(self):
        result = self.module.assemble({"db": MagicMock()})
        assert result == ""

    def test_assemble_course_no_meta(self):
        db = MagicMock()
        course = MagicMock()
        course.meta = None
        db.query().filter().first.return_value = course
        result = self.module.assemble({"db": db, "course_id": 1})
        assert result == ""

    def test_assemble_with_generated_content(self):
        db = MagicMock()
        course = MagicMock()
        course.meta = {
            "generated_overview": "Python 入门课程",
            "generated_lessons": [
                {"title": "变量与类型", "description": "基础", "order": 1,
                 "concepts": ["变量", "类型"], "prerequisites": []},
                {"title": "控制流", "description": "进阶", "order": 2,
                 "concepts": ["if", "for"], "prerequisites": ["变量"]},
            ],
            "current_lesson_index": 0,
        }
        db.query().filter().first.return_value = course

        result = self.module.assemble({"db": db, "course_id": 1})

        assert "Python 入门课程" in result
        assert "变量与类型" in result
        assert "控制流" in result
        assert "[当前章节]" in result
        assert "待学习" in result
        assert "教学指引" in result

    def test_assemble_with_concept_map(self):
        db = MagicMock()
        course = MagicMock()
        course.meta = {
            "generated_overview": "概述",
            "concept_map": {
                "nodes": [{"name": "变量"}, {"name": "函数"}],
                "edges": [{"source": "变量", "target": "函数", "relation": "组合"}],
            },
            "generated_lessons": [],
        }
        db.query().filter().first.return_value = course

        result = self.module.assemble({"db": db, "course_id": 1})

        assert "变量" in result
        assert "函数" in result
        assert "组合" in result

    def test_render_lessons_progress_markers(self):
        lessons = [
            {"title": "L1", "description": "D1", "concepts": ["c1"], "prerequisites": []},
            {"title": "L2", "description": "D2", "concepts": ["c2"], "prerequisites": []},
            {"title": "L3", "description": "D3", "concepts": ["c3"], "prerequisites": []},
        ]
        result = self.module._render_lessons(lessons, 1)
        assert "已完成" in result  # L1 done
        assert "当前章节" in result  # L2 current
        assert "待学习" in result  # L3 pending


# ── TeachingPlanner Tests ──────────────────────────────────────────────


class TestTeachingPlanner:
    """TeachingPlanner 单元测试"""

    def setup_method(self):
        self.planner = TeachingPlanner()

    def _make_course(self, meta=None):
        course = MagicMock()
        course.id = 1
        course.meta = meta
        course.world = MagicMock()
        course.world.user_id = 1
        return course

    def test_get_current_lesson_no_meta(self):
        course = self._make_course(meta=None)
        assert self.planner.get_current_lesson(course) is None

    def test_get_current_lesson_no_lessons(self):
        course = self._make_course(meta={})
        assert self.planner.get_current_lesson(course) is None

    def test_get_current_lesson_valid(self):
        course = self._make_course(meta={
            "generated_lessons": [
                {"title": "L1", "concepts": ["a"]},
                {"title": "L2", "concepts": ["b"]},
            ],
            "current_lesson_index": 1,
        })
        result = self.planner.get_current_lesson(course)
        assert result is not None
        assert result["title"] == "L2"
        assert result["_index"] == 1
        assert result["_total"] == 2

    def test_get_progress_empty(self):
        db = MagicMock()
        course = self._make_course(meta=None)
        progress = self.planner.get_progress(db, course)
        assert progress["total_lessons"] == 0
        assert progress["progress_pct"] == 0.0

    def test_get_progress_with_lessons(self):
        db = MagicMock()
        course = self._make_course(meta={
            "generated_lessons": [
                {"title": "L1"},
                {"title": "L2"},
                {"title": "L3"},
            ],
            "current_lesson_index": 1,
            "completed_lessons": [0],
        })
        progress = self.planner.get_progress(db, course)
        assert progress["total_lessons"] == 3
        assert progress["completed_lessons"] == 1
        assert progress["current_index"] == 1
        assert progress["progress_pct"] == 33.3

    def test_advance_lesson(self):
        db = MagicMock()
        db.query().filter().first.return_value = None  # ProgressTracking

        course = self._make_course(meta={
            "generated_lessons": [
                {"title": "L1"},
                {"title": "L2"},
            ],
            "current_lesson_index": 0,
            "completed_lessons": [],
        })

        result = self.planner.advance_lesson(db, course)
        assert "error" not in result
        assert course.meta["current_lesson_index"] == 1
        assert 0 in course.meta["completed_lessons"]

    def test_advance_lesson_at_end(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}, {"title": "L2"}],
            "current_lesson_index": 1,
            "completed_lessons": [0],
        })

        result = self.planner.advance_lesson(db, course)
        assert course.meta["current_lesson_index"] == 1  # stays at last

    def test_set_lesson_valid(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}, {"title": "L2"}, {"title": "L3"}],
            "current_lesson_index": 0,
        })

        result = self.planner.set_lesson(db, course, 2)
        assert "error" not in result
        assert course.meta["current_lesson_index"] == 2

    def test_set_lesson_out_of_range(self):
        db = MagicMock()
        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}],
        })

        result = self.planner.set_lesson(db, course, 5)
        assert "error" in result

    def test_advance_no_content(self):
        db = MagicMock()
        course = self._make_course(meta=None)
        result = self.planner.advance_lesson(db, course)
        assert "error" in result

    def test_get_progress_lessons_have_status(self):
        db = MagicMock()
        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}, {"title": "L2"}, {"title": "L3"}],
            "current_lesson_index": 1,
            "completed_lessons": [0],
        })
        progress = self.planner.get_progress(db, course)
        assert progress["lessons"][0]["_status"] == "completed"
        assert progress["lessons"][1]["_status"] == "current"
        assert progress["lessons"][2]["_status"] == "pending"

    def test_course_completed_signal(self):
        """[TODO-T6] After advancing past the last lesson, get_progress
        should set course_completed=True so frontend can show completion."""
        db = MagicMock()
        db.query().filter().first.return_value = None

        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}, {"title": "L2"}],
            "current_lesson_index": 1,
            "completed_lessons": [0],
        })

        result = self.planner.advance_lesson(db, course)
        assert result["course_completed"] is True
        assert result["progress_pct"] == 100.0

    def test_course_not_completed_mid_course(self):
        """course_completed should be False until the final advance."""
        db = MagicMock()
        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}, {"title": "L2"}, {"title": "L3"}],
            "current_lesson_index": 1,
            "completed_lessons": [0],
        })
        progress = self.planner.get_progress(db, course)
        assert progress["course_completed"] is False

    def test_record_progress_does_not_bump_existing_mastery(self):
        """[TODO-T5] Revisiting a lesson must not increment mastery — that
        was the bug where set_lesson(1) after advance_lesson(2) silently
        added +20 to lesson 1's mastery on every revisit."""
        db = MagicMock()
        existing = MagicMock()
        existing.mastery_level = 60
        db.query.return_value.filter.return_value.first.return_value = existing

        course = self._make_course(meta={
            "generated_lessons": [{"title": "L1"}],
            "current_lesson_index": 0,
        })

        self.planner._record_lesson_progress(db, course, 0)

        assert existing.mastery_level == 60, "revisit must not change mastery_level"
        assert not db.add.called, "must not insert another row when one exists"