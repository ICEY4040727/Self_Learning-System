"""Teaching Planner Service

管理课程教学进度：当前章节、完成状态、自动推进。

Phase 3 Step 3: 课程感知教学集成
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.models.models import Course, ProgressTracking

logger = logging.getLogger(__name__)


class TeachingPlanner:
    """教学进度管理器

    职责：
    - 获取/设置当前教学章节
    - 推进到下一课（手动或自动）
    - 计算整体完成度
    """

    def get_current_lesson(self, course: Course) -> dict | None:
        """获取当前课程的教学章节信息

        Returns:
            当前章节 dict（含 title, description, concepts 等），或 None
        """
        if not course.meta:
            return None

        lessons = course.meta.get("generated_lessons", [])
        if not lessons:
            return None

        current_idx = course.meta.get("current_lesson_index", 0)
        if 0 <= current_idx < len(lessons):
            lesson = dict(lessons[current_idx])
            lesson["_index"] = current_idx
            lesson["_total"] = len(lessons)
            return lesson

        return None

    def get_progress(self, db: Session, course: Course) -> dict:
        """获取课程教学进度

        Returns:
            {
                "total_lessons": int,
                "current_index": int,
                "completed_lessons": int,
                "progress_pct": float,
                "current_lesson": dict | None,
                "lessons": list[dict],
            }
        """
        if not course.meta:
            return {
                "total_lessons": 0,
                "current_index": 0,
                "completed_lessons": 0,
                "progress_pct": 0.0,
                "current_lesson": None,
                "lessons": [],
            }

        lessons = course.meta.get("generated_lessons", [])
        current_idx = course.meta.get("current_lesson_index", 0)
        completed = course.meta.get("completed_lessons", [])

        # current_idx 超出范围时 clamp
        if current_idx >= len(lessons):
            current_idx = max(0, len(lessons) - 1)

        total = len(lessons)
        done = len(completed)
        pct = (done / total * 100) if total > 0 else 0.0

        current_lesson = None
        if lessons and 0 <= current_idx < len(lessons):
            current_lesson = dict(lessons[current_idx])
            current_lesson["_index"] = current_idx
            current_lesson["_status"] = "completed" if current_idx in completed else "current"

        # 给每个 lesson 加状态
        lesson_list = []
        for i, l in enumerate(lessons):
            item = dict(l)
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
        }

    def advance_lesson(self, db: Session, course: Course) -> dict:
        """推进到下一课

        Marks current lesson as completed and moves to next.

        Returns:
            更新后的进度 dict
        """
        if not course.meta:
            return {"error": "课程无生成内容"}

        lessons = course.meta.get("generated_lessons", [])
        if not lessons:
            return {"error": "课程无章节"}

        current_idx = course.meta.get("current_lesson_index", 0)
        completed = set(course.meta.get("completed_lessons", []))

        # 标记当前为完成
        completed.add(current_idx)

        # 推进到下一课（不超出范围）
        next_idx = current_idx + 1
        if next_idx >= len(lessons):
            next_idx = len(lessons) - 1  # 保持在最后一课

        course.meta["current_lesson_index"] = next_idx
        course.meta["completed_lessons"] = sorted(completed)
        flag_modified(course, "meta")

        # 记录到 ProgressTracking
        self._record_lesson_progress(db, course, next_idx)

        db.flush()

        logger.info(
            "Course %d: lesson %d → %d (completed: %s)",
            course.id, current_idx, next_idx, sorted(completed),
        )

        return self.get_progress(db, course)

    def set_lesson(self, db: Session, course: Course, lesson_index: int) -> dict:
        """手动设置当前教学章节

        Args:
            lesson_index: 目标章节索引 (0-based)

        Returns:
            更新后的进度 dict
        """
        if not course.meta:
            return {"error": "课程无生成内容"}

        lessons = course.meta.get("generated_lessons", [])
        if not lessons:
            return {"error": "课程无章节"}

        if lesson_index < 0 or lesson_index >= len(lessons):
            return {"error": f"章节索引超出范围 (0-{len(lessons)-1})"}

        course.meta["current_lesson_index"] = lesson_index
        flag_modified(course, "meta")

        self._record_lesson_progress(db, course, lesson_index)
        db.flush()

        logger.info("Course %d: manually set to lesson %d", course.id, lesson_index)

        return self.get_progress(db, course)

    def _record_lesson_progress(self, db: Session, course: Course, lesson_idx: int):
        """记录章节进度到 ProgressTracking 表（topic_type='lesson'）"""
        lessons = course.meta.get("generated_lessons", [])
        if not lessons or lesson_idx >= len(lessons):
            return

        lesson = lessons[lesson_idx]
        topic = lesson.get("title", f"Lesson {lesson_idx + 1}")

        # [TODO-T3] filter by topic_type so a lesson title that happens to
        # equal a concept name doesn't collide with mastery_tracker rows.
        existing = db.query(ProgressTracking).filter(
            ProgressTracking.course_id == course.id,
            ProgressTracking.topic == topic,
            ProgressTracking.topic_type == "lesson",
        ).first()

        if existing:
            existing.mastery_level = min((existing.mastery_level or 0) + 20, 100)
            existing.last_review = datetime.now(UTC)
        else:
            tracking = ProgressTracking(
                course_id=course.id,
                user_id=course.world.user_id if course.world else None,
                topic=topic,
                topic_type="lesson",
                mastery_level=20,
                last_review=datetime.now(UTC),
            )
            db.add(tracking)


# Global instance
teaching_planner = TeachingPlanner()