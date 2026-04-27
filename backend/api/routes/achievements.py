"""Achievement & Gamification API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import User
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
    current_user: User = Depends(get_current_user),
):
    """获取用户的成就状态概览。

    [TODO-N1] Requires authentication and ownership — previously this route
    had no auth dependency at all, allowing any caller to enumerate any
    user's achievements (IDOR).
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot read another user's achievements")

    return gamification_engine.get_achievements_status(
        db, user_id=user_id, character_id=character_id,
    )