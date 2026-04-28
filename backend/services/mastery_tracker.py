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

from backend.core.config import get_settings
from backend.models.models import (
    ConceptMastery,
    Course,
    FSRSState,
    MemoryFact,
)

logger = logging.getLogger(__name__)


def _mastery_cfg() -> dict:
    """[TODO-T9] All mastery tunables live in core/config.py learning_system.mastery."""
    return get_settings().learning_system["mastery"]


# Re-exports for backward compat with tests that import these names.
# Read at module load — cfg dict won't change at runtime.
_cfg = _mastery_cfg()
MASTERY_DELTA_MAP = _cfg["delta_map"]
MIN_MASTERY = _cfg["min"]
MAX_MASTERY = _cfg["max"]
AUTO_ADVANCE_THRESHOLD = _cfg["auto_advance_threshold"]
del _cfg


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
        user_id: int,
    ) -> dict:
        """从新提取的记忆事实更新掌握度

        Args:
            memories: 本轮对话新提取的 MemoryFact 列表
            course_id: 当前课程 ID
            world_id: 当前世界 ID
            user_id: 当前用户 ID — ProgressTracking.user_id 是 NOT NULL，
                必须传入（之前漏传导致 prod INSERT 失败）。

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
                    concept=concept,
                    delta=delta,
                    user_id=user_id,
                )
                updated_concepts.append(concept)

                # [TODO-T2] Schedule FSRS for both mastered AND struggle.
                # Struggle is precisely when the system should pull a concept
                # forward in the review queue, not skip it.
                if fact.fact_type in ("concept_mastered", "concept_struggle"):
                    self._schedule_review(
                        db, world_id, concept, signal=fact.fact_type,
                    )

        # 检查是否可以自动推进
        auto_advanced = False
        new_lesson_index = None

        if updated_concepts and course.meta:
            lessons = course.meta.get("generated_lessons", [])
            current_idx = course.meta.get("current_lesson_index", 0)

            if lessons and 0 <= current_idx < len(lessons):
                current_lesson = lessons[current_idx]
                lesson_concepts = current_lesson.get("concepts", [])

                if lesson_concepts and self._check_lesson_mastered(db, user_id, lesson_concepts):
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
        concept: str,
        delta: int,
        user_id: int,
    ):
        """更新单个概念的掌握度。

        [TR-A3] Writes to ConceptMastery keyed by (user_id, concept_id).
        Cross-world by design — the same concept learned in one course/world
        is reflected everywhere the user encounters it.
        """
        tracking = db.query(ConceptMastery).filter(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id == concept,
        ).first()

        if tracking:
            old = tracking.mastery_level or 0
            tracking.mastery_level = max(MIN_MASTERY, min(MAX_MASTERY, old + delta))
            tracking.last_review = datetime.now(UTC)
        else:
            tracking = ConceptMastery(
                user_id=user_id,
                concept_id=concept,
                mastery_level=max(MIN_MASTERY, min(MAX_MASTERY, 50 + delta)),
                last_review=datetime.now(UTC),
            )
            db.add(tracking)

    def _check_lesson_mastered(self, db: Session, user_id: int, concepts: list[str]) -> bool:
        """检查当前章节的核心概念是否都已达到掌握阈值。

        [TR-A4] Reads ConceptMastery (per-user, cross-world).
        """
        if not concepts:
            return False

        rows = db.query(ConceptMastery).filter(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id.in_(concepts),
        ).all()
        by_concept = {r.concept_id: r.mastery_level or 0 for r in rows}

        # 任一概念未追踪视为 0（还没学）→ 章节未掌握
        if not all(c in by_concept for c in concepts):
            return False

        avg = sum(by_concept.values()) / len(concepts)
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

    def _schedule_review(
        self, db: Session, world_id: int, concept: str,
        *, signal: str = "concept_mastered",
    ):
        """调度 FSRS 复习 — 委托给 spaced_repetition wrapper（py-fsrs）。

        Args:
            signal: "concept_mastered" → Rating.Good (3)
                    "concept_struggle" → Rating.Again (1)

        [TODO-T7] Replaced hand-rolled stability *= 1.5 / *= 0.5 logic with
        spaced_repetition.review (py-fsrs lib). The library handles
        difficulty, stability, retrievability per the FSRS algorithm; the
        old code ignored difficulty entirely and capped stability at 365
        days, freezing intervals after ~13 successful reviews.

        [NEW-T1] flush() before SELECT — sessions are autoflush=False; same
        concept hit twice in one call would otherwise duplicate INSERT.
        """
        from backend.services import spaced_repetition

        rating_int = 1 if signal == "concept_struggle" else 3

        db.flush()
        existing = db.query(FSRSState).filter(
            FSRSState.world_id == world_id,
            FSRSState.concept_id == concept,
        ).first()

        # Use card_data as authoritative state. The individual columns can't
        # round-trip through py-fsrs (state/step/card_id missing) so reading
        # them and rebuilding a Card silently lost progress.
        existing_state = existing.card_data if existing else None

        result = spaced_repetition.review(existing_state, rating_int)
        fsrs_payload = result["fsrs_state"]

        if existing is None:
            existing = FSRSState(world_id=world_id, concept_id=concept)
            db.add(existing)

        existing.card_data = fsrs_payload
        # Keep individual columns synchronised for ad-hoc SQL queries.
        existing.difficulty = fsrs_payload.get("difficulty")
        existing.stability = fsrs_payload.get("stability")
        existing.last_review = result["last_review"]
        existing.next_review = result["due"]
        # reps tracked locally (py-fsrs Card has no reps field) —
        # struggle resets the streak, mastered increments it.
        if signal == "concept_struggle":
            existing.reps = 0
        else:
            existing.reps = (existing.reps or 0) + 1

    def get_course_mastery(self, db: Session, course_id: int, user_id: int) -> dict:
        """获取课程的掌握度概览。

        [TR-A4] Concept mastery is now cross-world per (user, concept). The
        course-scoped view is built by:
          1. taking the course's lesson concept list from course.meta,
          2. looking up the user's ConceptMastery rows for those concepts,
          3. computing the overview.

        Concepts that the user hasn't learned anywhere don't appear — that's
        consistent with the old "untracked = 0" behavior.

        Returns:
            {
                "overall_mastery": float,
                "concepts": dict[str, int],
                "weak_concepts": list[str],
                "mastered_count": int,
                "total_tracked": int,
            }
        """
        empty = {
            "overall_mastery": 0.0,
            "concepts": {},
            "weak_concepts": [],
            "mastered_count": 0,
            "total_tracked": 0,
        }

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course or not course.meta:
            return empty

        course_concepts: list[str] = []
        for lesson in course.meta.get("generated_lessons") or []:
            for c in lesson.get("concepts") or []:
                if c not in course_concepts:
                    course_concepts.append(c)

        if not course_concepts:
            return empty

        rows = db.query(ConceptMastery).filter(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id.in_(course_concepts),
        ).all()

        if not rows:
            return empty

        cfg = _mastery_cfg()
        weak_threshold = cfg["weak_threshold"]
        mastered_threshold = cfg["auto_advance_threshold"]

        concepts: dict[str, int] = {}
        weak: list[str] = []
        mastered = 0
        total = 0

        for r in rows:
            m = r.mastery_level or 0
            concepts[r.concept_id] = m
            total += m
            if m < weak_threshold:
                weak.append(r.concept_id)
            if m >= mastered_threshold:
                mastered += 1

        overall = total / len(rows) if rows else 0.0

        return {
            "overall_mastery": round(overall, 1),
            "concepts": concepts,
            "weak_concepts": weak,
            "mastered_count": mastered,
            "total_tracked": len(rows),
        }


# Global instance
mastery_tracker = MasteryTracker()