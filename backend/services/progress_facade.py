"""Progress facade — unified lesson progress read + compat write surface.

Canonical sources:
- Lesson pointer: CourseProgress via teaching_planner
- Concept mastery: ConceptMastery via mastery_tracker

ProgressTracking is compat-read only when ``use_progress_facade`` is enabled;
new rows must not be inserted through this facade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.models import (
    ConceptMastery,
    Course,
    FSRSState,
    ProgressTracking,
    World,
)
from backend.services import spaced_repetition
from backend.services.mastery_tracker import mastery_tracker
from backend.services.teaching_planner import teaching_planner

logger = logging.getLogger(__name__)


@dataclass
class CompatProgressView:
    """Synthetic ProgressTracking-shaped row for compat responses without INSERT."""

    id: int
    user_id: int
    course_id: int
    topic: str
    mastery_level: int
    next_review: datetime | None
    last_review: datetime | None
    topic_type: str = "concept"


def use_progress_facade() -> bool:
    """Feature flag — set USE_PROGRESS_FACADE=false to restore archive direct writes."""
    return get_settings().use_progress_facade


def skip_progress_tracking_writes() -> bool:
    return use_progress_facade()


def progress_compat_headers(course_id: int | None = None) -> dict[str, str]:
    headers = {"Deprecation": "true"}
    if course_id is not None:
        headers["Link"] = f'</api/courses/{course_id}/progress>; rel="successor-version"'
    return headers


def get_lesson_progress(db: Session, course: Course, user_id: int) -> dict[str, Any]:
    """Canonical lesson progress (CourseProgress / LessonPlan)."""
    _ = user_id  # caller supplies for auth symmetry; planner reads course.world
    return teaching_planner.get_progress(db, course)


def get_canonical_lesson_index(db: Session, course_id: int, user_id: int) -> int:
    course = (
        db.query(Course)
        .join(World, Course.world_id == World.id)
        .filter(Course.id == course_id, World.user_id == user_id)
        .first()
    )
    if not course:
        return 0
    return get_lesson_progress(db, course, user_id).get("current_index", 0)


def get_course_mastery(db: Session, course_id: int, user_id: int) -> dict[str, Any]:
    return mastery_tracker.get_course_mastery(db, course_id, user_id)


def list_compat_progress_rows(
    db: Session,
    user_id: int,
    course_id: int | None = None,
) -> list[ProgressTracking | CompatProgressView]:
    """Read legacy ProgressTracking rows for archive GET /progress."""
    query = (
        db.query(ProgressTracking)
        .join(Course, ProgressTracking.course_id == Course.id)
        .join(World, Course.world_id == World.id)
        .filter(
            ProgressTracking.user_id == user_id,
            World.user_id == user_id,
        )
    )
    if course_id is not None:
        query = query.filter(ProgressTracking.course_id == course_id)
    return list(query.all())


def _upsert_concept_mastery(
    db: Session,
    *,
    user_id: int,
    topic: str,
    mastery_level: int,
    last_review: datetime | None = None,
) -> ConceptMastery:
    now = last_review or datetime.now(UTC)
    row = (
        db.query(ConceptMastery)
        .filter(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id == topic,
        )
        .first()
    )
    if row:
        row.mastery_level = mastery_level
        row.last_review = now
    else:
        row = ConceptMastery(
            user_id=user_id,
            concept_id=topic,
            mastery_level=mastery_level,
            last_review=now,
        )
        db.add(row)
    db.flush()
    return row


def _find_existing_progress_tracking(
    db: Session,
    *,
    user_id: int,
    course_id: int,
    topic: str,
) -> ProgressTracking | None:
    return (
        db.query(ProgressTracking)
        .filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.user_id == user_id,
            ProgressTracking.topic == topic,
        )
        .first()
    )


def _synthetic_compat_row(
    *,
    user_id: int,
    course_id: int,
    topic: str,
    mastery_level: int,
    next_review: datetime | None,
    last_review: datetime | None,
    source_id: int,
) -> CompatProgressView:
    # Negative id marks non-persisted compat rows (distinct from progress_trackings PKs).
    return CompatProgressView(
        id=-source_id,
        user_id=user_id,
        course_id=course_id,
        topic=topic,
        mastery_level=mastery_level,
        next_review=next_review,
        last_review=last_review,
    )


def create_progress_compat(
    db: Session,
    *,
    user_id: int,
    course_id: int,
    topic: str,
    mastery_level: int = 0,
    next_review: datetime | None = None,
) -> ProgressTracking | CompatProgressView:
    """Compat create: write ConceptMastery; never INSERT ProgressTracking."""
    if not use_progress_facade():
        row = ProgressTracking(
            course_id=course_id,
            user_id=user_id,
            topic=topic,
            mastery_level=mastery_level,
            next_review=next_review,
        )
        db.add(row)
        db.flush()
        return row

    now = datetime.now(UTC)
    cm = _upsert_concept_mastery(
        db,
        user_id=user_id,
        topic=topic,
        mastery_level=mastery_level,
        last_review=now,
    )

    existing_pt = _find_existing_progress_tracking(
        db, user_id=user_id, course_id=course_id, topic=topic,
    )
    if existing_pt:
        existing_pt.mastery_level = mastery_level
        if next_review is not None:
            existing_pt.next_review = next_review
        existing_pt.last_review = now
        db.flush()
        return existing_pt

    return _synthetic_compat_row(
        user_id=user_id,
        course_id=course_id,
        topic=topic,
        mastery_level=mastery_level,
        next_review=next_review,
        last_review=now,
        source_id=cm.id,
    )


def update_progress_compat(
    db: Session,
    *,
    progress_id: int,
    user_id: int,
    course_id: int,
    topic: str,
    mastery_level: int = 0,
    next_review: datetime | None = None,
) -> ProgressTracking | CompatProgressView:
    """Compat update: canonical ConceptMastery + optional existing PT row."""
    if not use_progress_facade():
        db_progress = (
            db.query(ProgressTracking)
            .filter(
                ProgressTracking.id == progress_id,
                ProgressTracking.user_id == user_id,
            )
            .first()
        )
        if not db_progress:
            raise LookupError("Progress not found")
        db_progress.course_id = course_id
        db_progress.topic = topic
        db_progress.mastery_level = mastery_level
        if next_review is not None:
            db_progress.next_review = next_review
        db.flush()
        return db_progress

    now = datetime.now(UTC)
    cm = _upsert_concept_mastery(
        db,
        user_id=user_id,
        topic=topic,
        mastery_level=mastery_level,
        last_review=now,
    )

    db_progress = (
        db.query(ProgressTracking)
        .filter(
            ProgressTracking.id == progress_id,
            ProgressTracking.user_id == user_id,
        )
        .first()
    )
    if db_progress:
        db_progress.course_id = course_id
        db_progress.topic = topic
        db_progress.mastery_level = mastery_level
        if next_review is not None:
            db_progress.next_review = next_review
        db_progress.last_review = now
        db.flush()
        return db_progress

    return _synthetic_compat_row(
        user_id=user_id,
        course_id=course_id,
        topic=topic,
        mastery_level=mastery_level,
        next_review=next_review,
        last_review=now,
        source_id=cm.id,
    )


def record_review_compat(
    db: Session,
    *,
    progress_id: int,
    user_id: int,
    rating: int,
) -> dict[str, Any]:
    """FSRS review — updates FSRSState + ConceptMastery; no new ProgressTracking."""
    db_progress = (
        db.query(ProgressTracking)
        .join(Course, ProgressTracking.course_id == Course.id)
        .join(World, Course.world_id == World.id)
        .filter(
            ProgressTracking.id == progress_id,
            ProgressTracking.user_id == user_id,
            World.user_id == user_id,
        )
        .first()
    )

    if db_progress:
        topic = db_progress.topic
        course_id = db_progress.course_id
    elif progress_id < 0 and use_progress_facade():
        cm = db.query(ConceptMastery).filter(ConceptMastery.id == -progress_id).first()
        if not cm or cm.user_id != user_id:
            raise LookupError("Progress not found")
        topic = cm.concept_id
        course = (
            db.query(Course)
            .join(World, Course.world_id == World.id)
            .filter(World.user_id == user_id)
            .first()
        )
        if not course:
            raise LookupError("Course not found")
        course_id = course.id
        db_progress = None
    else:
        raise LookupError("Progress not found")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise LookupError("Course not found")

    fsrs_state_row = (
        db.query(FSRSState)
        .filter(
            FSRSState.user_id == user_id,
            FSRSState.concept_id == topic,
        )
        .first()
    )
    existing_fsrs_state = fsrs_state_row.card_data if fsrs_state_row else None
    result = spaced_repetition.review(existing_fsrs_state, rating)

    cm = _upsert_concept_mastery(
        db,
        user_id=user_id,
        topic=topic,
        mastery_level=result["mastery_level"],
        last_review=result["last_review"],
    )

    fsrs_payload = result["fsrs_state"]
    if fsrs_state_row is None:
        fsrs_state_row = FSRSState(
            user_id=user_id,
            world_id=course.world_id,
            concept_id=topic,
        )
        db.add(fsrs_state_row)

    fsrs_state_row.card_data = fsrs_payload
    fsrs_state_row.difficulty = fsrs_payload.get("difficulty")
    fsrs_state_row.stability = fsrs_payload.get("stability")
    fsrs_state_row.reps = (fsrs_state_row.reps or 0) + 1
    fsrs_state_row.last_review = result["last_review"]
    fsrs_state_row.next_review = result["due"]

    response_id = progress_id
    if db_progress is not None:
        db_progress.last_review = result["last_review"]
        db_progress.next_review = result["due"]
        db_progress.mastery_level = result["mastery_level"]
        response_id = db_progress.id
    else:
        response_id = -cm.id

    db.flush()

    return {
        "id": response_id,
        "topic": topic,
        "mastery_level": result["mastery_level"],
        "retrievability": result["retrievability"],
        "next_review": result["due"],
        "last_review": result["last_review"],
    }


def list_due_reviews_compat(
    db: Session,
    user_id: int,
    course_id: int | None = None,
) -> list[ProgressTracking]:
    """Due reviews — read legacy ProgressTracking rows (compat surface)."""
    now = datetime.now(UTC)
    query = (
        db.query(ProgressTracking)
        .join(Course, ProgressTracking.course_id == Course.id)
        .join(World, Course.world_id == World.id)
        .filter(
            ProgressTracking.user_id == user_id,
            ProgressTracking.next_review <= now,
            World.user_id == user_id,
        )
    )
    if course_id is not None:
        query = query.filter(ProgressTracking.course_id == course_id)
    return query.order_by(ProgressTracking.next_review).all()


# Global instance for symmetry with teaching_planner / mastery_tracker
class ProgressFacade:
    use_progress_facade = staticmethod(use_progress_facade)
    skip_progress_tracking_writes = staticmethod(skip_progress_tracking_writes)
    get_lesson_progress = staticmethod(get_lesson_progress)
    get_canonical_lesson_index = staticmethod(get_canonical_lesson_index)
    get_course_mastery = staticmethod(get_course_mastery)
    list_compat_progress_rows = staticmethod(list_compat_progress_rows)
    create_progress_compat = staticmethod(create_progress_compat)
    update_progress_compat = staticmethod(update_progress_compat)
    record_review_compat = staticmethod(record_review_compat)
    list_due_reviews_compat = staticmethod(list_due_reviews_compat)
    progress_compat_headers = staticmethod(progress_compat_headers)


progress_facade = ProgressFacade()
