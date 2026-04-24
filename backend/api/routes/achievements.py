"""Achievement & Gamification API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.services.gamification import gamification_engine

router = APIRouter()


class AchievementStatusResponse(BaseModel):
    unlocked: list[dict]
    locked_visible: list[dict]
    total_unlocked: int
    total_available: int

    class Config:
        from_attributes = True


@router.get(
    "/achievements/{user_id}/{character_id}",
    response_model=AchievementStatusResponse,
)
def get_achievement_status(
    user_id: int,
    character_id: int,
    db: Session = Depends(get_db),
):
    """获取用户的成就状态概览。"""
    return gamification_engine.get_achievements_status(
        db, user_id=user_id, character_id=character_id,
    )