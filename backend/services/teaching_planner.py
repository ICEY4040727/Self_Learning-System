"""Teaching Planner service.

Canonical lesson-pointer storage:
- Lesson content: `LessonPlan` rows, with `course.meta["generated_lessons"]` as fallback
- Lesson progress: `CourseProgress`, with legacy `course.meta` fields as fallback
"""

import logging

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.models.models import Course, CourseProgress, LessonPlan

logger = logging.getLogger(__name__)


class TeachingPlanner:
    """Manage lesson progression for a course."""

    def _get_lessons(self, db: Session, course: Course) -> list[dict]:
        """Return lesson content from canonical rows, falling back to legacy meta."""
        lesson_rows = (
            db.query(LessonPlan)
            .filter(LessonPlan.course_id == course.id)
            .order_by(LessonPlan.order_index)
            .all()
        )

        if lesson_rows:
            return [
                {
                    "title": lp.title,
                    "description": lp.description,
                    "order": lp.order_index,
                    "concepts": lp.concepts or [],
                    "prerequisites": lp.prerequisites or [],
                    "id": lp.id,
                }
                for lp in lesson_rows
            ]

        if course.meta and course.meta.get("generated_lessons"):
            return course.meta["generated_lessons"]

        return []

    def _get_progress_record(self, db: Session, course: Course, user_id: int) -> CourseProgress | None:
        return (
            db.query(CourseProgress)
            .filter(
                CourseProgress.course_id == course.id,
                CourseProgress.user_id == user_id,
            )
            .first()
        )

    def _get_current_index(self, db: Session, course: Course, user_id: int) -> int:
        progress = self._get_progress_record(db, course, user_id)
        if progress:
            return progress.current_lesson_index or 0
        if course.meta:
            return course.meta.get("current_lesson_index", 0)
        return 0

    def _get_completed(self, db: Session, course: Course, user_id: int) -> list[int]:
        progress = self._get_progress_record(db, course, user_id)
        if progress:
            return progress.completed_lesson_ids or []
        if course.meta:
            return course.meta.get("completed_lessons", [])
        return []

    def _set_lesson_progress(
        self,
        db: Session,
        course: Course,
        user_id: int,
        *,
        current_index: int,
        completed_ids: list[int] | None = None,
    ) -> None:
        """Single write gateway for lesson-pointer state."""
        progress = self._get_progress_record(db, course, user_id)
        if progress:
            progress.current_lesson_index = current_index
            if completed_ids is not None:
                progress.completed_lesson_ids = completed_ids
            return

        if not course.meta:
            course.meta = {}
        course.meta["current_lesson_index"] = current_index
        if completed_ids is not None:
            course.meta["completed_lessons"] = completed_ids
        flag_modified(course, "meta")

    def _get_user_id(self, course: Course) -> int | None:
        if course.world:
            return course.world.user_id
        return None

    def get_current_lesson(self, db: Session, course: Course) -> dict | None:
        lessons = self._get_lessons(db, course)
        if not lessons:
            return None

        user_id = self._get_user_id(course)
        if user_id is None:
            return None

        current_idx = self._get_current_index(db, course, user_id)
        if 0 <= current_idx < len(lessons):
            lesson = dict(lessons[current_idx])
            lesson["_index"] = current_idx
            lesson["_total"] = len(lessons)
            return lesson
        return None

    def get_progress(self, db: Session, course: Course, user_id: int | None = None) -> dict:
        lessons = self._get_lessons(db, course)
        if not lessons:
            return {
                "total_lessons": 0,
                "current_index": 0,
                "completed_lessons": 0,
                "progress_pct": 0.0,
                "current_lesson": None,
                "lessons": [],
                "course_completed": False,
            }

        uid = user_id if user_id is not None else self._get_user_id(course)
        if uid is None:
            return {
                "total_lessons": len(lessons),
                "current_index": 0,
                "completed_lessons": 0,
                "progress_pct": 0.0,
                "current_lesson": None,
                "lessons": [{"title": l.get("title", ""), "_status": "pending"} for l in lessons],
                "course_completed": False,
            }

        current_idx = self._get_current_index(db, course, uid)
        completed = set(self._get_completed(db, course, uid))

        if current_idx >= len(lessons):
            current_idx = max(0, len(lessons) - 1)

        total = len(lessons)
        done = len(completed)
        pct = (done / total * 100) if total > 0 else 0.0

        current_lesson = None
        if 0 <= current_idx < len(lessons):
            current_lesson = dict(lessons[current_idx])
            current_lesson["_index"] = current_idx
            current_lesson["_status"] = "completed" if current_idx in completed else "current"

        lesson_list = []
        for i, lesson in enumerate(lessons):
            item = dict(lesson)
            if i in completed:
                item["_status"] = "completed"
            elif i == current_idx:
                item["_status"] = "current"
            else:
                item["_status"] = "pending"
            lesson_list.append(item)

        return {
            "total_lessons": total,
            "current_index": current_idx,
            "completed_lessons": done,
            "progress_pct": round(pct, 1),
            "current_lesson": current_lesson,
            "lessons": lesson_list,
            "course_completed": total > 0 and done >= total,
        }

    def advance_lesson(self, db: Session, course: Course) -> dict:
        """Mark the current lesson completed and move to the next lesson."""
        lessons = self._get_lessons(db, course)
        if not lessons:
            return {"error": "课程无生成内容"}

        user_id = self._get_user_id(course)
        if user_id is None:
            return {"error": "无法确定用户"}

        current_idx = self._get_current_index(db, course, user_id)
        completed = set(self._get_completed(db, course, user_id))
        completed.add(current_idx)

        next_idx = current_idx + 1
        if next_idx >= len(lessons):
            next_idx = len(lessons) - 1

        self._set_lesson_progress(
            db,
            course,
            user_id,
            current_index=next_idx,
            completed_ids=sorted(completed),
        )
        db.flush()

        logger.info(
            "Course %d: lesson %d -> %d (completed: %s)",
            course.id,
            current_idx,
            next_idx,
            sorted(completed),
        )
        return self.get_progress(db, course)

    def set_lesson(self, db: Session, course: Course, lesson_index: int) -> dict:
        """Move the lesson pointer without mutating completion history."""
        lessons = self._get_lessons(db, course)
        if not lessons:
            return {"error": "课程无生成内容"}
        if lesson_index < 0 or lesson_index >= len(lessons):
            return {"error": f"章节索引超出范围 (0-{len(lessons) - 1})"}

        user_id = self._get_user_id(course)
        if user_id is None:
            return {"error": "无法确定用户"}

        self._set_lesson_progress(
            db,
            course,
            user_id,
            current_index=lesson_index,
        )
        db.flush()

        logger.info("Course %d: manually set to lesson %d", course.id, lesson_index)
        return self.get_progress(db, course)

    def try_auto_advance_if_mastered(
        self,
        db: Session,
        course: Course,
        user_id: int,
    ) -> tuple[bool, int | None]:
        """Advance once when all concepts in the current lesson are mastered."""
        from backend.services.mastery_tracker import mastery_tracker

        lessons = self._get_lessons(db, course)
        if not lessons:
            return False, None

        current_idx = self._get_current_index(db, course, user_id)
        if current_idx >= len(lessons) - 1:
            return False, None

        current_lesson = lessons[current_idx]
        lesson_concepts = current_lesson.get("concepts") or []
        if not lesson_concepts:
            return False, None

        if not mastery_tracker._check_lesson_mastered(db, user_id, lesson_concepts):
            return False, None

        completed = set(self._get_completed(db, course, user_id))
        completed.add(current_idx)
        next_idx = current_idx + 1

        self._set_lesson_progress(
            db,
            course,
            user_id,
            current_index=next_idx,
            completed_ids=sorted(completed),
        )
        db.flush()

        logger.info(
            "Auto-advanced course %d: lesson %d -> %d",
            course.id,
            current_idx,
            next_idx,
        )
        return True, next_idx


teaching_planner = TeachingPlanner()
