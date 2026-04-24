"""Mastery Tracker Service

基于对话信号自动追踪学生对概念的理解程度。
连接 MemoryFact → 概念掌握度 → 课程推进 的闭环。

Phase 3 Step 4: 掌握度追踪与自适应进度

核心逻辑:
1. 每轮对话后，分析新提取的 MemoryFact
2. concept_mastered → 提升掌握度 + 调度 FSRS 复习
3. concept_struggle → 降低掌握度 + 记录薄弱点
4. 当前章节所有核心概念已掌握 → 自动推进到下一课
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.models.models import (
    Course,
    FSRSState,
    MemoryFact,
    ProgressTracking,
)

logger = logging.getLogger(__name__)

# 掌握度变化阈值
MASTERY_DELTA_MAP = {
    "concept_mastered": 25,      # 大幅提升
    "concept_struggle": -15,     # 明显下降
    "student_state": 0,          # 不影响掌握度
    "preference": 0,
    "event": 0,
    "commitment": 0,
}

# 掌握度范围
MIN_MASTERY = 0
MAX_MASTERY = 100

# 自动推进阈值：当前章节核心概念平均掌握度 >= 此值时推进
AUTO_ADVANCE_THRESHOLD = 70


class MasteryTracker:
    """掌握度追踪器

    职责：
    - 从 MemoryFact 信号更新概念掌握度
    - 记录到 ProgressTracking 表
    - 更新 FSRS 调度
    - 判断是否自动推进课程章节
    """

    def update_from_memories(
        self,
        db: Session,
        memories: list[MemoryFact],
        course_id: int,
        world_id: int,
    ) -> dict:
        """从新提取的记忆事实更新掌握度

        Args:
            memories: 本轮对话新提取的 MemoryFact 列表
            course_id: 当前课程 ID
            world_id: 当前世界 ID

        Returns:
            {
                "updated_concepts": list[str],  # 更新的概念名
                "auto_advanced": bool,           # 是否触发了自动推进
                "new_lesson_index": int | None,  # 推进后的章节索引
            }
        """
        if not memories:
            return {"updated_concepts": [], "auto_advanced": False, "new_lesson_index": None}

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return {"updated_concepts": [], "auto_advanced": False, "new_lesson_index": None}

        updated_concepts = []

        for fact in memories:
            delta = MASTERY_DELTA_MAP.get(fact.fact_type, 0)
            if delta == 0:
                continue

            # 从 concept_tags 中提取关联概念
            concepts = fact.concept_tags or []
            if not concepts:
                continue

            for concept in concepts:
                self._update_concept_mastery(
                    db=db,
                    course_id=course_id,
                    concept=concept,
                    delta=delta,
                    world_id=world_id,
                )
                updated_concepts.append(concept)

                # 如果是 mastered，调度 FSRS 复习
                if fact.fact_type == "concept_mastered":
                    self._schedule_review(db, world_id, concept)

        # 检查是否可以自动推进
        auto_advanced = False
        new_lesson_index = None

        if updated_concepts and course.meta:
            lessons = course.meta.get("generated_lessons", [])
            current_idx = course.meta.get("current_lesson_index", 0)

            if lessons and 0 <= current_idx < len(lessons):
                current_lesson = lessons[current_idx]
                lesson_concepts = current_lesson.get("concepts", [])

                if lesson_concepts and self._check_lesson_mastered(db, course_id, lesson_concepts):
                    auto_advanced, new_lesson_index = self._try_auto_advance(db, course)

        if updated_concepts:
            logger.info(
                "Mastery updated for course %d: concepts=%s, auto_advanced=%s",
                course_id, updated_concepts, auto_advanced,
            )

        return {
            "updated_concepts": updated_concepts,
            "auto_advanced": auto_advanced,
            "new_lesson_index": new_lesson_index,
        }

    def _update_concept_mastery(
        self,
        db: Session,
        course_id: int,
        concept: str,
        delta: int,
        world_id: int,
    ):
        """更新单个概念的掌握度"""
        tracking = db.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.topic == concept,
        ).first()

        if tracking:
            old = tracking.mastery_level or 0
            tracking.mastery_level = max(MIN_MASTERY, min(MAX_MASTERY, old + delta))
            tracking.last_review = datetime.now(UTC)
        else:
            tracking = ProgressTracking(
                course_id=course_id,
                topic=concept,
                mastery_level=max(MIN_MASTERY, min(MAX_MASTERY, 50 + delta)),
                last_review=datetime.now(UTC),
            )
            db.add(tracking)

    def _check_lesson_mastered(self, db: Session, course_id: int, concepts: list[str]) -> bool:
        """检查当前章节的核心概念是否都已达到掌握阈值"""
        if not concepts:
            return False

        total_mastery = 0
        tracked = 0

        for concept in concepts:
            tracking = db.query(ProgressTracking).filter(
                ProgressTracking.course_id == course_id,
                ProgressTracking.topic == concept,
            ).first()

            if tracking:
                total_mastery += tracking.mastery_level or 0
                tracked += 1
            else:
                # 未追踪的概念视为 0（还没学）
                return False

        if tracked == 0:
            return False

        avg = total_mastery / tracked
        return avg >= AUTO_ADVANCE_THRESHOLD

    def _try_auto_advance(self, db: Session, course: Course) -> tuple[bool, int | None]:
        """尝试自动推进到下一课

        Returns:
            (是否推进成功, 新章节索引)
        """
        from sqlalchemy.orm.attributes import flag_modified

        lessons = course.meta.get("generated_lessons", [])
        current_idx = course.meta.get("current_lesson_index", 0)

        if current_idx >= len(lessons) - 1:
            # 已经是最后一课
            return False, None

        # 推进
        completed = set(course.meta.get("completed_lessons", []))
        completed.add(current_idx)

        next_idx = current_idx + 1
        course.meta["current_lesson_index"] = next_idx
        course.meta["completed_lessons"] = sorted(completed)
        flag_modified(course, "meta")

        logger.info(
            "Auto-advanced course %d: lesson %d → %d",
            course.id, current_idx, next_idx,
        )

        return True, next_idx

    def _schedule_review(self, db: Session, world_id: int, concept: str):
        """调度 FSRS 复习"""
        existing = db.query(FSRSState).filter(
            FSRSState.world_id == world_id,
            FSRSState.concept_id == concept,
        ).first()

        if existing:
            existing.reps = (existing.reps or 0) + 1
            existing.last_review = datetime.now(UTC)
            # 简化的间隔计算：每次复习后稳定性增加
            stability = (existing.stability or 1.0) * 1.5
            existing.stability = min(stability, 365.0)
            from datetime import timedelta
            existing.next_review = datetime.now(UTC) + timedelta(days=stability)
        else:
            from datetime import timedelta
            fsrs = FSRSState(
                world_id=world_id,
                concept_id=concept,
                difficulty=5.0,
                stability=1.0,
                last_review=datetime.now(UTC),
                next_review=datetime.now(UTC) + timedelta(days=1),
                reps=1,
            )
            db.add(fsrs)

    def get_course_mastery(self, db: Session, course_id: int) -> dict:
        """获取课程的掌握度概览

        Returns:
            {
                "overall_mastery": float,  # 总体掌握度 0-100
                "concepts": dict[str, int],  # 各概念掌握度
                "weak_concepts": list[str],  # 薄弱概念 (mastery < 40)
                "mastered_count": int,
                "total_tracked": int,
            }
        """
        trackings = db.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
        ).all()

        if not trackings:
            return {
                "overall_mastery": 0.0,
                "concepts": {},
                "weak_concepts": [],
                "mastered_count": 0,
                "total_tracked": 0,
            }

        concepts = {}
        weak = []
        mastered = 0
        total = 0

        for t in trackings:
            m = t.mastery_level or 0
            concepts[t.topic] = m
            total += m
            if m < 40:
                weak.append(t.topic)
            if m >= AUTO_ADVANCE_THRESHOLD:
                mastered += 1

        overall = total / len(trackings) if trackings else 0.0

        return {
            "overall_mastery": round(overall, 1),
            "concepts": concepts,
            "weak_concepts": weak,
            "mastered_count": mastered,
            "total_tracked": len(trackings),
        }


# Global instance
mastery_tracker = MasteryTracker()