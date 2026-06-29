"""Archive compat shell — aggregates slug routes + progress compat surface (v1.0.5 Seam B)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.api.routes import characters, courses, learner_profiles, learning_diary, settings, worlds
from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import Course, User, World

router = APIRouter()
router.include_router(characters.router)
router.include_router(worlds.router)
router.include_router(learner_profiles.router)
router.include_router(courses.router)
router.include_router(settings.router)
router.include_router(learning_diary.router)

# Re-exports for tests / legacy imports
from backend.api.routes.characters import (  # noqa: E402, F401
    PERSONA_GENERATE_PROMPT,
    PERSONA_TEMPLATES,
    PersonaGenerateRequest,
    PersonaGenerateResponse,
)

class ProgressTrackingCreate(BaseModel):
    course_id: int
    topic: str
    mastery_level: int = 0
    next_review: datetime | None = None


class ProgressTrackingResponse(ProgressTrackingCreate):
    id: int
    user_id: int
    last_review: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# Progress Tracking endpoints
@router.post("/progress", response_model=ProgressTrackingResponse)
def create_progress(
    progress: ProgressTrackingCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.services.progress_facade import progress_facade

    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == progress.course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for key, value in progress_facade.progress_compat_headers(progress.course_id).items():
        response.headers[key] = value

    db_progress = progress_facade.create_progress_compat(
        db,
        user_id=current_user.id,
        course_id=progress.course_id,
        topic=progress.topic,
        mastery_level=progress.mastery_level,
        next_review=progress.next_review,
    )
    db.commit()
    if hasattr(db_progress, "__mapper__"):
        db.refresh(db_progress)
    return db_progress


@router.get("/progress", response_model=list[ProgressTrackingResponse])
def get_progress(
    response: Response,
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from backend.services.progress_facade import progress_facade

    for key, value in progress_facade.progress_compat_headers(course_id).items():
        response.headers[key] = value
    if course_id is not None:
        canonical_index = progress_facade.get_canonical_lesson_index(
            db, course_id, current_user.id,
        )
        response.headers["X-Canonical-Current-Lesson-Index"] = str(canonical_index)

    return progress_facade.list_compat_progress_rows(db, current_user.id, course_id)


@router.put("/progress/{progress_id}", response_model=ProgressTrackingResponse)
def update_progress(
    progress_id: int,
    progress: ProgressTrackingCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.services.progress_facade import progress_facade

    for key, value in progress_facade.progress_compat_headers(progress.course_id).items():
        response.headers[key] = value

    try:
        db_progress = progress_facade.update_progress_compat(
            db,
            progress_id=progress_id,
            user_id=current_user.id,
            course_id=progress.course_id,
            topic=progress.topic,
            mastery_level=progress.mastery_level,
            next_review=progress.next_review,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Progress not found")

    db.commit()
    if hasattr(db_progress, "__mapper__"):
        db.refresh(db_progress)
    return db_progress


# Review endpoint – FSRS spaced repetition
class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=4)  # 1=Again, 2=Hard, 3=Good, 4=Easy


class ReviewResponse(BaseModel):
    id: int
    topic: str
    mastery_level: int
    retrievability: float
    next_review: datetime | None = None
    last_review: datetime | None = None


@router.post("/progress/{progress_id}/review", response_model=ReviewResponse)
def review_progress(
    progress_id: int,
    req: ReviewRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a review for a topic and compute next review date via FSRS."""
    from backend.services.progress_facade import progress_facade

    response.headers["Deprecation"] = "true"

    try:
        result = progress_facade.record_review_compat(
            db,
            progress_id=progress_id,
            user_id=current_user.id,
            rating=req.rating,
        )
    except LookupError as exc:
        detail = str(exc) or "Progress not found"
        raise HTTPException(status_code=404, detail=detail)

    db.commit()

    return ReviewResponse(
        id=result["id"],
        topic=result["topic"],
        mastery_level=result["mastery_level"],
        retrievability=result["retrievability"],
        next_review=result["next_review"],
        last_review=result["last_review"],
    )


@router.get("/progress/due", response_model=list[ProgressTrackingResponse])
def get_due_reviews(
    response: Response,
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get topics that are due for review (next_review <= now)."""
    from backend.services.progress_facade import progress_facade

    for key, value in progress_facade.progress_compat_headers(course_id).items():
        response.headers[key] = value

    return progress_facade.list_due_reviews_compat(db, current_user.id, course_id)
