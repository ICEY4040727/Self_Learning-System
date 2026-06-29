"""Teaching Planner Service

管理课程教学进度：当前章节、完成状态、自动推进。

Phase 3 Step 3: 课程感知教学集成

数据源迁移：从 course.meta JSON → LessonPlan 表 + CourseProgress 表
- 课程列表：LessonPlan 行（按 order_index 排序）
- 进度状态：CourseProgress 行（current_lesson_index, completed_lesson_ids）
- 向后兼容：如 LessonPlan 行为空，回退读 course.meta
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.core.config import get_settings
from backend.models.models import Course, CourseProgress, LessonPlan, ProgressTracking

logger = logging.getLogger(__name__)


class TeachingPlanner:
    """教学进度管理器

    职责：
    - 获取/设置当前教学章节
    - 推进到下一课（手动或自动）
    - 计算整体完成度
    """

    def _get_lessons(self, db: Session, course: Course) -> list[dict]:
        """获取课程的所有章节（新数据源优先，兼容旧数据）

        Returns:
            list of lesson dicts with keys: title, description, order, concepts, prerequisites
        """
        # 新数据源：LessonPlan 表
        lesson_rows = db.query(LessonPlan).filter(
            LessonPlan.course_id == course.id,
        ).order_by(LessonPlan.order_index).all()

        if lesson_rows:
            return [
                {
                    "title": lp.title,
                    "description": lp.description,
                    "order": lp.order_index,
                    "concepts": lp.concepts or [],
                    "prerequisites": lp.prerequisites or [],
                    "id": lp.id,  # include DB id for reference
                }
                for lp in lesson_rows
            ]

        # 向后兼容：旧数据从 course.meta 读取
        if course.meta and course.meta.get("generated_lessons"):
            return course.meta["generated_lessons"]

        return []

    def _get_progress_record(self, db: Session, course: Course, user_id: int) -> CourseProgress | None:
        """获取 CourseProgress 行"""
        return db.query(CourseProgress).filter(
            CourseProgress.course_id == course.id,
            CourseProgress.user_id == user_id,
        ).first()

    def _get_current_index(self, db: Session, course: Course, user_id: int) -> int:
        """获取当前章节索引（新数据源优先，兼容旧数据）"""
        progress = self._get_progress_record(db, course, user_id)
        if progress:
            return progress.current_lesson_index or 0

        # 向后兼容
        if course.meta:
            return course.meta.get("current_lesson_index", 0)
        return 0

    def _get_completed(self, db: Session, course: Course, user_id: int) -> list[int]:
        """获取已完成的章节索引列表"""
        progress = self._get_progress_record(db, course, user_id)
        if progress:
            return progress.completed_lesson_ids or []

        # 向后兼容
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
        """唯一 lesson pointer 写入口。

        - 有 CourseProgress 行 → 只写表（不写 course.meta 指针字段）
        - 无行 → legacy fallback 写 course.meta
        """
        progress = self._get_progress_record(db, course, user_id)
        if progress:
            progress.current_lesson_index = current_index
            if completed_ids is not None:
                progress.completed_lesson_ids = completed_ids
        else:
            if not course.meta:
                course.meta = {}
            course.meta["current_lesson_index"] = current_index
            if completed_ids is not None:
                course.meta["completed_lessons"] = completed_ids
            flag_modified(course, "meta")

    def _get_user_id(self, course: Course) -> int | None:
        """从 course → world → user 获取 user_id"""
        if course.world:
            return course.world.user_id
        return None

    def get_current_lesson(self, db: Session, course: Course) -> dict | None:
        """获取当前课程的教学章节信息

        Returns:
            当前章节 dict（含 title, description, concepts 等），或 None
        """
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
                "course_completed": bool,
            }
        """
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

        user_id = self._get_user_id(course)
        if user_id is None:
            return {
                "total_lessons": len(lessons),
                "current_index": 0,
                "completed_lessons": 0,
                "progress_pct": 0.0,
                "current_lesson": None,
                "lessons": [{"title": l.get("title", ""), "_status": "pending"} for l in lessons],
                "course_completed": False,
            }

        current_idx = self._get_current_index(db, course, user_id)
        completed_list = self._get_completed(db, course, user_id)
        completed = set(completed_list)

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

        course_completed = total > 0 and done >= total

        return {
            "total_lessons": total,
            "current_index": current_idx,
            "completed_lessons": done,
            "progress_pct": round(pct, 1),
            "current_lesson": current_lesson,
            "lessons": lesson_list,
            "course_completed": course_completed,
        }

    def advance_lesson(self, db: Session, course: Course) -> dict:
        """推进到下一课

        Marks current lesson as completed and moves to next.
        """
        lessons = self._get_lessons(db, course)
        if not lessons:
            return {"error": "课程无生成内容"}

        user_id = self._get_user_id(course)
        if user_id is None:
            return {"error": "无法确定用户"}

        current_idx = self._get_current_index(db, course, user_id)
        completed_list = self._get_completed(db, course, user_id)
        completed = set(completed_list)

        # 标记当前为完成
        completed.add(current_idx)

        # 推进到下一课（不超出范围）
        next_idx = current_idx + 1
        if next_idx >= len(lessons):
            next_idx = len(lessons) - 1  # stay on last lesson

        self._set_lesson_progress(
            db,
            course,
            user_id,
            current_index=next_idx,
            completed_ids=sorted(completed),
        )

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
        lessons = self._get_lessons(db, course)
        if not lessons:
            return {"error": "课程无生成内容"}

        if lesson_index < 0 or lesson_index >= len(lessons):
            return {"error": f"章节索引超出范围 (0-{len(lessons)-1})"}

        user_id = self._get_user_id(course)
        if user_id is None:
            return {"error": "无法确定用户"}

        self._set_lesson_progress(
            db,
            course,
            user_id,
            current_index=lesson_index,
        )

        self._record_lesson_progress(db, course, lesson_index)
        db.flush()

        logger.info("Course %d: manually set to lesson %d", course.id, lesson_index)

        return self.get_progress(db, course)

    def _record_lesson_progress(self, db: Session, course: Course, lesson_idx: int):
        """首次到达某 lesson 时插入 'started' 行（mastery=20）。

        [TODO-T5] 不再对 existing 行 += 20。
        [v1.0.5] ProgressFacade 启用时不再 INSERT ProgressTracking。
        """
        from backend.services.progress_facade import progress_facade

        if progress_facade.skip_progress_tracking_writes():
            return

        lessons = self._get_lessons(db, course)
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
            # Already started — just refresh last_review timestamp.
            existing.last_review = datetime.now(UTC)
            return

        # [TODO-T9] initial mastery for a freshly-started lesson is config-driven
        initial = get_settings().learning_system["mastery"]["lesson_started_initial"]
        tracking = ProgressTracking(
            course_id=course.id,
            user_id=course.world.user_id if course.world else None,
            topic=topic,
            topic_type="lesson",
            mastery_level=initial,
            last_review=datetime.now(UTC),
        )
        db.add(tracking)

    def try_auto_advance_if_mastered(
        self,
        db: Session,
        course: Course,
        user_id: int,
    ) -> tuple[bool, int | None]:
        """唯一 auto-advance 事务入口（TeachingPlanner 完整边界）。

        读取当前课节 → 判定 concepts 是否 mastered → 推进并落库。
        """
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
        self._record_lesson_progress(db, course, next_idx)
        db.flush()

        logger.info(
            "Auto-advanced course %d: lesson %d → %d",
            course.id, current_idx, next_idx,
        )
        return True, next_idx


# Global instance
teaching_planner = TeachingPlanner()

