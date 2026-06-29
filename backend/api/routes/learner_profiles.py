from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import LearnerProfile, User, World


router = APIRouter()

class LearnerProfileCreate(BaseModel):
    world_id: int
    profile: dict | None = None


class LearnerProfileResponse(LearnerProfileCreate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

# Learner Profile endpoints
@router.post("/learner_profile", response_model=LearnerProfileResponse)
def create_learner_profile(
    profile: LearnerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    world = db.query(World).filter(
        World.id == profile.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_profile = LearnerProfile(
        user_id=current_user.id,
        world_id=profile.world_id,
        profile=profile.profile or {},
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/learner_profile", response_model=list[LearnerProfileResponse])
def get_learner_profiles(
    world_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id
    )
    if world_id:
        query = query.filter(LearnerProfile.world_id == world_id)
    return query.all()


@router.put("/learner_profile/{profile_id}", response_model=LearnerProfileResponse)
def update_learner_profile(
    profile_id: int,
    profile: LearnerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_profile = db.query(LearnerProfile).filter(
        LearnerProfile.id == profile_id,
        LearnerProfile.user_id == current_user.id
    ).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Learner profile not found")

    world = db.query(World).filter(
        World.id == profile.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_profile.world_id = profile.world_id
    db_profile.profile = profile.profile or {}

    db.commit()
    db.refresh(db_profile)
    return db_profile


# World-scoped learner profile (Phase 2F: frontend expects this route)
@router.get("/worlds/{world_id}/learner_profile")
def get_world_learner_profile(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the learner profile for a specific world.

    Frontend (CoursePage, Learning) expects this route to return
    { dimension_scores, strengths, weaknesses, learning_stats, last_updated }
    directly, unwrapped from the profile JSON column.
    """
    lp = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id,
        LearnerProfile.world_id == world_id,
    ).first()
    if lp is None:
        raise HTTPException(status_code=404, detail="Learner profile not found")

    profile = lp.profile if isinstance(lp.profile, dict) else {}
    return {
        "dimension_scores": profile.get("dimension_scores", {}),
        "strengths": profile.get("strengths", []),
        "weaknesses": profile.get("weaknesses", []),
        "learning_stats": profile.get("learning_stats", {}),
        "last_updated": profile.get("last_updated"),
    }
